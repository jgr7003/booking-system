"""Business constants of passwords, email links and sign-in limits."""

from datetime import timedelta

# Shortest password accepted. Length matters more than mixing kinds of characters (NIST SP 800-63B).
MIN_PASSWORD_LENGTH = 10

# Longest password accepted; Argon2 doesn't need a limit, but a huge body is refused early.
MAX_PASSWORD_LENGTH = 128

# Lifetime of the link that verifies the email of a new account.
VERIFY_EMAIL_TTL = timedelta(hours=48)

# Lifetime of the link that sets the first password (accounts created by SSO or by an organization).
SET_PASSWORD_TTL = timedelta(days=7)

# Lifetime of the link that resets a forgotten password.
RESET_PASSWORD_TTL = timedelta(minutes=30)

# Path of the web app that opens the link to verify the email; the email adds `?token=...`.
VERIFY_EMAIL_PATH = "/account/verify-email"

# Path of the web app that opens the links to set or reset the password (`?token=...&kind=set|reset`).
SET_PASSWORD_PATH = "/account/password"

# Sign ups and password emails allowed per address in `ATTEMPT_WINDOW`.
ATTEMPTS_PER_IP = 60

# Emails with links allowed per address of the user in `ATTEMPT_WINDOW` (sign up, forgot, resend).
EMAILS_PER_ADDRESS = 5

# Window of the attempt counters.
ATTEMPT_WINDOW = timedelta(minutes=15)
