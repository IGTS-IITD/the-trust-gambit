from django.db import transaction
from django.utils import timezone

from .models import Round
from .scoring import calculate_scores_for_round


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
        # loop again in case the next round's timer has *also* already elapsed


def force_advance_current_round(game):
    """
    Manual override: immediately ends whatever round is currently open
    (regardless of its timer) and starts the next one now. Used for an
    admin "end round early" action. Returns the round that's now current
    (or None if that was the last round).
    """
    round_obj = resolve_current_round(game)
    if not round_obj:
        return None
    _advance_past(round_obj, next_starts_at=timezone.now())
    return resolve_current_round(game)


@transaction.atomic
def _advance_past(round_obj, next_starts_at=None):
    # Lock the row so a near-simultaneous poll from another participant
    # can't score this same round twice.
    locked = Round.objects.select_for_update().get(pk=round_obj.pk)
    if locked.is_completed:
        return

    calculate_scores_for_round(locked.id)

    next_round = Round.objects.filter(
        game=locked.game, round_number=locked.round_number + 1
    ).first()
    if not next_round:
        return

    # Schedule off the ideal end time, not "now", so a detection delay on
    # one round doesn't compound into every later round running late too.
    next_round.starts_at = next_starts_at or (
        locked.starts_at + timezone.timedelta(seconds=locked.duration_seconds)
    )
    next_round.save(update_fields=["starts_at"])


def start_game(game):
    """
    Kicks off round 1 for a game, if it hasn't been started already.
    Returns the started round, or None if there's no round 1 to start or
    the game is already underway.
    """
    if Round.objects.filter(game=game, starts_at__isnull=False).exists():
        return None

    round_one = Round.objects.filter(game=game, round_number=1).first()
    if not round_one:
        return None

    round_one.starts_at = timezone.now()
    round_one.save(update_fields=["starts_at"])
    return round_one
