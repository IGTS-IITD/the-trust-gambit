from django.shortcuts import get_object_or_404
from django.db import models
from rest_framework import generics, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django.contrib.auth.models import User

from .models import Action, Game, GameScore, Participant, Domain, SelfRating, Hostel, Round, Lobby, GameMembership
from .serializers import GameScoreSerializer, UserSerializer, ParticipantProfileSerializer, SelfRatingSerializer, PublicSelfRatingSerializer, HostelSerializer, RoundSerializer, SimpleParticipantSerializer, ActionSerializer

from .scoring import calculate_scores_for_round
from .lobby_utils import register_participant
from .round_flow import resolve_current_round, force_advance_current_round, start_game
from .email_verification import send_verification_email, resolve_verification_token

class RegisterUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        email = request.data.get('email')
        User.objects.filter(is_active=False).filter(
            models.Q(username=username) | models.Q(email__iexact=email)
        ).delete()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        hostel_id = request.data.get('hostel_id')
        hostel = None
        if hostel_id:
            try:
                hostel = Hostel.objects.get(id=hostel_id)
            except Hostel.DoesNotExist:
                user.delete()
                return Response({"hostel_id": "Invalid hostel ID provided."}, status=status.HTTP_400_BAD_REQUEST)

        Participant.objects.create(user=user, hostel=hostel)
        send_verification_email(user)

        headers = self.get_success_headers(serializer.data)
        return Response({
            'user': serializer.data,
            'detail': 'Account created. Check your email for a verification link before logging in.',
        }, status=status.HTTP_201_CREATED, headers=headers)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        user = resolve_verification_token(request.data.get('uid', ''), request.data.get('token', ''))
        if not user:
            return Response({'detail': 'This verification link is invalid or has expired.'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])
            
            # Automatically register for all active games
            active_games = Game.objects.exclude(state=Game.State.COMPLETED)
            if hasattr(user, 'participant'):
                for game in active_games:
                    register_participant(user.participant, game)

        token, created = Token.objects.get_or_create(user=user)
        participant = getattr(user, 'participant', None)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'participant_id': participant.id if participant else None,
        })


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '')
        user = User.objects.filter(email__iexact=email, is_active=False).first()
        if user:
            send_verification_email(user)
        return Response({'detail': "If that email is registered and not yet verified, we've sent a new link."})


class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError:
            username = request.data.get('username', '')
            unverified = User.objects.filter(username=username, is_active=False).exists()
            if unverified:
                return Response(
                    {'detail': 'Please verify your email before logging in.', 'unverified': True},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username
        })

class ParticipantProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ParticipantProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.participant

    def perform_update(self, serializer):
        hostel_id = self.request.data.get('hostel_id')
        if hostel_id is not None:
            try:
                hostel = Hostel.objects.get(id=hostel_id)
                serializer.instance.hostel = hostel
            except Hostel.DoesNotExist:
                raise serializers.ValidationError({"hostel_id": "Invalid hostel ID provided."})
        serializer.save()

class DomainListView(generics.ListAPIView):
    queryset = Domain.objects.all()
    serializer_class = SelfRatingSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        class SimpleDomainSerializer(serializers.ModelSerializer):
            class Meta:
                model = Domain
                fields = ['id', 'name']
        
        queryset = self.filter_queryset(self.get_queryset())
        serializer = SimpleDomainSerializer(queryset, many=True)
        return Response(serializer.data)

class SelfRatingCreateListView(generics.ListCreateAPIView):
    serializer_class = SelfRatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SelfRating.objects.filter(participant=self.request.user.participant)

    def perform_create(self, serializer):
        if not self.request.user.participant:
            raise serializers.ValidationError("User is not associated with a Participant profile.")
        
        if serializer.validated_data['participant'].user != self.request.user:
            raise serializers.ValidationError("You can only submit ratings for your own participant profile.")
            
        serializer.save()


