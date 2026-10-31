"""Validated types of sign in through a provider."""

from typing import Annotated

from pydantic import AfterValidator


def _return_to(value: str) -> str:
    """Accepts only a path of this app, so the sign in can't redirect anywhere else (open redirect)."""
    if not value.startswith("/") or value.startswith("//") or "\\" in value or len(value) > 500:
        raise ValueError("Only a path of this app is accepted, e.g. `/trip`.")
    if any(ord(c) < 32 for c in value):
        raise ValueError("Only a path of this app is accepted, e.g. `/trip`.")
    return value


# Path of the app to go back to after signing in, e.g. `/checkout/abc`.
ReturnTo = Annotated[str, AfterValidator(_return_to)]
