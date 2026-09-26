from django.db import transaction
from django.utils import timezone

from .models import Round, Game, Lobby
from .scoring import calculate_scores_for_round
from .lobby_utils import assign_pending_memberships

def resolve_current_round(game):
    """
    The single source of truth for "what round is current right now" for a
    game. Auto-scores and advances any round whose timer has expired,
    cascading through multiple rounds in one call if nobody has checked in
    for a while (e.g. a slow round, or everyone stepping away).

    Returns the Round that's actually open right now, or None if the game
    hasn't been started yet (no round has `starts_at` set) or has finished
    (every round is completed).
    """
    while True:
        round_obj = (
            Round.objects.filter(game=game, is_completed=False, starts_at__isnull=False)
            .order_by("-round_number")
            .first()
        )
        if not round_obj:
            return None

        elapsed = (timezone.now() - round_obj.starts_at).total_seconds()
        if elapsed < round_obj.duration_seconds:
            return round_obj

        _advance_past(round_obj)


def _advance_past(locked_round):
    """
    Given a completed round, score it, mark it closed, and launch the next
    round off its ideal end time (not just "now").
    """
    locked = (
        Round.objects.select_for_update()
        .filter(pk=locked_round.pk, is_completed=False)
        .first()
    )
    if not locked:
        return

    calculate_scores_for_round(locked.id)
    
    locked.is_completed = True
    locked.save(update_fields=["is_completed"])

    locked_game = Game.objects.select_for_update().get(pk=locked.game.pk)
    
    assign_pending_memberships(locked_game, is_game_start=False)
    
    next_round = Round.objects.filter(
        game=locked_game, round_number=locked.round_number + 1
    ).first()
    
    if not next_round:
        locked_game.state = Game.State.COMPLETED
        locked_game.save(update_fields=['state'])
        # (Lobbies persist permanently now)
        return

    next_round.starts_at = locked.starts_at + timezone.timedelta(seconds=locked.duration_seconds)
    next_round.save(update_fields=["starts_at"])


def force_advance_current_round(game):
    """
    Forces the currently active round to advance regardless of the time elapsed.
    """
    round_obj = Round.objects.filter(
        game=game, is_completed=False, starts_at__isnull=False
    ).order_by("-round_number").first()
    
    if not round_obj:
        return None
        
    _advance_past(round_obj)
    
    return Round.objects.filter(
        game=game, round_number=round_obj.round_number + 1
    ).first()


@transaction.atomic
def start_game(game):
    """
    Kicks off round 1 for a game, if it hasn't been started already.
    Returns the started round, or None if there's no round 1 to start,
    the game is already underway, or another game is running.
    """
    # Enforce only 1 running game
    if Game.objects.filter(state=Game.State.RUNNING).exists():
        return None

    locked_game = Game.objects.select_for_update().get(pk=game.pk)
    
    if locked_game.state != Game.State.REGISTRATION:
        return None
        
    if Round.objects.filter(game=locked_game, starts_at__isnull=False).exists():
        return None

    round_one = Round.objects.filter(game=locked_game, round_number=1).first()
    if not round_one:
        return None

    assign_pending_memberships(locked_game, is_game_start=True)

    round_one.starts_at = timezone.now()
    round_one.save(update_fields=["starts_at"])
    
    locked_game.state = Game.State.RUNNING
    locked_game.save(update_fields=['state'])
    
    return round_one
