"""Business constants of the payments module."""

# Prefix of the tokens the simulated card form produces: `tok_fake_<last 4 digits>`. A real
# gateway's tokenization would produce its own tokens; the card number never reaches the backend.
FAKE_TOKEN_PREFIX = "tok_fake_"

# Cards ending in these digits are declined by the simulated gateway, like the test cards of
# real gateways.
FAKE_DECLINED_LAST4 = "0002"

# Cards ending in these digits pass the verification purchase, but the simulated gateway can't
# reverse it: the small charge stays on the card and has to be refunded by hand.
FAKE_REVERSAL_FAILS_LAST4 = "0003"

# Amount of the small purchase that verifies a card, in the currency of the booking. Real gateways
# use their own minimum; it is charged and reversed, so the traveler is never left with it.
VERIFICATION_AMOUNT = "1.00"
