import math

from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
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
from .round_flow import (
    resolve_current_round,
    force_advance_current_round,
    start_game,
    pause_current_round,
    resume_current_round,
    set_current_round_remaining,
    restart_game,
)
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
        active_game = (
            Game.objects.filter(state=Game.State.RUNNING).first()
            or Game.objects.filter(state=Game.State.REGISTRATION).first()
            or Game.objects.filter(state=Game.State.COMPLETED).order_by('-id').first()
        )
        if not active_game:
            return Response({"detail": "No active game at the moment."}, status=404)

        current_round = resolve_current_round(active_game)
        last_completed_round = Round.objects.filter(
            game=active_game, is_completed=True
        ).order_by('-round_number').first()
        if not current_round:
            membership = GameMembership.objects.filter(
                game=active_game, participant=request.user.participant
            ).first()
            if last_completed_round and membership and membership.lobby:
                return Response({
                    'current_round': None,
                    'last_completed_round_id': last_completed_round.id,
                    'last_completed_round_results': RoundResultsView.build_payload(
                        last_completed_round, membership
                    ),
                    'delegation_targets': [],
                })
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
            'delegation_targets': participants_serializer.data,
            'last_completed_round_id': (
                last_completed_round.id if last_completed_round else None
            ),
            'last_completed_round_results': (
                RoundResultsView.build_payload(last_completed_round, membership)
                if last_completed_round and membership.lobby else None
            ),
        })

