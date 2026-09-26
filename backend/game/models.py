from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

class Hostel(models.Model):
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name

class Game(models.Model):
    class State(models.TextChoices):
        REGISTRATION = 'REGISTRATION', 'Registration'
        RUNNING = 'RUNNING', 'Running'
        COMPLETED = 'COMPLETED', 'Completed'

    name = models.CharField(max_length=200, default="The Trust Gambit")
    state = models.CharField(max_length=20, choices=State.choices, default=State.REGISTRATION)
    lambda_param = models.FloatField(default=0.5) 
    beta_param = models.FloatField(default=0.2)
    player_limit = models.PositiveIntegerField(default=settings.LOBBY_PLAYER_LIMIT)

    def __str__(self):
        return self.name

class Lobby(models.Model):
    name = models.CharField(max_length=100)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='lobbies')
    is_active = models.BooleanField(default=True)
    sequence_number = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('game', 'sequence_number')

    def __str__(self):
        return f"Lobby: {self.name} (Game: {self.game.name})"
    
class Participant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hostel = models.ForeignKey(Hostel, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username

class GameMembership(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='memberships')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='memberships')
    lobby = models.ForeignKey(Lobby, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    registered_at = models.DateTimeField(auto_now_add=True)
    eligible_from_round = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('game', 'participant')

    def __str__(self):
        return f"{self.participant.user.username} in {self.game.name} (Lobby: {self.lobby.name if self.lobby else 'Unassigned'})"

class Domain(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class SelfRating(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='ratings')
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0, validators=[
            MinValueValidator(0),
            MaxValueValidator(10)
        ])
    justification = models.TextField(max_length=500) 

    class Meta:
        unique_together = ('participant', 'domain') 

    def __str__(self):
        return f"{self.participant.user.username} rates {self.domain.name} as {self.rating}"

class Round(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='rounds')
    # lobby = models.ForeignKey(Lobby, on_delete=models.CASCADE, related_name='rounds', null=True)
    
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    question_text = models.TextField()
    correct_answer = models.CharField(max_length=255, default='correct answer here')
    is_completed = models.BooleanField(default=False)
    round_number = models.PositiveIntegerField()

    duration_seconds = models.PositiveIntegerField(
        default=120,
        help_text="How long this round stays open once it starts.",
    )
    starts_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        help_text="Set automatically when this round becomes current. Leave blank.",
    )

    class Meta:
        unique_together = ('game', 'round_number')

    def __str__(self):
        return f"Round {self.round_number} ({self.domain.name})"

class Action(models.Model):
    class ActionType(models.TextChoices):
        SOLVE = 'SOLVE', 'Solve'
        DELEGATE = 'DELEGATE', 'Delegate'
        PASS = 'PASS', 'Pass'

    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='actions')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=10, choices=ActionType.choices)

    submitted_answer = models.TextField(null=True, blank=True)

    delegated_to = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegated_by'
    )
    
    is_solve_correct = models.BooleanField(null=True, blank=True)
    points_awarded = models.FloatField(default=0)

    def __str__(self):
        return f"{self.participant.user.username} chose to {self.action_type} in Round {self.round.round_number}"

class GameScore(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='scores')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='game_scores')
    score = models.FloatField(default=0)

    class Meta:
        unique_together = ('game', 'participant')

    def __str__(self):
        return f"{self.participant.user.username}: {self.score} points in {self.game.name}"

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Game)
def auto_populate_game(sender, instance, created, **kwargs):
    """
    Whenever a new game is created, instantly register all existing participants
    on the site to this new game (as unassigned), and pre-create lobbies.
    """
    if created:
        from .lobby_utils import register_participant
        import math
        
        # Pre-create the correct number of lobbies
        n = Participant.objects.count()
        limit = instance.player_limit
        required_lobbies = max(1, math.ceil(n / limit))
        for i in range(1, required_lobbies + 1):
            Lobby.objects.create(
                name=f"{instance.name}-Lobby-{i}",
                game=instance,
                sequence_number=i
            )
            
        for participant in Participant.objects.all():
            register_participant(participant, instance)