import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from section_1_central_mind.auth_service import (
    AuthService,
    AuthenticationError,
)


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = AuthService(Path(self.temp.name) / "private" / "auth.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def bootstrap(self):
        return self.service.bootstrap_admin("first_admin", "A-long-test-password-1")

    def test_registration_disabled_by_default(self):
        with self.assertRaises(AuthenticationError):
            self.service.register("ordinary_user", "A-long-test-password-2")

    def test_bootstrap_only_once(self):
        self.bootstrap()
        with self.assertRaises(AuthenticationError):
            self.service.bootstrap_admin("another_admin", "A-long-test-password-3")

    def test_public_registration_only_creates_user(self):
        self.bootstrap()
        admin = self.service.login("first_admin", "A-long-test-password-1")
        self.service.set_registration_enabled(admin["token"], True)
        result = self.service.register("ordinary_user", "A-long-test-password-2")
        self.assertEqual(result["role"], "user")

    def test_public_registration_cannot_choose_privileged_role(self):
        self.bootstrap()
        admin = self.service.login("first_admin", "A-long-test-password-1")
        self.service.set_registration_enabled(admin["token"], True)
        with self.assertRaises(TypeError):
            self.service.register("ordinary_user", "A-long-test-password-2",
                                  role="administrator")

    def test_wrong_password_is_denied(self):
        self.bootstrap()
        with self.assertRaises(AuthenticationError):
            self.service.login("first_admin", "Wrong-password-123")

    def test_new_login_revokes_previous_session(self):
        self.bootstrap()
        first = self.service.login("first_admin", "A-long-test-password-1")
        second = self.service.login("first_admin", "A-long-test-password-1")
        with self.assertRaises(AuthenticationError):
            self.service.validate_session(first["token"])
        self.assertEqual(
            self.service.validate_session(second["token"])["role"],
            "administrator",
        )

    def test_roles_are_enforced_by_backend(self):
        self.bootstrap()
        admin = self.service.login("first_admin", "A-long-test-password-1")
        self.service.create_account(
            admin["token"], "designated_trainer",
            "A-long-test-password-4", role="trainer"
        )
        trainer = self.service.login(
            "designated_trainer", "A-long-test-password-4"
        )
        with self.assertRaises(AuthenticationError):
            self.service.set_registration_enabled(trainer["token"], True)

    def test_only_one_trainer_can_exist(self):
        self.bootstrap()
        admin = self.service.login("first_admin", "A-long-test-password-1")
        self.service.create_account(
            admin["token"], "designated_trainer",
            "A-long-test-password-4", role="trainer"
        )
        with self.assertRaises(AuthenticationError):
            self.service.create_account(
                admin["token"], "another_trainer",
                "A-long-test-password-5", role="trainer"
            )

    def test_logout_revokes_session(self):
        self.bootstrap()
        session = self.service.login("first_admin", "A-long-test-password-1")
        self.service.logout(session["token"])
        with self.assertRaises(AuthenticationError):
            self.service.validate_session(session["token"])

    def test_audit_is_admin_only(self):
        self.bootstrap()
        admin = self.service.login("first_admin", "A-long-test-password-1")
        self.service.create_account(
            admin["token"], "ordinary_user",
            "A-long-test-password-2", role="user"
        )
        user = self.service.login("ordinary_user", "A-long-test-password-2")
        with self.assertRaises(AuthenticationError):
            self.service.audit_events(user["token"])

    def test_short_password_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service.bootstrap_admin("first_admin", "short")

    def test_duplicate_account_creation_is_denied(self):
        self.bootstrap()
        admin = self.service.login("first_admin", "A-long-test-password-1")
        with self.assertRaises(AuthenticationError):
            self.service.create_account(
                admin["token"], "first_admin",
                "A-long-test-password-2", role="user"
            )


if __name__ == "__main__":
    unittest.main()


class AuthDenialAuditPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = AuthService(
            Path(self.temp.name) / "private" / "auth.sqlite3"
        )
        self.service.bootstrap_admin(
            "first_admin", "A-long-test-password-1"
        )
        self.admin = self.service.login(
            "first_admin", "A-long-test-password-1"
        )

    def tearDown(self):
        self.temp.cleanup()

    def events(self):
        return self.service.audit_events(self.admin["token"], limit=1000)

    def test_denied_login_is_persisted_in_audit(self):
        with self.assertRaises(AuthenticationError):
            self.service.login(
                "first_admin", "Definitely-wrong-password"
            )

        denied = [
            e for e in self.events()
            if e["event"] == "login_denied"
            and e["subject"] == "first_admin"
        ]
        self.assertTrue(denied)

    def test_disabled_registration_denial_is_persisted(self):
        with self.assertRaises(AuthenticationError):
            self.service.register(
                "blocked_user", "A-long-test-password-2"
            )

        denied = [
            e for e in self.events()
            if e["event"] == "registration_denied"
            and e["subject"] == "blocked_user"
        ]
        self.assertTrue(denied)
        self.assertEqual(
            denied[0]["detail"]["reason"],
            "registration_disabled",
        )

    def test_role_authorization_denial_is_persisted(self):
        self.service.create_account(
            self.admin["token"],
            "ordinary_user",
            "A-long-test-password-2",
            role="user",
        )
        user = self.service.login(
            "ordinary_user", "A-long-test-password-2"
        )

        with self.assertRaises(AuthenticationError):
            self.service.set_registration_enabled(
                user["token"], True
            )

        denied = [
            e for e in self.events()
            if e["event"] == "authorization_denied"
            and e["actor"] == "ordinary_user"
        ]
        self.assertTrue(denied)

    def test_second_bootstrap_denial_is_persisted(self):
        with self.assertRaises(AuthenticationError):
            self.service.bootstrap_admin(
                "second_admin", "A-long-test-password-3"
            )

        denied = [
            e for e in self.events()
            if e["event"] == "bootstrap_denied"
            and e["subject"] == "second_admin"
        ]
        self.assertTrue(denied)

    def test_invalid_account_role_denial_is_persisted(self):
        with self.assertRaises(AuthenticationError):
            self.service.create_account(
                self.admin["token"],
                "forbidden_admin",
                "A-long-test-password-6",
                role="administrator",
            )

        denied = [
            e for e in self.events()
            if e["event"] == "account_creation_denied"
            and e["subject"] == "forbidden_admin"
        ]

        self.assertTrue(denied)
        self.assertEqual(
            denied[0]["detail"]["reason"],
            "invalid_role",
        )
        self.assertEqual(
            denied[0]["detail"]["role"],
            "administrator",
        )

    def test_duplicate_account_denial_is_persisted(self):
        with self.assertRaises(AuthenticationError):
            self.service.create_account(
                self.admin["token"],
                "first_admin",
                "A-long-test-password-2",
                role="user",
            )

        denied = [
            e for e in self.events()
            if e["event"] == "account_creation_denied"
            and e["subject"] == "first_admin"
        ]
        self.assertTrue(denied)


class AuthSessionLookupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "private" / "auth.sqlite3"
        self.service = AuthService(self.db_path)
        self.service.bootstrap_admin(
            "first_admin", "A-long-test-password-1"
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_active_token_lookup_index_exists(self):
        import sqlite3

        db = sqlite3.connect(self.db_path)
        try:
            indexes = {
                row[0]
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
            }
        finally:
            db.close()

        self.assertIn("active_token_lookup", indexes)

    def test_valid_session_still_resolves_account(self):
        session = self.service.login(
            "first_admin", "A-long-test-password-1"
        )
        account = self.service.validate_session(session["token"])

        self.assertEqual(account["username"], "first_admin")
        self.assertEqual(account["role"], "administrator")

    def test_random_token_is_denied(self):
        with self.assertRaises(AuthenticationError):
            self.service.validate_session(
                "this-is-not-a-real-session-token"
            )

    def test_previous_token_remains_invalid_after_second_login(self):
        first = self.service.login(
            "first_admin", "A-long-test-password-1"
        )
        second = self.service.login(
            "first_admin", "A-long-test-password-1"
        )

        with self.assertRaises(AuthenticationError):
            self.service.validate_session(first["token"])

        account = self.service.validate_session(second["token"])
        self.assertEqual(account["username"], "first_admin")


class AuthConnectionLifecycleTests(unittest.TestCase):
    def test_auth_operations_emit_no_resource_warning(self):
        import gc
        import warnings

        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "private" / "auth.sqlite3"

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)

                service = AuthService(db_path)
                service.bootstrap_admin(
                    "warning_admin",
                    "A-long-test-password-1",
                )

                first = service.login(
                    "warning_admin",
                    "A-long-test-password-1",
                )
                service.validate_session(first["token"])
                service.registration_enabled()
                service.audit_events(first["token"])

                second = service.login(
                    "warning_admin",
                    "A-long-test-password-1",
                )

                with self.assertRaises(AuthenticationError):
                    service.validate_session(first["token"])

                service.validate_session(second["token"])
                service.logout(second["token"])

                # Force finalization while warning capture is still active.
                gc.collect()

            resource_warnings = [
                warning
                for warning in caught
                if issubclass(warning.category, ResourceWarning)
            ]

            self.assertEqual(
                resource_warnings,
                [],
                [
                    str(warning.message)
                    for warning in resource_warnings
                ],
            )


class RememberedSessionTests(unittest.TestCase):
    def test_remembered_token_survives_service_restart_but_logout_revokes_it(self):
        import time
        from section_1_central_mind.auth_service import AuthService, AuthenticationError
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'auth.sqlite3'
            service = AuthService(database, session_seconds=3600)
            service.bootstrap_admin('remember_admin', 'Long-remember-password-1')
            start = time.time()
            ordinary = service.login('remember_admin', 'Long-remember-password-1')
            remembered = service.login('remember_admin', 'Long-remember-password-1', remember_me=True)
            self.assertAlmostEqual(ordinary['expires_at'] - start, 3600, delta=5)
            self.assertAlmostEqual(remembered['expires_at'] - start, 30 * 86400, delta=5)
            restarted = AuthService(database)
            self.assertEqual(restarted.validate_session(remembered['token'])['username'], 'remember_admin')
            with self.assertRaises(AuthenticationError):
                restarted.validate_session(ordinary['token'])
            restarted.logout(remembered['token'])
            with self.assertRaises(AuthenticationError):
                service.validate_session(remembered['token'])