class SubmitActionView(generics.CreateAPIView):
    serializer_class = ActionSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        active_game = (
            Game.objects.filter(state=Game.State.RUNNING).first()
            or Game.objects.filter(state=Game.State.REGISTRATION).first()
        )
        if not active_game:
            raise serializers.ValidationError("No active game to submit an action for.")

        current_round = resolve_current_round(active_game)
        if not current_round:
            raise serializers.ValidationError("No active round available to submit an action for.")
        if current_round.is_paused:
            raise serializers.ValidationError("The game is paused. Submissions are temporarily disabled.")
            
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
        scope = request.query_params.get('scope', 'global')
        if scope not in {'global', 'lobby'}:
            return Response(
                {'detail': "scope must be either 'global' or 'lobby'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        active_game = Game.objects.filter(state=Game.State.RUNNING).first()
        if not active_game:
            active_game = Game.objects.filter(
                state=Game.State.COMPLETED
            ).order_by('-id').first()
        if not active_game:
            active_game = Game.objects.filter(state=Game.State.REGISTRATION).first()
        if active_game and active_game.state == Game.State.RUNNING:
            resolve_current_round(active_game)
            active_game.refresh_from_db()
        if not active_game:
            active_game = Game.objects.filter(
                state=Game.State.COMPLETED
            ).order_by('-id').first()
        if not active_game:
            return Response([], status=status.HTTP_200_OK)

        participants = Participant.objects.filter(
            memberships__game=active_game
        ).select_related('user').distinct()
        if scope == 'lobby':
            membership = GameMembership.objects.filter(
                game=active_game,
                participant=request.user.participant,
            ).select_related('lobby').first()
            if not membership or not membership.lobby:
                return Response([], status=status.HTTP_200_OK)
            participants = participants.filter(
                memberships__game=active_game,
                memberships__lobby=membership.lobby,
            ).distinct()

        participants = participants.annotate(
            score=Coalesce(
                Sum(
                    'game_scores__score',
                    filter=Q(game_scores__game=active_game),
                ),
                Value(0.0),
            )
        ).order_by('-score', 'user__username')

        return Response([
            {
                'participant': SimpleParticipantSerializer(participant).data,
                'score': participant.score,
            }
            for participant in participants
        ])
    
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


class AdminRestartGameView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        game_id = request.data.get('game_id')
        game = get_object_or_404(Game, id=game_id)
        restarted_round = restart_game(game)
        if not restarted_round:
            return Response(
                {'error': 'A game can be restarted only when all its rounds are complete and no other game is running.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({
            'status': 'RESTARTED',
            'game_id': game.id,
            'round': RoundSerializer(restarted_round).data,
        })


class AdminResetLeaderboardView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        game_id = request.data.get('game_id')
        game = get_object_or_404(Game, id=game_id)
        deleted, _ = GameScore.objects.filter(game=game).delete()
        return Response({
            'status': 'RESET',
            'game_id': game.id,
            'deleted_score_rows': deleted,
        })


class AdminPauseGameView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        active_game = Game.objects.filter(state=Game.State.RUNNING).first()
        if not active_game:
            return Response({'error': 'No active running game to pause.'}, status=status.HTTP_404_NOT_FOUND)
        round_obj = pause_current_round(active_game)
        if not round_obj:
            return Response({'error': 'No active round to pause.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'status': 'PAUSED', 'round': RoundSerializer(round_obj).data})


class AdminResumeGameView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        active_game = Game.objects.filter(state=Game.State.RUNNING).first()
        if not active_game:
            return Response({'error': 'No active running game to resume.'}, status=status.HTTP_404_NOT_FOUND)
        round_obj = resume_current_round(active_game)
        if not round_obj:
            return Response({'error': 'No paused round to resume.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'status': 'RUNNING', 'round': RoundSerializer(round_obj).data})


class AdminSetRoundTimeView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        active_game = Game.objects.filter(state=Game.State.RUNNING).first()
        if not active_game:
            return Response({'error': 'No active running game.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            remaining_seconds = float(request.data.get('remaining_seconds'))
        except (TypeError, ValueError):
            return Response({'error': 'remaining_seconds must be a number.'}, status=status.HTTP_400_BAD_REQUEST)
        if not math.isfinite(remaining_seconds) or not 0 < remaining_seconds:
            return Response({'error': 'remaining_seconds must be greater than zero.'}, status=status.HTTP_400_BAD_REQUEST)

        round_obj = set_current_round_remaining(active_game, remaining_seconds)
        if not round_obj:
            return Response({'error': 'No active round to retime.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'status': 'UPDATED', 'round': RoundSerializer(round_obj).data})

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


class RoundResultsView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def build_payload(round_obj, membership):
        lobby_participants = list(
            Participant.objects.filter(memberships__lobby=membership.lobby)
            .select_related('user').distinct()
        )
        participant_ids = {participant.id for participant in lobby_participants}
        actions = list(
            Action.objects.filter(
                round=round_obj, participant_id__in=participant_ids
            ).select_related('participant', 'delegated_to')
        )
        action_by_participant = {action.participant_id: action for action in actions}
        delegated_counts = {
            participant_id: sum(
                action.action_type == Action.ActionType.DELEGATE
                and action.delegated_to_id == participant_id
                for action in actions
            )
            for participant_id in participant_ids
        }
        participant_results = []
        for participant in lobby_participants:
            action = action_by_participant.get(participant.id)
            points = action.points_awarded if action else 0
            base_points = action.base_points_awarded if action else 0
            participant_results.append({
                'participant': SimpleParticipantSerializer(participant).data,
                'action_type': action.action_type if action else None,
                'is_solve_correct': action.is_solve_correct if action else None,
                'points_awarded': points,
                'base_points_awarded': base_points,
                'reputation_bonus': points - base_points,
                'delegated_to_me': delegated_counts[participant.id],
            })

        return {
            'round': RoundSerializer(round_obj).data,
            'correct_answer': (
                round_obj.correct_answer
                if round_obj.question_type == Round.QuestionType.STANDARD
                else round_obj.resolved_answer
            ),
            'answer_explanation': round_obj.answer_explanation,
            'consensus_votes': round_obj.consensus_vote_counts,
            'participants': participant_results,
        }

    def get(self, request, round_id, *args, **kwargs):
        round_obj = get_object_or_404(Round.objects.select_related('game'), id=round_id)
        membership = GameMembership.objects.filter(
            game=round_obj.game, participant=request.user.participant
        ).select_related('lobby').first()
        if not membership or not membership.lobby:
            return Response({'detail': 'You are not in a lobby for this game.'}, status=status.HTTP_403_FORBIDDEN)
        if not round_obj.is_completed:
            return Response({'detail': 'Results are available after the round ends.'}, status=status.HTTP_409_CONFLICT)
        return Response(self.build_payload(round_obj, membership))