class AdminAssignLobbyView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        game_id = request.data.get('game_id')
        participant_id = request.data.get('participant_id')
        lobby_id = request.data.get('lobby_id')

        if not all([game_id, participant_id, lobby_id]):
            return Response({'error': 'game_id, participant_id, and lobby_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        game = get_object_or_404(Game, id=game_id)
        participant = get_object_or_404(Participant, id=participant_id)
        lobby = get_object_or_404(Lobby, id=lobby_id)

        if game.state == Game.State.COMPLETED:
            return Response({'error': 'Cannot assign to a completed game.'}, status=status.HTTP_400_BAD_REQUEST)

        if lobby.game != game:
            return Response({'error': 'Lobby does not belong to this game.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            membership = GameMembership.objects.get(game=game, participant=participant)
        except GameMembership.DoesNotExist:
            return Response({'error': 'Participant is not registered for this game.'}, status=status.HTTP_400_BAD_REQUEST)

        if membership.lobby:
            if membership.lobby == lobby:
                return Response({'status': 'Already assigned to this lobby.'})
            return Response({'error': 'Participant is already assigned to another lobby.'}, status=status.HTTP_400_BAD_REQUEST)

        current_members_count = GameMembership.objects.filter(lobby=lobby).count()
        if current_members_count >= game.player_limit:
            return Response({'error': 'Lobby is already at or above the normal player limit.'}, status=status.HTTP_400_BAD_REQUEST)

        membership.lobby = lobby
        
        if game.state == Game.State.RUNNING:
            current_round = resolve_current_round(game)
            if current_round:
                membership.eligible_from_round = current_round.round_number + 1
            else:
                membership.eligible_from_round = 1
        else:
            membership.eligible_from_round = 1

        membership.save(update_fields=['lobby', 'eligible_from_round'])
        
        return Response({'status': 'Successfully assigned.'})


class AllRatingsListView(generics.ListAPIView):
    queryset = SelfRating.objects.all().select_related('participant__user', 'domain')
    serializer_class = PublicSelfRatingSerializer
    permission_classes = [IsAuthenticated]
    
class HostelListView(generics.ListAPIView):
    queryset = Hostel.objects.all()
    serializer_class = HostelSerializer
    permission_classes = [AllowAny]

class CurrentRoundView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        active_game = Game.objects.exclude(state=Game.State.COMPLETED).first()
        if not active_game:
            return Response({"detail": "No active game at the moment."}, status=404)

        current_round = resolve_current_round(active_game)
        if not current_round:
            return Response({"detail": "No active round at the moment."}, status=status.HTTP_404_NOT_FOUND)

        membership = GameMembership.objects.filter(game=active_game, participant=request.user.participant).first()
        user_lobby = membership.lobby if membership else None
        
        if not user_lobby:
            return Response({"detail": "You have not been assigned to a lobby yet."}, status=400)

        # Ensure the user is eligible for this round
        if membership.eligible_from_round and membership.eligible_from_round > current_round.round_number:
            return Response({"detail": "You are assigned but not eligible for the current round."}, status=400)

        other_participants = Participant.objects.filter(memberships__lobby=user_lobby).exclude(user=request.user)
        
        round_serializer = RoundSerializer(current_round)
        participants_serializer = SimpleParticipantSerializer(other_participants, many=True)

        return Response({
            'current_round': round_serializer.data,
            'delegation_targets': participants_serializer.data
        })

class SubmitActionView(generics.CreateAPIView):
    serializer_class = ActionSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        active_game = Game.objects.exclude(state=Game.State.COMPLETED).first()
        if not active_game:
            raise serializers.ValidationError("No active game to submit an action for.")

        current_round = resolve_current_round(active_game)
        if not current_round:
            raise serializers.ValidationError("No active round available to submit an action for.")
            
        membership = GameMembership.objects.filter(game=active_game, participant=self.request.user.participant).first()
        if not membership or not membership.lobby:
            raise serializers.ValidationError("You are not assigned to a lobby.")
            
        if membership.eligible_from_round and membership.eligible_from_round > current_round.round_number:
            raise serializers.ValidationError("You are not eligible for the current round.")

        context['round'] = current_round
        return context

    def perform_create(self, serializer):
        current_round = self.get_serializer_context()['round']
        serializer.save(
            participant=self.request.user.participant,
            round=current_round
        )

class LeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from django.db.models import Sum
        participants = Participant.objects.all()
        
        leaderboard = []
        for p in participants:
            res = GameScore.objects.filter(participant=p).aggregate(Sum('score'))
            score = res['score__sum'] or 0
            
            participant_data = SimpleParticipantSerializer(p).data
            leaderboard.append({
                'participant': participant_data,
                'score': score
            })
            
        leaderboard.sort(key=lambda x: x['score'], reverse=True)
        return Response(leaderboard)
    
class AdminEndRoundView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        active_game = Game.objects.filter(state=Game.State.RUNNING).first()
        if not active_game:
            return Response({'error': 'No active running game to end a round for.'}, status=status.HTTP_404_NOT_FOUND)

        ended_round = resolve_current_round(active_game)
        if not ended_round:
            return Response({'error': 'No active round to end.'}, status=status.HTTP_404_NOT_FOUND)

        next_round = force_advance_current_round(active_game)
        return Response({
            'status': f'Round {ended_round.round_number} scored and ended early.',
            'next_round': next_round.round_number if next_round else None,
        })


class AdminStartGameView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        active_game = Game.objects.filter(state=Game.State.REGISTRATION).first()
        if not active_game:
            return Response({'error': 'No game in registration state to start.'}, status=status.HTTP_404_NOT_FOUND)

        started_round = start_game(active_game)
        if not started_round:
            return Response(
                {'error': 'Game already started, or there is no round 1 to start.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({'status': f'Round {started_round.round_number} started.'})

class RoundListView(generics.ListAPIView):
    queryset = Round.objects.all().order_by('-round_number')
    serializer_class = RoundSerializer
    permission_classes = [IsAuthenticated]

class DelegationGraphView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, round_id, *args, **kwargs):
        try:
            round_obj = Round.objects.get(id=round_id)
        except Round.DoesNotExist:
            return Response({"detail": "Round not found."}, status=status.HTTP_404_NOT_FOUND)
            
        membership = GameMembership.objects.filter(game=round_obj.game, participant=request.user.participant).first()
        user_lobby = membership.lobby if membership else None
        
        if not user_lobby:
            return Response({"detail": "You are not in a lobby."}, status=status.HTTP_400_BAD_REQUEST)

        all_lobby_participants = Participant.objects.filter(memberships__lobby=user_lobby).select_related('user')
        nodes = [{'id': str(p.id), 'data': {'label': p.user.username}, 'position': {'x': 0, 'y': 0}} for p in all_lobby_participants]
        
        actions = Action.objects.filter(
            round=round_obj, 
            participant__memberships__lobby=user_lobby
        ).select_related('participant', 'delegated_to')

        edges = []
        for action in actions:
            if action.action_type == Action.ActionType.DELEGATE and action.delegated_to:
                edges.append({
                    'id': f"e-{action.participant.id}-{action.delegated_to.id}",
                    'source': str(action.participant.id),
                    'target': str(action.delegated_to.id),
                    'animated': True,
                })
        
        return Response({'nodes': nodes, 'edges': edges})
