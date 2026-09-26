import math
from django.db import transaction
from django.db.models import Count
from .models import Participant, Lobby, Game, GameMembership

@transaction.atomic
def register_participant(participant, game):
    """
    Registers a participant for a game (lobby=None).
    If the game is in REGISTRATION state, dynamically scales lobbies if needed.
    """
    locked_game = Game.objects.select_for_update().get(pk=game.pk)
    
    if locked_game.state == Game.State.COMPLETED:
        return {"error": "Cannot register for a completed game."}

    membership, created = GameMembership.objects.get_or_create(
        game=locked_game,
        participant=participant
    )

    if not created:
        return {"status": "Already registered"}

    # Determine eligibility round
    if locked_game.state == Game.State.REGISTRATION:
        eligibility = 1
    else:
        from .models import Round
        current_round = Round.objects.filter(game=locked_game, is_completed=False, starts_at__isnull=False).order_by('-round_number').first()
        eligibility = current_round.round_number + 1 if current_round else 1

    membership.eligible_from_round = eligibility
    membership.save(update_fields=['eligible_from_round'])
    
    if locked_game.state == Game.State.REGISTRATION:
        total_memberships = GameMembership.objects.filter(game=locked_game).count()
        lobby_count = Lobby.objects.filter(game=locked_game).count()
        limit = locked_game.player_limit
        
        # Scale up lobbies if necessary
        required_lobbies = max(1, math.ceil(total_memberships / limit))
        if required_lobbies > lobby_count:
            # Create the missing lobbies
            for i in range(lobby_count + 1, required_lobbies + 1):
                Lobby.objects.create(
                    name=f"{locked_game.name}-Lobby-{i}",
                    game=locked_game,
                    sequence_number=i
                )
    
    return {"status": "Registered successfully (unassigned)"}


def assign_pending_memberships(game, is_game_start=False):
    """
    Complex balancing logic as specified.
    """
    unassigned = list(GameMembership.objects.filter(game=game, lobby__isnull=True).order_by('registered_at'))
    if not unassigned:
        return

    limit = game.player_limit
    all_lobbies = list(Lobby.objects.filter(game=game).annotate(num_members=Count('members')).order_by('sequence_number'))
    
    if not all_lobbies:
        # Failsafe if someone deleted all lobbies manually
        l = Lobby.objects.create(name=f"{game.name}-Lobby-1", game=game, sequence_number=1)
        l.num_members = 0
        all_lobbies = [l]

    if is_game_start:
        # 1. Filter out overfilled lobbies.
        valid_lobbies = [l for l in all_lobbies if l.num_members <= limit]
        if not valid_lobbies:
            # fallback
            valid_lobbies = all_lobbies

        # Distribute all unassigned players across valid lobbies
        for membership in unassigned:
            valid_lobbies.sort(key=lambda x: (x.num_members, x.sequence_number))
            chosen = valid_lobbies[0]
            membership.lobby = chosen
            membership.save(update_fields=['lobby'])
            chosen.num_members += 1

    else:
        # Mid-Round
        if len(unassigned) == 1:
            # Single player goes to lowest absolute lobby
            all_lobbies.sort(key=lambda x: (x.num_members, x.sequence_number))
            chosen = all_lobbies[0]
            unassigned[0].lobby = chosen
            unassigned[0].save(update_fields=['lobby'])
        else:
            # > 1 new players
            available_spots = sum(max(0, limit - l.num_members) for l in all_lobbies)
            
            if len(unassigned) <= available_spots:
                # They fit! Distribute them to valid lobbies
                valid_lobbies = [l for l in all_lobbies if l.num_members < limit]
                for membership in unassigned:
                    valid_lobbies.sort(key=lambda x: (x.num_members, x.sequence_number))
                    chosen = valid_lobbies[0]
                    membership.lobby = chosen
                    membership.save(update_fields=['lobby'])
                    chosen.num_members += 1
            else:
                # They don't fit. Create new lobbies explicitly for them.
                new_lobbies_needed = math.ceil(len(unassigned) / limit)
                max_seq = max((l.sequence_number for l in all_lobbies), default=0)
                
                new_lobbies = []
                for i in range(1, new_lobbies_needed + 1):
                    new_l = Lobby.objects.create(
                        name=f"{game.name}-Lobby-{max_seq + i}",
                        game=game,
                        sequence_number=max_seq + i
                    )
                    new_l.num_members = 0
                    new_lobbies.append(new_l)
                
                # Distribute unassigned players strictly among these new lobbies
                for membership in unassigned:
                    new_lobbies.sort(key=lambda x: (x.num_members, x.sequence_number))
                    chosen = new_lobbies[0]
                    membership.lobby = chosen
                    membership.save(update_fields=['lobby'])
                    chosen.num_members += 1