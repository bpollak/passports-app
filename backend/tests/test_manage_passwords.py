import importlib.util
import io
import sys
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


def _load_manage_passwords():
    """Load the module with lightweight import fakes and no external dependencies."""
    auth = types.ModuleType("backend.auth")
    auth.hash_password = Mock(name="hash_password")
    auth.verify_password = Mock(name="verify_password")

    seed = types.ModuleType("backend.seed")
    seed.REQUIRED_LOCATIONS = {"csc": "CSC", "bookstore": "Bookstore"}
    seed.get_configured_password_hashes = Mock(
        name="get_configured_password_hashes"
    )

    module_name = "backend._manage_passwords_under_test"
    module_path = Path(__file__).resolve().parents[1] / "manage_passwords.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)

    import_fakes = {
        "backend.auth": auth,
        "backend.seed": seed,
    }
    with patch.dict(sys.modules, import_fakes):
        spec.loader.exec_module(module)
    return module


manage_passwords = _load_manage_passwords()


class PasswordLengthTests(unittest.TestCase):
    def test_ascii_72_byte_boundary_and_overflow(self):
        self.assertIsNone(manage_passwords._password_validation_error("a" * 72))
        self.assertEqual(
            manage_passwords._password_validation_error("a" * 73),
            "Password must be at most 72 UTF-8 bytes",
        )

    def test_unicode_72_byte_boundary_and_overflow(self):
        self.assertEqual(len(("😀" * 18).encode("utf-8")), 72)
        self.assertIsNone(manage_passwords._password_validation_error("😀" * 18))
        self.assertEqual(
            manage_passwords._password_validation_error("😀" * 19),
            "Password must be at most 72 UTF-8 bytes",
        )

    def test_hash_stdin_rejects_overflow_cleanly(self):
        with patch.object(manage_passwords.sys, "stdin", io.StringIO("a" * 73 + "\n")):
            with self.assertRaisesRegex(SystemExit, "at most 72 UTF-8 bytes"):
                manage_passwords.read_password(password_stdin=True)

    def test_change_interactive_reprompts_after_unicode_overflow(self):
        passwords = iter(["😀" * 19, "valid-password", "valid-password"])
        stderr = io.StringIO()

        with patch.object(
            manage_passwords.getpass, "getpass", side_effect=passwords
        ), redirect_stderr(stderr):
            password = manage_passwords.read_new_password(password_stdin=False)

        self.assertEqual(password, "valid-password")
        self.assertIn("Password must be at most 72 UTF-8 bytes", stderr.getvalue())


class ChangePasswordTests(unittest.TestCase):
    def _run_change(
        self, configured_hashes, current_password, new_password, password_hash
    ):
        password_input = io.StringIO(f"{current_password}\n{new_password}\n")
        original_hashes = configured_hashes.copy()

        with patch.object(
            manage_passwords,
            "get_configured_password_hashes",
            return_value=configured_hashes,
        ) as get_hashes, patch.object(
            manage_passwords,
            "verify_password",
            side_effect=lambda candidate, stored: candidate == stored,
        ), patch.object(
            manage_passwords, "hash_password", return_value=password_hash
        ) as hash_password, patch.object(
            manage_passwords.sys, "stdin", password_input
        ):
            result = manage_passwords.change_password("csc", password_stdin=True)

        self.assertEqual(configured_hashes, original_hashes)
        get_hashes.assert_called_once_with()
        return result, hash_password

    def test_duplicate_other_location_password_does_not_change_state(self):
        configured_hashes = {
            "csc": "current-secret",
            "bookstore": "duplicate-secret",
        }
        original_hashes = configured_hashes.copy()

        with self.assertRaisesRegex(
            SystemExit, "already used by another location"
        ), patch.object(
            manage_passwords,
            "get_configured_password_hashes",
            return_value=configured_hashes,
        ), patch.object(
            manage_passwords,
            "verify_password",
            side_effect=lambda candidate, stored: candidate == stored,
        ), patch.object(
            manage_passwords, "hash_password"
        ) as hash_password, patch.object(
            manage_passwords.sys,
            "stdin",
            io.StringIO("current-secret\nduplicate-secret\n"),
        ):
            manage_passwords.change_password("csc", password_stdin=True)

        self.assertEqual(configured_hashes, original_hashes)
        hash_password.assert_not_called()

    def test_unique_password_returns_hash_without_changing_state(self):
        configured_hashes = {
            "csc": "current-secret",
            "bookstore": "other-secret",
        }

        result, hash_password = self._run_change(
            configured_hashes,
            current_password="current-secret",
            new_password="unique-secret",
            password_hash="new-password-hash",
        )

        self.assertEqual(result, "new-password-hash")
        hash_password.assert_called_once_with("unique-secret")

    def test_interactive_current_password_attempt_cap_is_preserved(self):
        configured_hashes = {
            "csc": "correct-secret",
            "bookstore": "other-secret",
        }

        with patch.object(
            manage_passwords,
            "get_configured_password_hashes",
            return_value=configured_hashes,
        ), patch.object(
            manage_passwords,
            "verify_password",
            side_effect=lambda candidate, stored: candidate == stored,
        ), patch.object(
            manage_passwords, "hash_password"
        ) as hash_password, patch.object(
            manage_passwords.getpass,
            "getpass",
            side_effect=["wrong-secret"] * 3,
        ) as getpass, redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(SystemExit, "Aborting after 3 attempts"):
                manage_passwords.change_password("csc", password_stdin=False)

        self.assertEqual(getpass.call_count, 3)
        hash_password.assert_not_called()

    def test_change_command_reports_no_state_change_and_next_steps(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        args = SimpleNamespace(location="csc", password_stdin=False)

        with patch.object(
            manage_passwords, "change_password", return_value="new-password-hash"
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            manage_passwords._change_command(args)

        self.assertEqual(stdout.getvalue().strip(), "new-password-hash")
        message = stderr.getvalue()
        self.assertIn("No state changed", message)
        self.assertIn("LOCATION_CSC_PASSWORD_HASH", message)
        self.assertIn("Kubernetes Secret", message)
        self.assertIn("restart the deployment", message)


if __name__ == "__main__":
    unittest.main()
