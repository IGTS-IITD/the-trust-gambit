from django.shortcuts import get_object_or_404
from django.db import models
from rest_framework import generics, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django.contrib.auth.models import User

from .models import Action, Game, GameScore, Participant, Domain, SelfRating, Hostel, Round, Lobby
from .serializers import GameScoreSerializer, UserSerializer, ParticipantProfileSerializer, SelfRatingSerializer, PublicSelfRatingSerializer, HostelSerializer, RoundSerializer, SimpleParticipantSerializer, ActionSerializer

from .scoring import calculate_scores_for_round
from .lobby_utils import assign_participants_to_lobbies
from .round_flow import resolve_current_round, force_advance_current_round, start_game
from .email_verification import send_verification_email, resolve_verification_token

class RegisterUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        email = request.data.get('email')
        # A previous, never-verified registration with this username or
        # email doesn't block a fresh attempt (lost the link, mistyped
        # something the first time, etc.) - clear it out before validating.
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
        # Same response either way, so this can't be used to probe which
        # emails are registered.
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

class AdminAssignLobbiesView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        lobby_size = request.data.get('lobby_size')
        if not lobby_size or not isinstance(lobby_size, int) or lobby_size <= 0:
            return Response({'error': 'A valid integer lobby_size is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        result = assign_participants_to_lobbies(lobby_size)
        
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(result, status=status.HTTP_200_OK)

class AllRatingsListView(generics.ListAPIView):
    """
    Provides a public, read-only list of all self-ratings from all participants.
    """
    queryset = SelfRating.objects.all().select_related('participant__user', 'domain')
    serializer_class = PublicSelfRatingSerializer
    permission_classes = [IsAuthenticated] # Only logged-in users can see this
    
class HostelListView(generics.ListAPIView):
    queryset = Hostel.objects.all()
    serializer_class = HostelSerializer
    permission_classes = [AllowAny]

class CurrentRoundView(APIView):
    """
    Provides the details for the current active round and a list of participants.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        active_game = Game.objects.filter(is_active=True).first()
        if not active_game:
            return Response({"detail": "No active game at the moment."}, status=404)

        current_round = resolve_current_round(active_game)
        if not current_round:
            return Response({"detail": "No active round at the moment."}, status=status.HTTP_404_NOT_FOUND)

        user_lobby = request.user.participant.current_lobby
        if not user_lobby:
            return Response({"detail": "You have not been assigned to a lobby yet."}, status=400)

        other_participants = Participant.objects.filter(current_lobby=user_lobby).exclude(user=request.user)
        
        round_serializer = RoundSerializer(current_round)
        participants_serializer = SimpleParticipantSerializer(other_participants, many=True)

        return Response({
            'current_round': round_serializer.data,
            'delegation_targets': participants_serializer.data
        })

# class LobbyLeaderboardView(generics.ListAPIView):
#     # (Requirement 4: Leaderboard is lobby-specific)
#     serializer_class = GameScoreSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         lobby_id = self.kwargs.get('lobby_id')
#         return GameScore.objects.filter(participant__current_lobby_id=lobby_id).order_by('-score')

class SubmitActionView(generics.CreateAPIView):
    """
    Allows a participant to submit their action for the current round.
    """
    serializer_class = ActionSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        # Pass the current round to the serializer for validation
        context = super().get_serializer_context()
        active_game = Game.objects.filter(is_active=True).first()
        if not active_game:
            raise serializers.ValidationError("No active game to submit an action for.")

        current_round = resolve_current_round(active_game)
        if not current_round:
            # This should ideally be handled with a custom exception
            raise serializers.ValidationError("No active round available to submit an action for.")
        context['round'] = current_round
        return context

    def perform_create(self, serializer):
        current_round = self.get_serializer_context()['round']
        
        # Automatically associate the action with the current participant and round
        serializer.save(
            participant=self.request.user.participant,
            round=current_round
        )

# class LeaderboardView(generics.ListAPIView):
#     """
#     Provides a view of the game leaderboard, ordered by score.
#     """
#     serializer_class = GameScoreSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         # Assuming there is one main active game. 
#         # This could be enhanced to select a game via URL parameter.
#         active_game = Game.objects.filter(is_active=True).first()
#         if not active_game:
#             return GameScore.objects.none() # Return empty queryset if no active game
        
#         return GameScore.objects.filter(game=active_game).order_by('-score')

class LeaderboardView(APIView):
    """
    Provides the leaderboard for the currently logged-in user's lobby.
    The lobby is determined automatically from the user's profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        participant = request.user.participant
        lobby = participant.current_lobby

        if not lobby:
            # If the user isn't in a lobby, return an empty list.
            return Response([], status=status.HTTP_200_OK)

        # Get all scores for participants who are in the user's lobby
        queryset = GameScore.objects.filter(participant__current_lobby=lobby).order_by('-score')
        
        # Serialize the data and return it
        serializer = GameScoreSerializer(queryset, many=True)
        return Response(serializer.data)
    
class AdminEndRoundView(APIView):
    """
    An admin-only escape hatch to end the current round immediately,
    regardless of its timer, and start the next one right away. Normal
    rounds end automatically on their own via round_flow.resolve_current_round.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        active_game = Game.objects.filter(is_active=True).first()
        if not active_game:
            return Response({'error': 'No active game to end a round for.'}, status=status.HTTP_404_NOT_FOUND)

        ended_round = resolve_current_round(active_game)
        if not ended_round:
            return Response({'error': 'No active round to end.'}, status=status.HTTP_404_NOT_FOUND)

        next_round = force_advance_current_round(active_game)
        return Response({
            'status': f'Round {ended_round.round_number} scored and ended early.',
            'next_round': next_round.round_number if next_round else None,
        })


class AdminStartGameView(APIView):
    """
    An admin-only endpoint to kick off round 1 (and therefore the whole
    automated round sequence) for the active game.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        active_game = Game.objects.filter(is_active=True).first()
        if not active_game:
            return Response({'error': 'No active game to start.'}, status=status.HTTP_404_NOT_FOUND)

        started_round = start_game(active_game)
        if not started_round:
            return Response(
                {'error': 'Game already started, or there is no round 1 to start.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({'status': f'Round {started_round.round_number} started.'})

class RoundListView(generics.ListAPIView):
    """
    Provides a list of all rounds, with the newest first.
    Useful for selecting a round to view its delegation graph.
    """
    queryset = Round.objects.all().order_by('-round_number')
    serializer_class = RoundSerializer
    permission_classes = [IsAuthenticated]

class DelegationGraphView(APIView):
    """
    Returns the data needed to draw a trust graph for a specific round.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, round_id, *args, **kwargs):
        try:
            round_obj = Round.objects.get(id=round_id)
        except Round.DoesNotExist:
            return Response({"detail": "Round not found."}, status=status.HTTP_404_NOT_FOUND)
        
        user_lobby = request.user.participant.current_lobby
        if not user_lobby:
            return Response({"detail": "You are not in a lobby."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Get ALL participants in the lobby to serve as the nodes.
        all_lobby_participants = Participant.objects.filter(current_lobby=user_lobby).select_related('user')
        nodes = [{'id': str(p.id), 'data': {'label': p.user.username}, 'position': {'x': 0, 'y': 0}} for p in all_lobby_participants]
        
        # 2. Get only the actions from that lobby for the specific round to create the edges.
        actions = Action.objects.filter(
            round=round_obj, 
            participant__current_lobby=user_lobby
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

