from .models import Round, Action, GameScore

def calculate_scores_for_round(round_id):
    """
    Main function to orchestrate the scoring process for a completed round.
    This function should be called when a round ends.
    """
    try:
        round_obj = Round.objects.get(id=round_id)
    except Round.DoesNotExist:
        print(f"Error: Round with id {round_id} not found.")
        return

    if round_obj.is_completed:
        print(f"Error: Round {round_id} has already been scored.")
        return

    game = round_obj.game
    actions = Action.objects.filter(round=round_obj)
    action_map = {action.participant.id: action for action in actions}
    # This dictionary will store the final scores for the round, including bonuses.
    final_round_points = {p_id: 0 for p_id in action_map.keys()}
    # This dictionary will store the base points (pre-bonus) used for delegation calculations.
    base_round_points = {p_id: 0 for p_id in action_map.keys()}

    # --- R4: Detect and Penalize Cycles FIRST ---
    delegation_graph = {
        p_id: action.delegated_to.id
        for p_id, action in action_map.items()
        if action.action_type == Action.ActionType.DELEGATE and action.delegated_to
    }
    all_cycle_members = set()

    # Find all participants who are part of any cycle.
    for p_id in delegation_graph:
        # Avoid re-checking if already identified as part of a cycle
        if p_id in all_cycle_members:
            continue
        path = [p_id]
        current = p_id
        while current in delegation_graph:
            current = delegation_graph[current]
            if current in path:
                cycle_start_index = path.index(current)
                # Penalize all members of the found cycle
                for member_id in path[cycle_start_index:]:
                    base_round_points[member_id] = -1
                    all_cycle_members.add(member_id)
                break 
            path.append(current)
            # Protection against non-existent nodes in buggy data
            if current not in delegation_graph and current not in action_map:
                break
    
    # --- R2: Score terminal actions (Solve/Pass) for non-cycle members ---
    for p_id, action in action_map.items():
        if p_id in all_cycle_members:
            continue

        if action.action_type == Action.ActionType.PASS:
            base_round_points[p_id] = 0
        elif action.action_type == Action.ActionType.SOLVE:
            is_correct = (action.submitted_answer or '').lower() == (round_obj.correct_answer or '').lower()
            action.is_solve_correct = is_correct
            base_round_points[p_id] = 1 if is_correct else -1
    
    # --- R2 (Delegation): Calculate delegation points based on pre-bonus scores ---
    memo = {}
    for p_id in action_map:
        if action_map[p_id].action_type == Action.ActionType.DELEGATE:
            _calculate_delegation_points(p_id, action_map, base_round_points, game, memo, all_cycle_members)

    # All base scores are now calculated. Copy them to the final score map.
    for p_id, points in base_round_points.items():
        final_round_points[p_id] = points

    # --- R3: Apply Reputation Bonus AFTER all base scores are set ---
    trust_counts = {}
    for action in actions:
        if action.action_type == Action.ActionType.DELEGATE and action.delegated_to:
            delegated_to_id = action.delegated_to.id
            trust_counts[delegated_to_id] = trust_counts.get(delegated_to_id, 0) + 1
    
    for p_id, base_points in base_round_points.items():
        # Bonus is only applied if the base score (from solving) is positive.
        if base_points > 0:
            bonus = game.beta_param * trust_counts.get(p_id, 0)
            final_round_points[p_id] += bonus

    # --- Finalize and Save Scores ---
    for p_id, points in final_round_points.items():
        action = action_map[p_id]
        action.points_awarded = points
        action.save()

        score_obj, created = GameScore.objects.get_or_create(
            game=game,
            participant=action.participant
        )
        score_obj.score += points
        score_obj.save()

    round_obj.is_completed = True
    round_obj.save()
    print(f"Scoring for Round {round_id} complete.")


def _calculate_delegation_points(p_id, action_map, base_round_points, game, memo, cycle_members):
    """
    Recursively calculates points for a participant who delegated based on pre-bonus scores.
    Uses memoization to avoid re-calculating scores.
    """
    if p_id in memo:
        return memo[p_id]
    
    if p_id in cycle_members:
        # Base case for cycles is already set to -1 in the main function.
        memo[p_id] = base_round_points[p_id]
        return base_round_points[p_id]

    action = action_map.get(p_id)
    
    # If points are already set (e.g., from Solve/Pass/Cycle), return them.
    if action.action_type != Action.ActionType.DELEGATE:
        return base_round_points.get(p_id, 0)

    # Base case: delegation chain ends unexpectedly.
    if not action.delegated_to or action.delegated_to.id not in action_map:
        base_round_points[p_id] = -1
        memo[p_id] = -1
        return -1

    # Recursive step: get the points of the person who was delegated to.
    delegated_to_id = action.delegated_to.id
    points_j = _calculate_delegation_points(delegated_to_id, action_map, base_round_points, game, memo, cycle_members)
    
    # Apply the scoring rule for delegation (R2)
    final_points = 0
    lambda_param = game.lambda_param
    if points_j > 0:
        final_points = lambda_param * points_j
    elif points_j < 0:
        # This correctly handles chains delegating into a cycle (e.g., points_j = -1)
        final_points = points_j / lambda_param if lambda_param != 0 else points_j
    else: # points_j == 0
        final_points = -1

    base_round_points[p_id] = final_points
    memo[p_id] = final_points
    return final_points


