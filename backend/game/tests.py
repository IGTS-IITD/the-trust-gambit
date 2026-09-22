from django.core import mail
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from .models import Game, Round, Participant, Action, GameScore, Domain, Lobby
from .scoring import calculate_scores_for_round
from .round_flow import resolve_current_round, start_game, force_advance_current_round

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

        self.assertEqual(current.id, self.round2.id)
        self.assertTrue(Round.objects.get(pk=self.round1.pk).is_completed)
        self.assertEqual(GameScore.objects.get(participant=self.p_a).score, 1)

    def test_cascades_through_multiple_expired_rounds(self):
        start_game(self.game)
        # Both rounds' timers have already elapsed by the time anyone checks.
        self.round1.starts_at = timezone.now() - timezone.timedelta(seconds=200)
        self.round1.save(update_fields=["starts_at"])

        current = resolve_current_round(self.game)

        self.assertIsNone(current)  # game finished, no round 3
        self.assertTrue(Round.objects.get(pk=self.round1.pk).is_completed)
        self.assertTrue(Round.objects.get(pk=self.round2.pk).is_completed)

    def test_force_advance_ends_round_early(self):
        start_game(self.game)
        Action.objects.create(round=self.round1, participant=self.p_a, action_type="SOLVE", submitted_answer="42")

        next_round = force_advance_current_round(self.game)

        self.assertEqual(next_round.id, self.round2.id)
        self.assertTrue(Round.objects.get(pk=self.round1.pk).is_completed)
        self.assertEqual(GameScore.objects.get(participant=self.p_a).score, 1)

    def test_double_resolve_does_not_double_score(self):
        start_game(self.game)
        Action.objects.create(round=self.round1, participant=self.p_a, action_type="SOLVE", submitted_answer="42")
        self.round1.starts_at = timezone.now() - timezone.timedelta(seconds=61)
        self.round1.save(update_fields=["starts_at"])

        resolve_current_round(self.game)
        resolve_current_round(self.game)  # simulates a second concurrent poll

        self.assertEqual(GameScore.objects.get(participant=self.p_a).score, 1)


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

