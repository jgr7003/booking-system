"""Business constants of the airport and city autocomplete."""


# Length limits of the text typed in the airport autocomplete.
PLACE_QUERY_MIN_LENGTH = 2


PLACE_QUERY_MAX_LENGTH = 50


# Default and maximum number of airport autocomplete suggestions.
PLACE_SUGGESTIONS_DEFAULT = 8


PLACE_SUGGESTIONS_MAX = 20


# Cities suggested at most before the airports, so airports stay visible.
PLACE_MAX_CITIES = 3


# Minimum word similarity (pg_trgm, 0-1) to suggest a misspelled place: "heatrow" → "heathrow" is 0.55.
PLACE_WORD_SIMILARITY_THRESHOLD = 0.5


# Cache of airport suggestions. Bump the version when the cached format changes.
PLACES_CACHE_PREFIX = "airports:v1:"


PLACES_CACHE_TTL_S = 24 * 60 * 60
