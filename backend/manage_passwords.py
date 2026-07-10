import argparse
import getpass
import sys

from .auth import hash_password, verify_password
from .seed import REQUIRED_LOCATIONS, get_configured_password_hashes


MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_BYTES = 72
MAX_CURRENT_PASSWORD_ATTEMPTS = 3


def _bcrypt_password_validation_error(password: str) -> str | None:
    try:
        password_bytes = password.encode("utf-8")
    except UnicodeEncodeError:
        return "Password must contain valid UTF-8 characters"
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        return f"Password must be at most {MAX_PASSWORD_BYTES} UTF-8 bytes"
    return None


def _password_validation_error(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    return _bcrypt_password_validation_error(password)


def read_password(password_stdin: bool, prompt: str = "Password: ") -> str:
    if password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass(prompt)
    error = _password_validation_error(password)
    if error:
        raise SystemExit(error)
    return password


def read_new_password(password_stdin: bool) -> str:
    if password_stdin:
        password = sys.stdin.readline().rstrip("\n")
        error = _password_validation_error(password)
        if error:
            raise SystemExit(error)
        return password

    while True:
        password = getpass.getpass("New password: ")
        error = _password_validation_error(password)
        if error:
            print(error, file=sys.stderr)
            continue
        confirm = getpass.getpass("Confirm new password: ")
        if password != confirm:
            print("Passwords do not match. Try again.", file=sys.stderr)
            continue
        return password


def change_password(loc_id: str, password_stdin: bool) -> str:
    """Verify the configured password and return a replacement hash."""
    configured_hashes = get_configured_password_hashes()
    try:
        current_hash = configured_hashes[loc_id]
    except KeyError:
        raise SystemExit(
            f"Location '{loc_id}' has no configured password hash."
        ) from None

    if password_stdin:
        current = sys.stdin.readline().rstrip("\n")
        error = _bcrypt_password_validation_error(current)
        if error:
            raise SystemExit(error)
        if not verify_password(current, current_hash):
            raise SystemExit("Current password is incorrect.")
    else:
        for attempt in range(1, MAX_CURRENT_PASSWORD_ATTEMPTS + 1):
            current = getpass.getpass("Current password: ")
            error = _bcrypt_password_validation_error(current)
            if error:
                raise SystemExit(error)
            if verify_password(current, current_hash):
                break
            remaining = MAX_CURRENT_PASSWORD_ATTEMPTS - attempt
            if remaining > 0:
                print(
                    f"Incorrect password. {remaining} attempt(s) remaining.",
                    file=sys.stderr,
                )
            else:
                raise SystemExit(
                    "Current password is incorrect. Aborting after "
                    f"{MAX_CURRENT_PASSWORD_ATTEMPTS} attempts."
                )

    new_password = read_new_password(password_stdin)
    for other_loc_id, other_hash in configured_hashes.items():
        if other_loc_id != loc_id and verify_password(new_password, other_hash):
            raise SystemExit(
                "New password is already used by another location. "
                "Choose a unique password."
            )
    return hash_password(new_password)


def _hash_command(args) -> None:
    password = read_password(args.password_stdin)
    print(hash_password(password))


def _change_command(args) -> None:
    new_hash = change_password(args.location, args.password_stdin)
    env_var = f"LOCATION_{args.location.upper()}_PASSWORD_HASH"
    print(file=sys.stderr)
    print(
        "No state changed: this command did not modify the database, environment, "
        "or Kubernetes Secret.",
        file=sys.stderr,
    )
    print(
        f"Patch {env_var} in your environment / Kubernetes Secret with the hash below,",
        file=sys.stderr,
    )
    print(
        "then restart the deployment for the new password to take effect.",
        file=sys.stderr,
    )
    print(file=sys.stderr)
    print(new_hash)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage location dashboard passwords.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    hash_parser = subparsers.add_parser(
        "hash", help="Generate a bcrypt hash for a password."
    )
    hash_parser.add_argument("--password-stdin", action="store_true")
    hash_parser.set_defaults(func=_hash_command)

    change_parser = subparsers.add_parser(
        "change",
        help="Verify a location's current configured password and print a "
        "replacement bcrypt hash. Does not modify any state.",
    )
    change_parser.add_argument(
        "--location",
        required=True,
        choices=sorted(REQUIRED_LOCATIONS.keys()),
        help="Location whose password to change.",
    )
    change_parser.add_argument("--password-stdin", action="store_true")
    change_parser.set_defaults(func=_change_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
