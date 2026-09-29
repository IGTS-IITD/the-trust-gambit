from django.db import transaction
from django.utils import timezone

from .models import Round, Game, Action, GameScore, Lobby
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
            .select_related("game", "domain")
            .order_by("-round_number")
            .first()
        )
        if not round_obj:
            final_round = Round.objects.filter(
                game=game, is_completed=True
            ).order_by('-round_number').first()
            if (
                game.state == Game.State.RUNNING
                and final_round
                and final_round.results_until
            ):
                if timezone.now() >= final_round.results_until:
                    game.state = Game.State.COMPLETED
                    game.save(update_fields=['state'])
            return None

        if round_obj.is_paused:
            return round_obj

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
        locked.results_until = timezone.now() + timezone.timedelta(
            seconds=locked_game.result_display_seconds
        )
        locked.save(update_fields=['results_until'])
        # Keep the game running until the final result display window expires.
        return

    next_round.starts_at = locked.starts_at + timezone.timedelta(seconds=locked.duration_seconds)
    next_round.save(update_fields=["starts_at"])


@transaction.atomic
def pause_current_round(game):
    """Freeze the current round at its server-calculated remaining time."""
    round_obj = (
        Round.objects.select_for_update()
        .filter(game=game, is_completed=False, starts_at__isnull=False)
        .order_by('-round_number')
        .first()
    )
    if not round_obj:
        return None
    if round_obj.is_paused:
        return round_obj

    remaining = max(
        0,
        round_obj.duration_seconds
        - (timezone.now() - round_obj.starts_at).total_seconds(),
    )
    if remaining <= 0:
        _advance_past(round_obj)
        return None

    round_obj.is_paused = True
    round_obj.paused_at = timezone.now()
    round_obj.paused_remaining_seconds = remaining
    round_obj.save(update_fields=[
        'is_paused', 'paused_at', 'paused_remaining_seconds',
    ])
    return round_obj


@transaction.atomic
def resume_current_round(game):
    """Resume a paused round without consuming its frozen remaining time."""
    round_obj = (
        Round.objects.select_for_update()
        .filter(game=game, is_completed=False, is_paused=True)
        .order_by('-round_number')
        .first()
    )
    if not round_obj:
        return None

    remaining = max(0, round_obj.paused_remaining_seconds or 0)
    round_obj.starts_at = timezone.now() - timezone.timedelta(
        seconds=round_obj.duration_seconds - remaining
    )
    round_obj.is_paused = False
    round_obj.paused_at = None
    round_obj.paused_remaining_seconds = None
    round_obj.save(update_fields=[
        'starts_at', 'is_paused', 'paused_at', 'paused_remaining_seconds',
    ])
    return round_obj


@transaction.atomic
def set_current_round_remaining(game, remaining_seconds):
    """Set the current round's remaining time, preserving pause state."""
    round_obj = (
        Round.objects.select_for_update()
        .filter(game=game, is_completed=False, starts_at__isnull=False)
        .order_by('-round_number')
        .first()
    )
    if not round_obj:
        return None

    remaining = float(remaining_seconds)
    if round_obj.is_paused:
        round_obj.paused_remaining_seconds = remaining
        round_obj.save(update_fields=['paused_remaining_seconds'])
    else:
        round_obj.starts_at = timezone.now() - timezone.timedelta(
            seconds=round_obj.duration_seconds - remaining
        )
        round_obj.save(update_fields=['starts_at'])
    return round_obj


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


@transaction.atomic
def restart_game(game):
    """Reset a game whose rounds are all complete and start round one."""
    locked_game = Game.objects.select_for_update().get(pk=game.pk)
    rounds = Round.objects.filter(game=locked_game)
    if not rounds.exists() or rounds.filter(is_completed=False).exists():
        return None
    final_round = rounds.order_by('-round_number').first()
    if final_round.results_until and timezone.now() < final_round.results_until:
        return None
    if Game.objects.filter(state=Game.State.RUNNING).exclude(pk=locked_game.pk).exists():
        return None

    Action.objects.filter(round__game=locked_game).delete()
    GameScore.objects.filter(game=locked_game).delete()
    Round.objects.filter(game=locked_game).update(
        is_completed=False,
        starts_at=None,
        is_paused=False,
        paused_at=None,
        paused_remaining_seconds=None,
        results_until=None,
        resolved_answer=None,
        consensus_vote_counts={},
    )
    locked_game.state = Game.State.REGISTRATION
    locked_game.save(update_fields=['state'])
    locked_game.memberships.update(eligible_from_round=1)

    return start_game(locked_game)
