from rest_framework import serializers
from django.contrib.auth.models import User
from .email_verification import is_disposable_email
from .models import GameScore, Participant, Domain, SelfRating, Hostel, Action, Round, Game

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def validate_email(self, value):
        if is_disposable_email(value):
            raise serializers.ValidationError(
                "Disposable/temporary email addresses aren't allowed. Please use a real address."
            )
        existing = User.objects.filter(email__iexact=value).first()
        if existing and existing.is_active:
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        user.is_active = False
        user.save(update_fields=['is_active'])
        return user

class HostelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hostel
        fields = ['id', 'name']

class ParticipantProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    hostel = HostelSerializer(read_only=True)
    total_score = serializers.SerializerMethodField()
    
    class Meta:
        model = Participant
        fields = ['id', 'user', 'hostel', 'total_score']

    def get_total_score(self, obj):
        from django.db.models import Sum
        active_game = (
            Game.objects.filter(state=Game.State.RUNNING).first()
            or Game.objects.filter(state=Game.State.COMPLETED).order_by('-id').first()
            or Game.objects.filter(state=Game.State.REGISTRATION).first()
        )
        if not active_game:
            return 0
        return obj.game_scores.filter(game=active_game).aggregate(
            total=Sum('score')
        )['total'] or 0

class SelfRatingSerializer(serializers.ModelSerializer):
    participant = serializers.PrimaryKeyRelatedField(queryset=Participant.objects.all())
    domain = serializers.PrimaryKeyRelatedField(queryset=Domain.objects.all())

    class Meta:
        model = SelfRating
        fields = ['id', 'participant', 'domain', 'rating', 'justification']
        read_only_fields = ['id']

    def validate(self, data):
        if SelfRating.objects.filter(
            participant=data['participant'],
            domain=data['domain']
        ).exists():
            raise serializers.ValidationError("Participant has already rated this domain.")
        return data
        
class SimpleParticipantSerializer(serializers.ModelSerializer):
    """A simple serializer to list participants for delegation choices."""
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = Participant
        fields = ['id', 'username']


class PublicSelfRatingSerializer(serializers.ModelSerializer):
    """
    A read-only serializer to publicly display all user ratings.
    """
    participant = SimpleParticipantSerializer(read_only=True)
    domain = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = SelfRating
        fields = ['participant', 'domain', 'rating']
        
class RoundSerializer(serializers.ModelSerializer):
    domain = serializers.StringRelatedField() # Show the domain name instead of its ID
    seconds_remaining = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    result_display_seconds = serializers.IntegerField(
        source='game.result_display_seconds', read_only=True
    )
    game_name = serializers.CharField(source='game.name', read_only=True)

    class Meta:
        model = Round
        fields = [
            'id', 'round_number', 'domain', 'question_text',
            'duration_seconds', 'starts_at', 'seconds_remaining',
            'game_name', 'question_type', 'consensus_mode', 'resolved_answer',
            'consensus_vote_counts', 'answer_explanation', 'is_completed',
            'is_paused', 'status', 'results_until', 'result_display_seconds',
        ]

    def get_seconds_remaining(self, obj):
        if not obj.starts_at:
            return None
        if obj.is_paused:
            return max(0, int(obj.paused_remaining_seconds or 0))
        from django.utils import timezone
        elapsed = (timezone.now() - obj.starts_at).total_seconds()
        return max(0, int(obj.duration_seconds - elapsed))

    def get_status(self, obj):
        if obj.is_completed:
            return 'COMPLETED'
        if obj.is_paused:
            return 'PAUSED'
        if obj.starts_at:
            return 'RUNNING'
        return 'SCHEDULED'

class ActionSerializer(serializers.ModelSerializer):
    participant = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Action
        fields = ['id', 'action_type', 'delegated_to', 'submitted_answer', 'participant']
        read_only_fields = ['id', 'participant']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.round = self.context.get('round')

    def validate(self, data):
        action_type = data.get('action_type')
        delegated_to = data.get('delegated_to')
        submitted_answer = data.get('submitted_answer')
        
        participant = self.context['request'].user.participant

        if Action.objects.filter(round=self.round, participant=participant).exists():
            raise serializers.ValidationError("You have already submitted an action for this round.")

        if action_type == Action.ActionType.SOLVE:
            if not submitted_answer:
                raise serializers.ValidationError("A submitted_answer is required for the 'Solve' action.")
            if (
                self.round.question_type == Round.QuestionType.CONSENSUS
                and (submitted_answer or '').strip() not in {'1', '2', '3', '4'}
            ):
                raise serializers.ValidationError(
                    "Consensus answers must be one of 1, 2, 3, or 4."
                )
            if delegated_to:
                raise serializers.ValidationError("Cannot specify a delegation target when solving.")
        elif action_type == Action.ActionType.DELEGATE:
            if not delegated_to:
                raise serializers.ValidationError("A target must be specified when delegating.")
            if delegated_to == participant:
                raise serializers.ValidationError("You cannot delegate to yourself.")
            if submitted_answer:
                 raise serializers.ValidationError("Cannot submit an answer when delegating.")
        
        if action_type != Action.ActionType.DELEGATE and delegated_to:
            raise serializers.ValidationError("Cannot specify a delegation target unless the action is 'DELEGATE'.")

        return data
    
class GameScoreSerializer(serializers.ModelSerializer):
    """ Serializer for the leaderboard. """
    participant = SimpleParticipantSerializer(read_only=True)

    class Meta:
        model = GameScore
        fields = ['participant', 'score']


class RoundResultParticipantSerializer(serializers.Serializer):
    participant = SimpleParticipantSerializer()
    action_type = serializers.CharField(allow_null=True)
    is_solve_correct = serializers.BooleanField(allow_null=True)
    points_awarded = serializers.FloatField()
    base_points_awarded = serializers.FloatField()
    reputation_bonus = serializers.FloatField()
    delegated_to_me = serializers.IntegerField()
