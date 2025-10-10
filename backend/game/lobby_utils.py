import random
from .models import Participant, Lobby, Game

def assign_participants_to_lobbies(lobby_size: int):
    """
    Finds all unassigned participants, shuffles them, and assigns them
    to newly created lobbies of the specified size.
    """
    # Find the main active game
    active_game = Game.objects.filter(is_active=True).first()
    if not active_game:
        return {"error": "No active game found."}

    # Get all participants who are not currently in a lobby
    unassigned_participants = list(Participant.objects.filter(current_lobby__isnull=True))
    
    # Shuffle them for random assignment
    random.shuffle(unassigned_participants)
    
    num_lobbies_created = 0
    total_participants_assigned = 0
    
    # Create lobbies in chunks of lobby_size
    for i in range(0, len(unassigned_participants), lobby_size):
        chunk = unassigned_participants[i:i + lobby_size]
        
        # Create a new lobby
        lobby_number = Lobby.objects.count() + 1
        new_lobby = Lobby.objects.create(
            name=f"Lobby {lobby_number}",
            game=active_game
        )
        num_lobbies_created += 1
        
        # Assign participants in the chunk to the new lobby
        for participant in chunk:
            participant.current_lobby = new_lobby
            participant.save()
            total_participants_assigned += 1
            
    return {
        "status": "Lobby assignment complete.",
        "lobbies_created": num_lobbies_created,
        "participants_assigned": total_participants_assigned
    }