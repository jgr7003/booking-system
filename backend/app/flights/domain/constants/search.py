"""Business constants of the flight search."""


# Airlines don't accept more passengers in a single booking.
MAX_PASSENGERS = 9


# Children up to this age travel as infants and need an adult each.
INFANT_MAX_AGE = 1


# Allowed range for the maximum connections per slice; 0 means direct flights only.
MIN_CONNECTIONS = 0


MAX_CONNECTIONS = 2


# Passengers from this age are adults; younger ones are searched by age.
ADULT_AGE = 18
