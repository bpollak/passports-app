import argparse
import getpass
import sys

from .auth import hash_password


MIN_PASSWORD_LENGTH = 12


def read_password(password_stdin: bool) -> str:
    if password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass("Password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate location dashboard password hashes.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    hash_parser = subparsers.add_parser("hash", help="Generate a bcrypt hash for a password.")
    hash_parser.add_argument("--password-stdin", action="store_true")

    args = parser.parse_args()
    password = read_password(args.password_stdin)

    if args.command == "hash":
        print(hash_password(password))


if __name__ == "__main__":
    main()
