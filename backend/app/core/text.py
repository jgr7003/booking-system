"""Text helpers shared by every module."""

import re
import unicodedata

_SPACES = re.compile(r"\s+")


def normalize_search_text(value: str) -> str:
    """Normalizes text for searching: no accents, lower case, single spaces.

    Args:
        value: Free text, e.g. `"  Zürich   Airport"`.

    Returns:
        The normalized text, e.g. `"zurich airport"`.
    """
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _SPACES.sub(" ", without_accents).strip().lower()
