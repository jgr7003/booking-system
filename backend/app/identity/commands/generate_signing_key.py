"""Prints new keys of the identity module, ready to paste into `backend/.env`.

`AUTH_SIGNING_KEYS` signs the access tokens; `IDENTITY_SECRETS_KEY` encrypts the client secrets
of identity providers. It never writes them anywhere: they must not reach the repository::

    make auth-keygen
    python -m app.identity.commands.generate_signing_key [--kid 2026-10]

To rotate the signing key, put the new one first in `AUTH_SIGNING_KEYS` and keep the old one
after it until the tokens it signed expire (10 minutes).
"""

import argparse
import json
import sys
from datetime import UTC, datetime

from app.identity.services.secrets import generate_secrets_key
from app.identity.tokens.signing import generate_signing_key


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Arguments, without the program name; `sys.argv` if omitted.

    Returns:
        The exit code.
    """
    parser = argparse.ArgumentParser(description="Prints new AUTH_SIGNING_KEYS and IDENTITY_SECRETS_KEY.")
    parser.add_argument("--kid", default=datetime.now(UTC).strftime("%Y-%m-%d"), help="Id of the key")
    args = parser.parse_args(argv)
    print(f"AUTH_SIGNING_KEYS='{json.dumps([generate_signing_key(args.kid)])}'")
    print(f"IDENTITY_SECRETS_KEY={generate_secrets_key()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
