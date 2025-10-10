from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Hostel(models.Model):
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name

class Game(models.Model):
    name = models.CharField(max_length=200, default="The Trust Gambit")
    is_active = models.BooleanField(default=True)
    lambda_param = models.FloatField(default=0.5) 
    beta_param = models.FloatField(default=0.2)   

    def __str__(self):
        return self.name

class Lobby(models.Model):
    name = models.CharField(max_length=100)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='lobbies')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Lobby: {self.name} (Game: {self.game.name})"
    
class Participant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hostel = models.ForeignKey(Hostel, on_delete=models.SET_NULL, null=True, blank=True)
    current_lobby = models.ForeignKey(Lobby, on_delete=models.SET_NULL, null=True, blank=True, related_name='participants')

    def __str__(self):
        return self.user.username

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