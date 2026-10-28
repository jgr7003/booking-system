"""RabbitMQ topology of the flights module: booking commands and events."""

from aio_pika import ExchangeType

from app.core.messaging.broadcaster import EventBinding
from app.core.messaging.topology import ExchangeSpec, QueueSpec, Topology

# Commands for the booking worker.
BOOKING_COMMANDS = ExchangeSpec("bookings.commands", ExchangeType.DIRECT)

# Changes of state of a booking, for the API's open connections (SSE).
BOOKING_EVENTS = ExchangeSpec("bookings.events", ExchangeType.TOPIC)

# A booking is ready to be processed (new, or with its new price approved).
BOOKING_REQUESTED = "booking.requested"

# Work queue of the booking worker.
BOOKING_WORKER_QUEUE = QueueSpec(
    name="flights.booking-worker",
    exchange=BOOKING_COMMANDS,
    routing_keys=(BOOKING_REQUESTED,),
    retry_delay_s=30,
    # 10 attempts every 30 s: a 5-minute window, longer than `BOOKING_LEASE_S`.
    max_attempts=10,
)

# A booking was confirmed: the traveler gets the email.
BOOKING_CONFIRMED = "booking.confirmed"

# Work queue of the confirmation emails. It listens to the same events as the SSE connections.
BOOKING_NOTIFIER_QUEUE = QueueSpec(
    name="flights.booking-notifier",
    exchange=BOOKING_EVENTS,
    routing_keys=(BOOKING_CONFIRMED,),
    retry_delay_s=60,
    # 10 attempts every minute: a mail server down for a few minutes only delays the email.
    max_attempts=10,
)

# Everything the module needs in RabbitMQ.
TOPOLOGY = Topology(
    exchanges=(BOOKING_COMMANDS, BOOKING_EVENTS),
    queues=(BOOKING_WORKER_QUEUE, BOOKING_NOTIFIER_QUEUE),
)

# Events the API forwards to the SSE connections.
EVENT_BINDINGS = (EventBinding(BOOKING_EVENTS, "booking.*"),)
