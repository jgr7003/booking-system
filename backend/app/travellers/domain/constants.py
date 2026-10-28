"""Business constants of the travellers module."""

# Longest given or family name accepted. Each vertical may impose a stricter limit (airlines
# allow 40 characters for both names together).
MAX_NAME_LENGTH = 60

# Longest identity document number accepted.
MAX_DOCUMENT_NUMBER_LENGTH = 20

# Digits of an E.164 phone number, country code included.
PHONE_MIN_DIGITS = 8

# Digits of an E.164 phone number, country code included.
PHONE_MAX_DIGITS = 15
