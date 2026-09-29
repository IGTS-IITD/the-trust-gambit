from django.core import mail
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Count
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from .models import Game, Round, Participant, Action, GameScore, Domain, Lobby, GameMembership
from .scoring import calculate_scores_for_round
from .round_flow import (
    resolve_current_round,
    start_game,
    force_advance_current_round,
    pause_current_round,
    resume_current_round,
    set_current_round_remaining,
    restart_game,
    reset_game_to_registration,
)
from .serializers import ActionSerializer

class ScoringEngineTest(TestCase):

    def setUp(self):
        self.game = Game.objects.create(name="Test Gambit", lambda_param=0.5, beta_param=0.2)
        self.domain = Domain.objects.create(name="Logic Puzzles")
        self.user_a = User.objects.create_user('user_a')
        self.p_a = Participant.objects.create(user=self.user_a)
        self.user_b = User.objects.create_user('user_b')
        self.p_b = Participant.objects.create(user=self.user_b)
        self.user_c = User.objects.create_user('user_c')
        self.p_c = Participant.objects.create(user=self.user_c)

    def test_correct_solve(self):
        round = Round.objects.create(game=self.game, domain=self.domain, round_number=1, question_text="Q1", correct_answer="42")
        Action.objects.create(round=round, participant=self.p_a, action_type='SOLVE', submitted_answer="42")
        calculate_scores_for_round(round.id)
        score = GameScore.objects.get(participant=self.p_a).score
        # A solver with no one delegating to them gets exactly 1 point.
        self.assertEqual(score, 1)

    def test_incorrect_solve(self):
        round = Round.objects.create(game=self.game, domain=self.domain, round_number=1, question_text="Q1", correct_answer="42")
        Action.objects.create(round=round, participant=self.p_a, action_type='SOLVE', submitted_answer="wrong")
        calculate_scores_for_round(round.id)
        score = GameScore.objects.get(participant=self.p_a).score
        self.assertEqual(score, -1)
    
    def test_pass_action(self):
        round = Round.objects.create(game=self.game, domain=self.domain, round_number=1, question_text="Q1", correct_answer="42")
        Action.objects.create(round=round, participant=self.p_a, action_type='PASS')
        calculate_scores_for_round(round.id)
        score = GameScore.objects.get(participant=self.p_a).score
        self.assertEqual(score, 0)

    def test_successful_delegation(self):
        round = Round.objects.create(game=self.game, domain=self.domain, round_number=1, question_text="Q1", correct_answer="ok")
        Action.objects.create(round=round, participant=self.p_a, action_type='DELEGATE', delegated_to=self.p_b)
        Action.objects.create(round=round, participant=self.p_b, action_type='SOLVE', submitted_answer="ok")
        calculate_scores_for_round(round.id)
        
        # B's final score = 1 (base solve) + 0.2 (bonus for 1 trust) = 1.2
        score_b = GameScore.objects.get(participant=self.p_b).score
        self.assertAlmostEqual(score_b, 1.2)

        # A's score is based on B's PRE-BONUS score of 1.
        # score_a = lambda * 1 = 0.5
        score_a = GameScore.objects.get(participant=self.p_a).score
        self.assertAlmostEqual(score_a, 0.5)

    def test_unsuccessful_delegation(self):
        round = Round.objects.create(game=self.game, domain=self.domain, round_number=1, question_text="Q1", correct_answer="ok")
        Action.objects.create(round=round, participant=self.p_a, action_type='DELEGATE', delegated_to=self.p_b)
        Action.objects.create(round=round, participant=self.p_b, action_type='SOLVE', submitted_answer="wrong")
        calculate_scores_for_round(round.id)
        # B's score is -1. No bonus applies.
        score_b = GameScore.objects.get(participant=self.p_b).score
        self.assertEqual(score_b, -1)
        # A's score = B's score / lambda = -1 / 0.5 = -2
        score_a = GameScore.objects.get(participant=self.p_a).score
        self.assertEqual(score_a, -2)

    def test_reputation_bonus(self):
        round = Round.objects.create(game=self.game, domain=self.domain, round_number=1, question_text="Q1", correct_answer="win")
        Action.objects.create(round=round, participant=self.p_b, action_type='DELEGATE', delegated_to=self.p_a)
        Action.objects.create(round=round, participant=self.p_c, action_type='DELEGATE', delegated_to=self.p_a)
        Action.objects.create(round=round, participant=self.p_a, action_type='SOLVE', submitted_answer="win")
        calculate_scores_for_round(round.id)
        # A's final score = 1 (base solve) + 0.4 (bonus for 2 trusts) = 1.4
        score_a = GameScore.objects.get(participant=self.p_a).score
        self.assertAlmostEqual(score_a, 1.4)
    
    def test_delegation_cycle(self):
        round = Round.objects.create(game=self.game, domain=self.domain, round_number=1, question_text="Q1", correct_answer="any")
        Action.objects.create(round=round, participant=self.p_a, action_type='DELEGATE', delegated_to=self.p_b)
        Action.objects.create(round=round, participant=self.p_b, action_type='DELEGATE', delegated_to=self.p_c)
        Action.objects.create(round=round, participant=self.p_c, action_type='DELEGATE', delegated_to=self.p_a)
        calculate_scores_for_round(round.id)
        score_a = GameScore.objects.get(participant=self.p_a).score
        score_b = GameScore.objects.get(participant=self.p_b).score
        score_c = GameScore.objects.get(participant=self.p_c).score
        self.assertEqual(score_a, -1)
        self.assertEqual(score_b, -1)
        self.assertEqual(score_c, -1)

    def test_consensus_majority_sets_answer_at_round_close(self):
        round = Round.objects.create(
            game=self.game,
            domain=self.domain,
            round_number=1,
            question_text="Choose a number",
            question_type=Round.QuestionType.CONSENSUS,
            consensus_mode=Round.ConsensusMode.MAJORITY,
        )
        Action.objects.create(round=round, participant=self.p_a, action_type='SOLVE', submitted_answer="1")
        Action.objects.create(round=round, participant=self.p_b, action_type='SOLVE', submitted_answer="1")
        Action.objects.create(round=round, participant=self.p_c, action_type='SOLVE', submitted_answer="2")

        calculate_scores_for_round(round.id)

        round.refresh_from_db()
        self.assertEqual(round.resolved_answer, "1")
        self.assertEqual(round.consensus_vote_counts, {"1": 2, "2": 1})
        self.assertEqual(GameScore.objects.get(participant=self.p_a).score, 1)
        self.assertEqual(GameScore.objects.get(participant=self.p_b).score, 1)
        self.assertEqual(GameScore.objects.get(participant=self.p_c).score, -1)

    def test_consensus_minority_sets_answer_at_round_close(self):
        round = Round.objects.create(
            game=self.game,
            domain=self.domain,
            round_number=1,
            question_text="Choose a number",
            question_type=Round.QuestionType.CONSENSUS,
            consensus_mode=Round.ConsensusMode.MINORITY,
        )
        Action.objects.create(round=round, participant=self.p_a, action_type='SOLVE', submitted_answer="1")
        Action.objects.create(round=round, participant=self.p_b, action_type='SOLVE', submitted_answer="1")
        Action.objects.create(round=round, participant=self.p_c, action_type='SOLVE', submitted_answer="2")

        calculate_scores_for_round(round.id)

        round.refresh_from_db()
        self.assertEqual(round.resolved_answer, "2")
        self.assertEqual(GameScore.objects.get(participant=self.p_a).score, -1)
        self.assertEqual(GameScore.objects.get(participant=self.p_b).score, -1)
        self.assertEqual(GameScore.objects.get(participant=self.p_c).score, 1)

    def test_delegated_answer_counts_as_consensus_vote(self):
        round = Round.objects.create(
            game=self.game,
            domain=self.domain,
            round_number=1,
            question_text="Choose a number",
            question_type=Round.QuestionType.CONSENSUS,
        )
        Action.objects.create(round=round, participant=self.p_a, action_type='DELEGATE', delegated_to=self.p_b)
        Action.objects.create(round=round, participant=self.p_b, action_type='SOLVE', submitted_answer="2")
        Action.objects.create(round=round, participant=self.p_c, action_type='SOLVE', submitted_answer="1")

        calculate_scores_for_round(round.id)

        round.refresh_from_db()
        self.assertEqual(round.resolved_answer, "2")
        self.assertAlmostEqual(GameScore.objects.get(participant=self.p_a).score, 0.5)
        self.assertAlmostEqual(GameScore.objects.get(participant=self.p_b).score, 1.2)
        self.assertEqual(GameScore.objects.get(participant=self.p_c).score, -1)

    def test_consensus_serializer_rejects_invalid_numeric_choice(self):
        round = Round.objects.create(
            game=self.game,
            domain=self.domain,
            round_number=1,
            question_text="Choose a number",
            question_type=Round.QuestionType.CONSENSUS,
        )
        serializer = ActionSerializer(
            data={"action_type": "SOLVE", "submitted_answer": "9"},
            context={"request": type("Req", (), {"user": type("User", (), {"participant": self.p_a})()})(), "round": round},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("Consensus answers must be one of 1, 2, 3, or 4.", str(serializer.errors["non_field_errors"]))

    def test_consensus_cycle_and_inbound_delegation_are_minus_one(self):
        user_d = User.objects.create_user('user_d')
        participant_d = Participant.objects.create(user=user_d)
        round = Round.objects.create(
            game=self.game,
            domain=self.domain,
            round_number=1,
            question_text="Choose a number",
            question_type=Round.QuestionType.CONSENSUS,
        )
        Action.objects.create(round=round, participant=self.p_a, action_type='DELEGATE', delegated_to=self.p_b)
        Action.objects.create(round=round, participant=self.p_b, action_type='DELEGATE', delegated_to=self.p_a)
        Action.objects.create(round=round, participant=self.p_c, action_type='DELEGATE', delegated_to=self.p_a)
        Action.objects.create(round=round, participant=participant_d, action_type='SOLVE', submitted_answer="3")

        calculate_scores_for_round(round.id)

        round.refresh_from_db()
        self.assertEqual(round.resolved_answer, "3")
        self.assertEqual(GameScore.objects.get(participant=self.p_a).score, -1)
        self.assertEqual(GameScore.objects.get(participant=self.p_b).score, -1)
        self.assertEqual(GameScore.objects.get(participant=self.p_c).score, -1)
        self.assertEqual(GameScore.objects.get(participant=participant_d).score, 1)


class LeaderboardTest(TestCase):
    def test_leaderboard_returns_all_active_game_participants(self):
        game = Game.objects.create(name="Global leaderboard", state=Game.State.RUNNING)
        other_game = Game.objects.create(name="Previous game", state=Game.State.COMPLETED)

        users = [
            User.objects.create_user(f"leaderboard_{index}")
            for index in range(3)
        ]
        participants = [Participant.objects.create(user=user) for user in users]
        for participant in participants:
            GameMembership.objects.create(game=game, participant=participant)
        GameMembership.objects.create(game=other_game, participant=participants[1])

        GameScore.objects.create(game=game, participant=participants[0], score=4)
        GameScore.objects.create(game=other_game, participant=participants[1], score=99)

        token = Token.objects.create(user=users[0])
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = client.get("/api/leaderboard/")

        self.assertEqual(response.status_code, 200)
        scores = {
            row["participant"]["username"]: row["score"]
            for row in response.json()
        }
        self.assertEqual(scores, {
            "leaderboard_0": 4.0,
            "leaderboard_1": 0.0,
            "leaderboard_2": 0.0,
        })

    def test_lobby_scope_returns_only_current_lobby(self):
        game = Game.objects.create(name="Lobby leaderboard")
        lobby = Lobby.objects.create(name="Lobby 1", game=game)
        users = [
            User.objects.create_user(f"lobby_{index}")
            for index in range(3)
        ]
        participants = [Participant.objects.create(user=user) for user in users]
        GameMembership.objects.create(game=game, participant=participants[0], lobby=lobby)
        GameMembership.objects.create(game=game, participant=participants[1], lobby=lobby)
        GameMembership.objects.create(game=game, participant=participants[2])

        token = Token.objects.create(user=users[0])
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = client.get("/api/leaderboard/?scope=lobby")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["participant"]["username"] for row in response.json()],
            ["lobby_0", "lobby_1"],
        )

    def test_leaderboard_shows_scores_after_final_round_completes(self):
        game = Game.objects.create(name="Completed leaderboard")
        domain = Domain.objects.create(name="Final round")
        round_obj = Round.objects.create(
            game=game,
            domain=domain,
            round_number=1,
            question_text="Q1",
            correct_answer="42",
            duration_seconds=60,
        )
        users = [
            User.objects.create_user(f"completed_{index}")
            for index in range(2)
        ]
        participants = [Participant.objects.create(user=user) for user in users]
        for participant in participants:
            GameMembership.objects.create(game=game, participant=participant)

        start_game(game)
        Action.objects.create(
            round=round_obj,
            participant=participants[0],
            action_type=Action.ActionType.SOLVE,
            submitted_answer="42",
        )
        round_obj.starts_at = timezone.now() - timezone.timedelta(seconds=61)
        round_obj.save(update_fields=["starts_at"])

        token = Token.objects.create(user=users[0])
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        global_response = client.get("/api/leaderboard/")
        lobby_response = client.get("/api/leaderboard/?scope=lobby")

        self.assertEqual(global_response.status_code, 200)
        self.assertEqual(lobby_response.status_code, 200)
        self.assertEqual(
            {
                row["participant"]["username"]: row["score"]
                for row in global_response.json()
            },
            {"completed_0": 1.0, "completed_1": 0.0},
        )
        self.assertEqual(
            [row["participant"]["username"] for row in lobby_response.json()],
            ["completed_0", "completed_1"],
        )

    def test_leaderboard_retains_completed_scores_while_next_game_is_registration(self):
        completed_game = Game.objects.create(
            name="Finished standings", state=Game.State.COMPLETED
        )
        next_game = Game.objects.create(name="Next registration")
        user = User.objects.create_user("retained_score")
        participant = Participant.objects.create(user=user)
        GameMembership.objects.create(game=completed_game, participant=participant)
        GameMembership.objects.create(game=next_game, participant=participant)
        GameScore.objects.create(game=completed_game, participant=participant, score=17)

        token = Token.objects.create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = client.get("/api/leaderboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["score"], 17.0)

    def test_leaderboard_reset_is_explicit_and_admin_only(self):
        game = Game.objects.create(name="Reset standings")
        user = User.objects.create_user("reset_score")
        participant = Participant.objects.create(user=user)
        GameMembership.objects.create(game=game, participant=participant)
        GameScore.objects.create(game=game, participant=participant, score=8)

        user_token = Token.objects.create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {user_token.key}")
        denied = client.post("/api/admin/reset-leaderboard/", {"game_id": game.id})
        self.assertEqual(denied.status_code, 403)

        admin = User.objects.create_superuser("reset_admin", password="password")
        admin_token = Token.objects.create(user=admin)
        client.credentials(HTTP_AUTHORIZATION=f"Token {admin_token.key}")
        response = client.post("/api/admin/reset-leaderboard/", {"game_id": game.id})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(GameScore.objects.filter(game=game).exists())


class SubmitActionTest(TestCase):
    def test_submit_action_uses_running_game_over_older_registration_game(self):
        Game.objects.create(name="Older registration game")
        game = Game.objects.create(name="Running game")
        domain = Domain.objects.create(name="Submit action")
        round_obj = Round.objects.create(
            game=game,
            domain=domain,
            round_number=1,
            question_text="Q1",
            correct_answer="42",
        )
        user = User.objects.create_user("submitter")
        participant = Participant.objects.create(user=user)
        GameMembership.objects.create(game=game, participant=participant)
        start_game(game)

        token = Token.objects.create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = client.post(
            "/api/submit-action/",
            {"action_type": Action.ActionType.SOLVE, "submitted_answer": "42"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Action.objects.filter(
                round=round_obj,
                participant=participant,
                submitted_answer="42",
            ).exists()
        )


class ProfileScoreTest(TestCase):
    def test_profile_score_is_limited_to_current_game(self):
        old_game = Game.objects.create(
            name="Old game", state=Game.State.COMPLETED
        )
        active_game = Game.objects.create(
            name="Active game", state=Game.State.RUNNING
        )
        user = User.objects.create_user("profile_score")
        participant = Participant.objects.create(user=user)
        GameMembership.objects.create(game=active_game, participant=participant)
        GameScore.objects.create(game=old_game, participant=participant, score=99)
        GameScore.objects.create(game=active_game, participant=participant, score=4)

        token = Token.objects.create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = client.get("/api/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_score"], 4.0)

    def test_submit_action_is_rejected_while_game_is_paused(self):
        game = Game.objects.create(name="Paused game")
        domain = Domain.objects.create(name="Paused submit")
        round_obj = Round.objects.create(
            game=game, domain=domain, round_number=1,
            question_text="Q1", correct_answer="42",
        )
        user = User.objects.create_user("paused_submitter")
        participant = Participant.objects.create(user=user)
        GameMembership.objects.create(game=game, participant=participant)
        start_game(game)
        pause_current_round(game)

        token = Token.objects.create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = client.post(
            "/api/submit-action/",
            {"action_type": Action.ActionType.SOLVE, "submitted_answer": "42"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("paused", str(response.json()).lower())


class AdminTimingTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            "timing_admin", "timing@example.com", "password"
        )
        self.game = Game.objects.create(name="Admin timing")
        domain = Domain.objects.create(name="Admin timing domain")
        self.round = Round.objects.create(
            game=self.game, domain=domain, round_number=1,
            question_text="Q1", correct_answer="42",
        )
        self.client = APIClient()
        start_game(self.game)

    def test_admin_can_pause_resume_and_retime_current_round(self):
        token = Token.objects.create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        pause_response = self.client.post("/api/admin/pause-game/")
        self.assertEqual(pause_response.status_code, 200)
        self.round.refresh_from_db()
        self.assertTrue(self.round.is_paused)

        time_response = self.client.post(
            "/api/admin/set-round-time/",
            {"remaining_seconds": 15},
        )
        self.assertEqual(time_response.status_code, 200)
        self.round.refresh_from_db()
        self.assertEqual(self.round.paused_remaining_seconds, 15)

        resume_response = self.client.post("/api/admin/resume-game/")
        self.assertEqual(resume_response.status_code, 200)
        self.round.refresh_from_db()
        self.assertFalse(self.round.is_paused)

    def test_admin_can_restart_completed_game(self):
        force_advance_current_round(self.game)
        final_round = Round.objects.get(game=self.game, round_number=1)
        final_round.results_until = timezone.now() - timezone.timedelta(seconds=1)
        final_round.save(update_fields=['results_until'])
        self.game.refresh_from_db()
        resolve_current_round(self.game)
        self.game.refresh_from_db()
        self.assertEqual(self.game.state, Game.State.COMPLETED)

        token = Token.objects.create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post(
            "/api/admin/restart-game/",
            {"game_id": self.game.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.game.refresh_from_db()
        self.assertEqual(self.game.state, Game.State.RUNNING)

    def test_admin_can_reset_running_game_to_registration(self):
        user = User.objects.create_user("reset_player")
        participant = Participant.objects.create(user=user)
        membership = GameMembership.objects.create(
            game=self.game, participant=participant
        )
        start_game(self.game)
        Action.objects.create(
            round=self.round,
            participant=participant,
            action_type=Action.ActionType.PASS,
        )
        GameScore.objects.create(game=self.game, participant=participant, score=5)

        token = Token.objects.create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post(
            "/api/admin/reset-game/",
            {"game_id": self.game.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.game.refresh_from_db()
        self.round.refresh_from_db()
        membership.refresh_from_db()
        self.assertEqual(self.game.state, Game.State.REGISTRATION)
        self.assertIsNone(self.round.starts_at)
        self.assertFalse(Action.objects.filter(round=self.round).exists())
        self.assertFalse(GameScore.objects.filter(game=self.game).exists())
        self.assertIsNone(membership.lobby)
        self.assertEqual(Lobby.objects.filter(game=self.game).count(), 0)


class RoundResultsTest(TestCase):
    def test_completed_round_results_include_personal_breakdown(self):
        game = Game.objects.create(name="Results game", beta_param=0.2)
        domain = Domain.objects.create(name="Results")
        round_obj = Round.objects.create(
            game=game,
            domain=domain,
            round_number=1,
            question_text="Q1",
            correct_answer="42",
            answer_explanation="The answer follows from the stated constraint.",
        )
        user_a = User.objects.create_user("results_a")
        user_b = User.objects.create_user("results_b")
        participant_a = Participant.objects.create(user=user_a)
        participant_b = Participant.objects.create(user=user_b)
        lobby = Lobby.objects.create(name="Results lobby", game=game)
        for participant in (participant_a, participant_b):
            GameMembership.objects.create(game=game, participant=participant, lobby=lobby)

        start_game(game)
        Action.objects.create(
            round=round_obj,
            participant=participant_a,
            action_type=Action.ActionType.SOLVE,
            submitted_answer="42",
        )
        Action.objects.create(
            round=round_obj,
            participant=participant_b,
            action_type=Action.ActionType.DELEGATE,
            delegated_to=participant_a,
        )
        force_advance_current_round(game)

        token = Token.objects.create(user=user_a)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = client.get(f"/api/rounds/{round_obj.id}/results/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["correct_answer"], "42")
        self.assertEqual(payload["answer_explanation"], round_obj.answer_explanation)
        result_by_name = {
            row["participant"]["username"]: row for row in payload["participants"]
        }
        self.assertEqual(result_by_name["results_a"]["points_awarded"], 1.2)
        self.assertEqual(result_by_name["results_a"]["delegated_to_me"], 1)
        self.assertAlmostEqual(result_by_name["results_a"]["reputation_bonus"], 0.2)
        self.assertEqual(result_by_name["results_b"]["points_awarded"], 0.5)

        current_response = client.get("/api/current-round/")
        self.assertEqual(current_response.status_code, 200)
        self.assertIsNone(current_response.json()["current_round"])
        self.assertEqual(current_response.json()["last_completed_round_id"], round_obj.id)
        self.assertEqual(
            current_response.json()["last_completed_round_results"]["correct_answer"],
            "42",
        )

    def test_results_are_unavailable_before_round_completion(self):
        game = Game.objects.create(name="Incomplete results")
        domain = Domain.objects.create(name="Incomplete")
        round_obj = Round.objects.create(
            game=game, domain=domain, round_number=1, question_text="Q1",
        )
        user = User.objects.create_user("incomplete_results")
        participant = Participant.objects.create(user=user)
        lobby = Lobby.objects.create(name="Incomplete lobby", game=game)
        GameMembership.objects.create(
            game=game, participant=participant, lobby=lobby
        )
        token = Token.objects.create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = client.get(f"/api/rounds/{round_obj.id}/results/")

        self.assertEqual(response.status_code, 409)


class LobbyLifecycleTest(TestCase):
    def test_lobbies_are_created_only_when_game_starts(self):
        game = Game.objects.create(name="Deferred lobbies", player_limit=2)
        domain = Domain.objects.create(name="Lifecycle")
        Round.objects.create(
            game=game,
            domain=domain,
            round_number=1,
            question_text="Question",
        )
        participants = [
            Participant.objects.create(
                user=User.objects.create_user(f"lifecycle_{index}")
            )
            for index in range(3)
        ]
        for participant in participants:
            GameMembership.objects.create(game=game, participant=participant)

        self.assertEqual(Lobby.objects.filter(game=game).count(), 0)

        start_game(game)

        self.assertEqual(Lobby.objects.filter(game=game).count(), 2)
        self.assertEqual(
            GameMembership.objects.filter(game=game, lobby__isnull=False).count(),
            3,
        )

    def test_players_are_distributed_evenly_for_any_limit(self):
        game = Game.objects.create(name="Balanced lobbies", player_limit=10)
        domain = Domain.objects.create(name="Balance")
        Round.objects.create(
            game=game,
            domain=domain,
            round_number=1,
            question_text="Question",
        )
        for index in range(21):
            participant = Participant.objects.create(
                user=User.objects.create_user(f"balanced_{index}")
            )
            GameMembership.objects.create(game=game, participant=participant)

        start_game(game)

        lobby_sizes = list(
            Lobby.objects.filter(game=game)
            .annotate(num_members=Count('members'))
            .values_list('num_members', flat=True)
        )
        self.assertEqual(len(lobby_sizes), 3)
        self.assertEqual(lobby_sizes, [7] * 3)


class LobbyAdminTest(TestCase):
    def test_admin_can_assign_unassigned_participants(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "password")
        Game.objects.create(name="Active game")
        for index in range(3):
            Participant.objects.create(user=User.objects.create_user(f"player_{index}"))

        self.client.force_login(admin_user)
        response = self.client.post(
            "/admin/game/participant/assign-lobbies/",
            {"lobby_size": 2},
        )

        self.assertRedirects(response, "/admin/game/participant/", fetch_redirect_response=False)
        self.assertEqual(Lobby.objects.count(), 2)
        self.assertEqual(Participant.objects.filter(current_lobby__isnull=False).count(), 3)


class RoundFlowTest(TestCase):
    def setUp(self):
        self.game = Game.objects.create(name="Timer Gambit", lambda_param=0.5, beta_param=0.2)
        self.domain = Domain.objects.create(name="Logic Puzzles")
        self.p_a = Participant.objects.create(user=User.objects.create_user("flow_a"))
        self.p_b = Participant.objects.create(user=User.objects.create_user("flow_b"))
        self.round1 = Round.objects.create(
            game=self.game, domain=self.domain, round_number=1,
            question_text="Q1", correct_answer="42", duration_seconds=60,
        )
        self.round2 = Round.objects.create(
            game=self.game, domain=self.domain, round_number=2,
            question_text="Q2", correct_answer="7", duration_seconds=60,
        )

    def end_results_window(self, round_obj):
        round_obj.refresh_from_db()
        round_obj.results_until = timezone.now() - timezone.timedelta(seconds=1)
        round_obj.save(update_fields=['results_until'])
        self.game.refresh_from_db()
        return resolve_current_round(self.game)

    def test_no_current_round_before_game_starts(self):
        self.assertIsNone(resolve_current_round(self.game))

    def test_start_game_opens_round_one(self):
        started = start_game(self.game)
        self.assertEqual(started.round_number, 1)
        current = resolve_current_round(self.game)
        self.assertEqual(current.id, self.round1.id)

    def test_start_game_is_idempotent(self):
        start_game(self.game)
        second_call = start_game(self.game)
        self.assertIsNone(second_call)

    def test_round_within_timer_is_not_advanced(self):
        start_game(self.game)
        current = resolve_current_round(self.game)
        self.assertEqual(current.round_number, 1)
        self.assertFalse(Round.objects.get(pk=self.round1.pk).is_completed)

    def test_expired_round_is_scored_and_advances(self):
        start_game(self.game)
        Action.objects.create(round=self.round1, participant=self.p_a, action_type="SOLVE", submitted_answer="42")

        # Simulate the timer having run out.
        self.round1.starts_at = timezone.now() - timezone.timedelta(seconds=61)
        self.round1.save(update_fields=["starts_at"])

        current = resolve_current_round(self.game)

        self.assertIsNone(current)
        current = self.end_results_window(self.round1)

        self.assertEqual(current.id, self.round2.id)
        self.assertTrue(Round.objects.get(pk=self.round1.pk).is_completed)
        self.assertEqual(GameScore.objects.get(participant=self.p_a).score, 1)

    def test_cascades_through_multiple_expired_rounds(self):
        start_game(self.game)
        # Both rounds' timers have already elapsed by the time anyone checks.
        self.round1.starts_at = timezone.now() - timezone.timedelta(seconds=200)
        self.round1.save(update_fields=["starts_at"])

        current = resolve_current_round(self.game)

        self.assertIsNone(current)  # results window for round 1
        self.assertTrue(Round.objects.get(pk=self.round1.pk).is_completed)

        self.end_results_window(self.round1)
        self.round2.starts_at = timezone.now() - timezone.timedelta(seconds=61)
        self.round2.save(update_fields=['starts_at'])
        self.assertIsNone(resolve_current_round(self.game))
        self.end_results_window(self.round2)
        self.assertTrue(Round.objects.get(pk=self.round2.pk).is_completed)

    def test_force_advance_ends_round_early(self):
        start_game(self.game)
        Action.objects.create(round=self.round1, participant=self.p_a, action_type="SOLVE", submitted_answer="42")

        next_round = force_advance_current_round(self.game)

        self.assertIsNone(next_round)
        self.assertTrue(Round.objects.get(pk=self.round1.pk).is_completed)
        self.assertEqual(GameScore.objects.get(participant=self.p_a).score, 1)

        next_round = self.end_results_window(self.round1)
        self.assertEqual(next_round.id, self.round2.id)

    def test_double_resolve_does_not_double_score(self):
        start_game(self.game)
        Action.objects.create(round=self.round1, participant=self.p_a, action_type="SOLVE", submitted_answer="42")
        self.round1.starts_at = timezone.now() - timezone.timedelta(seconds=61)
        self.round1.save(update_fields=["starts_at"])

        resolve_current_round(self.game)
        resolve_current_round(self.game)  # simulates a second concurrent poll

        self.assertEqual(GameScore.objects.get(participant=self.p_a).score, 1)

    def test_pause_freezes_round_and_resume_preserves_remaining_time(self):
        start_game(self.game)
        self.round1.starts_at = timezone.now() - timezone.timedelta(seconds=20)
        self.round1.save(update_fields=["starts_at"])

        paused = pause_current_round(self.game)
        self.assertTrue(paused.is_paused)
        self.assertGreater(paused.paused_remaining_seconds, 39)
        self.assertLess(paused.paused_remaining_seconds, 41)
        self.assertEqual(resolve_current_round(self.game).id, self.round1.id)

        resumed = resume_current_round(self.game)
        self.assertFalse(resumed.is_paused)
        remaining = resumed.duration_seconds - (
            timezone.now() - resumed.starts_at
        ).total_seconds()
        self.assertGreater(remaining, 39)
        self.assertLess(remaining, 41)

    def test_set_current_round_remaining_works_while_running_or_paused(self):
        start_game(self.game)
        updated = set_current_round_remaining(self.game, 25)
        self.assertAlmostEqual(
            updated.duration_seconds - (timezone.now() - updated.starts_at).total_seconds(),
            25,
            delta=0.5,
        )

        paused = pause_current_round(self.game)
        updated = set_current_round_remaining(self.game, 15)
        self.assertEqual(updated.id, paused.id)
        self.assertEqual(updated.paused_remaining_seconds, 15)

    def test_restart_completed_game_resets_scores_and_preserves_lobby(self):
        GameMembership.objects.create(game=self.game, participant=self.p_a)
        start_game(self.game)
        lobby_id = GameMembership.objects.get(
            game=self.game, participant=self.p_a
        ).lobby_id
        Action.objects.create(
            round=self.round1,
            participant=self.p_a,
            action_type=Action.ActionType.SOLVE,
            submitted_answer="42",
        )
        force_advance_current_round(self.game)
        self.end_results_window(self.round1)
        force_advance_current_round(self.game)

        final_round = Round.objects.get(game=self.game, round_number=2)
        final_round.results_until = timezone.now() - timezone.timedelta(seconds=1)
        final_round.save(update_fields=['results_until'])
        self.game.refresh_from_db()
        resolve_current_round(self.game)
        self.game.refresh_from_db()
        self.assertEqual(self.game.state, Game.State.COMPLETED)
        self.assertTrue(GameScore.objects.filter(game=self.game).exists())

        restarted_round = restart_game(self.game)

        self.assertEqual(restarted_round.id, self.round1.id)
        self.game.refresh_from_db()
        self.round1.refresh_from_db()
        self.assertEqual(self.game.state, Game.State.RUNNING)
        self.assertFalse(self.round1.is_completed)
        self.assertIsNotNone(self.round1.starts_at)
        self.assertFalse(Action.objects.filter(round__game=self.game).exists())
        self.assertFalse(GameScore.objects.filter(game=self.game).exists())
        self.assertEqual(
            GameMembership.objects.get(
                game=self.game, participant=self.p_a
            ).lobby_id,
            lobby_id,
        )

    def test_restart_uses_completed_rounds_even_if_game_state_is_still_running(self):
        start_game(self.game)
        force_advance_current_round(self.game)
        self.end_results_window(self.round1)
        force_advance_current_round(self.game)
        self.end_results_window(self.round2)
        self.game.state = Game.State.RUNNING
        self.game.save(update_fields=['state'])

        restarted_round = restart_game(self.game)

        self.assertEqual(restarted_round.id, self.round1.id)
        self.game.refresh_from_db()
        self.assertEqual(self.game.state, Game.State.RUNNING)

    def test_final_round_keeps_game_running_during_results_window(self):
        start_game(self.game)
        force_advance_current_round(self.game)
        self.end_results_window(self.round1)
        force_advance_current_round(self.game)

        self.game.refresh_from_db()
        final_round = Round.objects.get(game=self.game, round_number=2)
        self.assertEqual(self.game.state, Game.State.RUNNING)
        self.assertGreater(final_round.results_until, timezone.now())
        self.assertIsNone(resolve_current_round(self.game))

        final_round.results_until = timezone.now() - timezone.timedelta(seconds=1)
        final_round.save(update_fields=['results_until'])
        resolve_current_round(self.game)
        self.game.refresh_from_db()
        self.assertEqual(self.game.state, Game.State.COMPLETED)


class AdminStartGameTest(TestCase):
    def test_admin_can_start_round_one(self):
        admin_user = User.objects.create_superuser("game_admin", "game_admin@example.com", "password")
        game = Game.objects.create(name="Button-started game")
        domain = Domain.objects.create(name="Trivia")
        Round.objects.create(game=game, domain=domain, round_number=1, question_text="Q1", correct_answer="1", duration_seconds=60)

        self.client.force_login(admin_user)
        response = self.client.post("/admin/game/game/start-game/")

        self.assertRedirects(response, "/admin/game/game/", fetch_redirect_response=False)
        self.assertIsNotNone(Round.objects.get(game=game, round_number=1).starts_at)


class EmailVerificationTest(TestCase):
    def register(self, username="verify_user", email="verify_user@example.com", password="StrongPass123!"):
        return self.client.post("/api/register/", {
            "username": username, "email": email, "password": password,
        }, content_type="application/json")

    def test_registration_creates_inactive_user_and_sends_email(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)
        self.assertNotIn("token", response.json())  # can't log in yet
        user = User.objects.get(username="verify_user")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.email, mail.outbox[0].to)

    def test_cannot_login_before_verifying(self):
        self.register()
        response = self.client.post("/api/login/", {
            "username": "verify_user", "password": "StrongPass123!",
        }, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json().get("unverified"))

    def test_verify_email_activates_and_returns_usable_token(self):
        self.register()
        user = User.objects.get(username="verify_user")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.post("/api/verify-email/", {"uid": uid, "token": token}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.json())
        user.refresh_from_db()
        self.assertTrue(user.is_active)

        login_response = self.client.post("/api/login/", {
            "username": "verify_user", "password": "StrongPass123!",
        }, content_type="application/json")
        self.assertEqual(login_response.status_code, 200)

    def test_invalid_token_rejected(self):
        self.register()
        user = User.objects.get(username="verify_user")
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        response = self.client.post("/api/verify-email/", {"uid": uid, "token": "not-a-real-token"}, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_disposable_email_rejected(self):
        response = self.register(email="someone@mailinator.com")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="someone@mailinator.com").exists())

    def test_duplicate_verified_email_rejected(self):
        self.register(username="first_user", email="dup@example.com")
        user = User.objects.get(username="first_user")
        user.is_active = True
        user.save()

        response = self.register(username="second_user", email="dup@example.com")
        self.assertEqual(response.status_code, 400)

    def test_unverified_registration_can_be_retried(self):
        first = self.register(username="retry_user", email="retry@example.com")
        self.assertEqual(first.status_code, 201)
        first_user_id = User.objects.get(username="retry_user").id

        second = self.register(username="retry_user", email="retry@example.com")

        self.assertEqual(second.status_code, 201)
        # The stale unverified account was replaced, not duplicated.
        self.assertEqual(User.objects.filter(username="retry_user").count(), 1)
        self.assertNotEqual(User.objects.get(username="retry_user").id, first_user_id)

    def test_resend_verification_sends_another_email(self):
        self.register()
        response = self.client.post("/api/resend-verification/", {"email": "verify_user@example.com"}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)  # original + resend

    def test_resend_does_not_leak_whether_email_exists(self):
        known = self.client.post("/api/resend-verification/", {"email": "nobody@example.com"}, content_type="application/json")
        self.register()
        registered = self.client.post("/api/resend-verification/", {"email": "verify_user@example.com"}, content_type="application/json")

        self.assertEqual(known.status_code, 200)
        self.assertEqual(known.json(), registered.json())

