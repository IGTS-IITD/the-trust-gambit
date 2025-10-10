from django.shortcuts import get_object_or_404
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

class RegisterUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        hostel_id = request.data.get('hostel_id')
        hostel = None
        if hostel_id:
            try:
                hostel = Hostel.objects.get(id=hostel_id)
            except Hostel.DoesNotExist:
                return Response({"hostel_id": "Invalid hostel ID provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        participant = Participant.objects.create(user=user, hostel=hostel)

        token, created = Token.objects.get_or_create(user=user)

        headers = self.get_success_headers(serializer.data)
        return Response({
            'user': serializer.data,
            'participant_id': participant.id,
            'token': token.key
        }, status=status.HTTP_201_CREATED, headers=headers)

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
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

        current_round = Round.objects.filter(game=active_game, is_completed=False).order_by('-round_number').first()
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
        
        current_round = Round.objects.filter(is_completed=False).order_by('-round_number').first()
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
    An admin-only endpoint to trigger the scoring for the current active round.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        # Find the current round to be ended
        current_round = Round.objects.filter(is_completed=False).order_by('round_number').first()

        if not current_round:
            return Response({'error': 'No active round to end.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Trigger the scoring logic from scoring.py
        calculate_scores_for_round(current_round.id)
        
        return Response({'status': f'Scoring successfully initiated for round {current_round.round_number}.'})

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

