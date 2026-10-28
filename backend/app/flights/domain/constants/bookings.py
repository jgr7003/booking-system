"""Business constants of the bookings."""


# Airlines accept at most this many characters for the given and family names together.
MAX_PASSENGER_NAME_LENGTH = 40


# Passengers per booking in the current version: one person, one flight.
MAX_PASSENGERS_PER_BOOKING = 1


# How long a worker owns a booking it is processing. Past it, another delivery may take it over
# (the worker died); the reconciliation with the provider prevents a second order. It must be
# longer than the slowest processing (three provider calls of up to 60 s) and shorter than the
# retry window of the booking queue (10 attempts every 30 s), so a redelivery that finds the
# booking taken retries until the lease of a dead worker expires.
BOOKING_LEASE_S = 4 * 60
