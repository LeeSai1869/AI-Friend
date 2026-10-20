from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
CENTRAL = ROOT / "section_1_central_mind"

if str(CENTRAL) not in sys.path:
    sys.path.insert(0, str(CENTRAL))

from auth_service import AuthenticationError
from guard.contract import GuardPrincipal
from server import _guard_principal_from_account


class TrustedPrincipalPropagationTests(unittest.TestCase):

    def test_trusted_account_becomes_authenticated_human_principal(self):
        principal = _guard_principal_from_account({
            "username": "alice.example",
            "role": "trainer",
        })

        self.assertIsInstance(
            principal,
            GuardPrincipal,
        )
        self.assertEqual(
            principal.principal_id,
            "alice.example",
        )
        self.assertEqual(
            principal.kind,
            "human",
        )
        self.assertEqual(
            principal.role,
            "trainer",
        )
        self.assertTrue(
            principal.authenticated,
        )
        self.assertEqual(
            principal.source,
            "auth_service",
        )

    def test_role_is_normalized(self):
        principal = _guard_principal_from_account({
            "username": "admin.example",
            "role": " Administrator ",
        })

        self.assertEqual(
            principal.role,
            "administrator",
        )

    def test_missing_username_fails_closed(self):
        with self.assertRaises(AuthenticationError):
            _guard_principal_from_account({
                "role": "user",
            })

    def test_missing_role_fails_closed(self):
        with self.assertRaises(AuthenticationError):
            _guard_principal_from_account({
                "username": "user.example",
            })

    def test_client_style_role_only_dict_is_not_enough(self):
        with self.assertRaises(AuthenticationError):
            _guard_principal_from_account({
                "role": "administrator",
                "approved_by": "administrator",
            })


if __name__ == "__main__":
    unittest.main()
