"""Business constants of the flights domain."""

# Airlines don't accept more passengers in a single booking.
MAX_PASSENGERS = 9

# Children up to this age travel as infants and need an adult each.
INFANT_MAX_AGE = 1

# Allowed range for the maximum connections per slice; 0 means direct flights only.
MIN_CONNECTIONS = 0
MAX_CONNECTIONS = 2

# Passengers from this age are adults; younger ones are searched by age.
ADULT_AGE = 18

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
