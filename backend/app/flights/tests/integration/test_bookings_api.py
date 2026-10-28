"""Bookings API against the test PostgreSQL, with a fake provider and a fake event broadcaster."""

import asyncio
import json
import uuid
from decimal import Decimal

import httpx2
import pytest
from sqlalchemy import func, select

from app.core.db import get_db_session, get_session_factory
from app.core.messaging.dependencies import get_broadcaster
from app.core.messaging.models import OutboxMessage
from app.flights.api.dependencies import get_flight_provider
from app.flights.domain.dtos.bookings import BookingStatus
from app.flights.domain.models.bookings import Booking
from app.flights.services.booking_events import booking_status_stream
from app.flights.tests.support import BOOKING_OFFER_ID, FakeBroadcaster, FakeFlightProvider
from app.main import app
from app.travellers.public import get_traveller

pytestmark = pytest.mark.anyio

URL = "/api/v1/flights/bookings"


def booking_body(**overrides) -> dict:
    """Body of `POST /bookings` for a fictitious adult, with the given fields replaced.

    Args:
        **overrides: Top-level fields to replace.

    Returns:
        The JSON body.
    """
    return {
        "offer_id": BOOKING_OFFER_ID,
        "expected_price": {"amount": "250.00", "currency": "USD"},
        "passenger": {
            "title": "ms",
            "traveller": {
                "given_name": "Ana",
                "family_name": "Muñoz",
                "born_on": "1990-05-20",
                "gender": "f",
                "email": "ana.prueba@example.com",
                "phone_number": "+5491112345678",
            },
        },
        "payment_token": "tok_fake_4242",
    } | overrides


def key_header(key: uuid.UUID | str | None = None) -> dict[str, str]:
    """`Idempotency-Key` header, with a new key unless one is given."""
    return {"Idempotency-Key": str(key or uuid.uuid4())}


@pytest.fixture
async def api(db_session_factory):
    """HTTP client of the app wired to the test database and a fake broadcaster.

    Args:
        db_session_factory: Factory of sessions on the test database.

    Yields:
        `(client, broadcaster)`.
    """
    broadcaster = FakeBroadcaster()

    async def session():
        """One session per request, as in production."""
        async with db_session_factory() as s:
            yield s

    app.dependency_overrides[get_db_session] = session
    app.dependency_overrides[get_session_factory] = lambda: db_session_factory
    app.dependency_overrides[get_broadcaster] = lambda: broadcaster
    app.dependency_overrides[get_flight_provider] = lambda: FakeFlightProvider()
    async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://test") as client:
        yield client, broadcaster


async def count(session_factory, model) -> int:
    """Rows of a table.

    Args:
        session_factory: Factory of sessions on the test database.
        model: Model of the table.

    Returns:
        The number of rows.
    """
    async with session_factory() as session:
        return await session.scalar(select(func.count()).select_from(model))


async def set_state(session_factory, booking_id: str, **fields) -> None:
    """Changes columns of a booking directly, to put it in a state for a test.

    Args:
        session_factory: Factory of sessions on the test database.
        booking_id: Id of the booking.
        **fields: Columns to set.
    """
    async with session_factory() as session, session.begin():
        booking = await session.get(Booking, uuid.UUID(booking_id))
        for name, value in fields.items():
            setattr(booking, name, value)


async def test_creates_a_pending_booking_with_its_traveller_and_command(api, db_session_factory):
    client, _ = api

    response = await client.post(URL, json=booking_body(), headers=key_header())

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert data["version"] == 1
    assert data["price"] == {"amount": "250.00", "currency": "USD"}
    assert data["passenger"] == {"title": "ms", "given_name": "ANA", "family_name": "MUNOZ"}
    assert data["order"] is None and data["booking_reference"] is None
    for private in ("cost", "markup", "email", "phone", "born_on", "payment_token"):
        assert private not in response.text

    async with db_session_factory() as session:
        booking = await session.get(Booking, uuid.UUID(data["id"]))
        assert booking.provider == "fake"
        assert booking.passenger["family_name"] == "MUNOZ"
        traveller = await get_traveller(session, booking.traveller_id)
        assert (traveller.given_name, traveller.family_name) == ("Ana", "Muñoz")
        (command,) = (await session.scalars(select(OutboxMessage))).all()
        assert (command.exchange, command.routing_key) == ("bookings.commands", "booking.requested")
        assert command.payload == {"booking_id": data["id"], "status": "pending", "version": 1}


async def test_a_retry_with_the_same_key_returns_the_same_booking_without_doing_it_again(api, db_session_factory):
    client, _ = api
    headers = key_header()

    first = await client.post(URL, json=booking_body(), headers=headers)
    second = await client.post(URL, json=booking_body(), headers=headers)

    assert (first.status_code, second.status_code) == (202, 200)
    assert first.json()["id"] == second.json()["id"]
    assert await count(db_session_factory, Booking) == 1
    assert await count(db_session_factory, OutboxMessage) == 1


async def test_concurrent_requests_with_the_same_key_create_one_booking(api, db_session_factory):
    client, _ = api
    headers = key_header()

    responses = await asyncio.gather(*(client.post(URL, json=booking_body(), headers=headers) for _ in range(5)))

    assert sorted(r.status_code for r in responses) == [200, 200, 200, 200, 202]
    assert len({r.json()["id"] for r in responses}) == 1
    assert await count(db_session_factory, Booking) == 1
    assert await count(db_session_factory, OutboxMessage) == 1


async def test_the_same_key_with_another_body_is_rejected(api):
    client, _ = api
    headers = key_header()
    await client.post(URL, json=booking_body(), headers=headers)

    response = await client.post(URL, json=booking_body(payment_token="tok_fake_1111"), headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "idempotency_key_reused"


@pytest.mark.parametrize("headers", [{}, {"Idempotency-Key": "not-a-uuid"}])
async def test_a_missing_or_invalid_key_is_rejected(api, db_session_factory, headers):
    client, _ = api

    response = await client.post(URL, json=booking_body(), headers=headers)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "idempotency_key_required"
    assert await count(db_session_factory, Booking) == 0


async def test_a_name_the_airline_cant_take_is_rejected_and_nothing_is_saved(api, db_session_factory):
    client, _ = api
    body = booking_body()
    body["passenger"]["traveller"]["family_name"] = "Prueba2"

    response = await client.post(URL, json=body, headers=key_header())

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert await count(db_session_factory, Booking) == 0


async def test_get_returns_the_booking_or_404(api):
    client, _ = api
    created = (await client.post(URL, json=booking_body(), headers=key_header())).json()

    found = await client.get(f"{URL}/{created['id']}")
    missing = await client.get(f"{URL}/{uuid.uuid4()}")

    assert found.status_code == 200 and found.json() == created
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "booking_not_found"


async def awaiting_approval(client, session_factory) -> str:
    """Creates a booking and leaves it waiting for the traveler to approve 262.10 USD.

    Args:
        client: HTTP client of the app.
        session_factory: Factory of sessions on the test database.

    Returns:
        The booking id.
    """
    booking_id = (await client.post(URL, json=booking_body(), headers=key_header())).json()["id"]
    await set_state(
        session_factory,
        booking_id,
        status=BookingStatus.AWAITING_PRICE_APPROVAL,
        version=3,
        offered_amount=Decimal("262.10"),
        offered_currency="USD",
    )
    return booking_id


# New price of `awaiting_approval`.
NEW_PRICE = {"amount": "262.10", "currency": "USD"}


async def test_accepting_the_new_price_sends_the_booking_back_to_the_worker(api, db_session_factory):
    client, _ = api
    booking_id = await awaiting_approval(client, db_session_factory)

    response = await client.post(f"{URL}/{booking_id}/price-decision", json={"decision": "accept", "price": NEW_PRICE})

    assert response.status_code == 202
    data = response.json()
    assert (data["status"], data["version"]) == ("pending", 4)
    assert data["price"] == NEW_PRICE
    async with db_session_factory() as session:
        routing_keys = (await session.scalars(select(OutboxMessage.routing_key).order_by(OutboxMessage.created_at))).all()
    assert routing_keys == ["booking.requested", "booking.pending", "booking.requested"]


async def test_repeating_the_same_decision_is_harmless(api, db_session_factory):
    client, _ = api
    booking_id = await awaiting_approval(client, db_session_factory)
    decision = {"decision": "accept", "price": NEW_PRICE}

    await client.post(f"{URL}/{booking_id}/price-decision", json=decision)
    again = await client.post(f"{URL}/{booking_id}/price-decision", json=decision)

    assert again.status_code == 202
    assert again.json()["version"] == 4
    assert await count(db_session_factory, OutboxMessage) == 3


async def test_rejecting_the_new_price_cancels_the_booking(api, db_session_factory):
    client, _ = api
    booking_id = await awaiting_approval(client, db_session_factory)

    response = await client.post(f"{URL}/{booking_id}/price-decision", json={"decision": "reject", "price": NEW_PRICE})

    assert response.json()["status"] == "cancelled"


async def test_a_decision_on_another_price_is_rejected(api, db_session_factory):
    client, _ = api
    booking_id = await awaiting_approval(client, db_session_factory)

    response = await client.post(
        f"{URL}/{booking_id}/price-decision",
        json={"decision": "accept", "price": {"amount": "250.00", "currency": "USD"}},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "price_mismatch"


async def test_a_decision_on_a_booking_that_isnt_waiting_for_one_is_a_conflict(api):
    client, _ = api
    booking_id = (await client.post(URL, json=booking_body(), headers=key_header())).json()["id"]

    response = await client.post(f"{URL}/{booking_id}/price-decision", json={"decision": "accept", "price": NEW_PRICE})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "price_decision_not_applicable"


def parse_sse(text: str) -> list[dict]:
    """Reads the `event`, `id` and `data` of each event of a `text/event-stream` body.

    Args:
        text: The whole body.

    Returns:
        One dict per event, without comments (pings).
    """
    events = []
    for block in text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if not line.startswith(":"))
        if fields:
            events.append({"event": fields.get("event"), "id": fields.get("id"), "data": json.loads(fields["data"])})
    return events


async def test_events_start_with_the_current_state_and_end_when_it_is_final(api, db_session_factory):
    client, broadcaster = api
    booking_id = (await client.post(URL, json=booking_body(), headers=key_header())).json()["id"]
    aggregate_id = uuid.UUID(booking_id)

    async def worker() -> None:
        """Pushes the events a worker would produce, once the stream is listening."""
        while not broadcaster.subscribers(aggregate_id):
            await asyncio.sleep(0.01)
        status = {"booking_id": booking_id}
        broadcaster.push(aggregate_id, status | {"status": "processing", "version": 2})
        broadcaster.push(aggregate_id, status | {"status": "processing", "version": 2})  # duplicated
        broadcaster.push(aggregate_id, status | {"status": "pending", "version": 1})  # late
        broadcaster.push(aggregate_id, status | {"status": "confirmed", "version": 3})

    _, response = await asyncio.gather(worker(), client.get(f"{URL}/{booking_id}/events"))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [(e["event"], e["id"], e["data"]["status"]) for e in parse_sse(response.text)] == [
        ("status", "1", "pending"),
        ("status", "2", "processing"),
        ("status", "3", "confirmed"),
    ]


async def test_reconnecting_to_a_final_booking_sends_its_state_and_closes(api, db_session_factory):
    client, _ = api
    booking_id = (await client.post(URL, json=booking_body(), headers=key_header())).json()["id"]
    await set_state(db_session_factory, booking_id, status=BookingStatus.CONFIRMED, version=3)

    response = await client.get(f"{URL}/{booking_id}/events", headers={"Last-Event-ID": "2"})

    assert [e["data"] for e in parse_sse(response.text)] == [
        {"booking_id": booking_id, "status": "confirmed", "version": 3}
    ]


async def test_events_of_an_unknown_booking_are_404(api):
    client, _ = api

    response = await client.get(f"{URL}/{uuid.uuid4()}/events")

    assert response.status_code == 404


async def test_without_events_the_stream_reads_the_database_again(api, db_session_factory):
    client, broadcaster = api
    booking_id = (await client.post(URL, json=booking_body(), headers=key_header())).json()["id"]
    stream = booking_status_stream(uuid.UUID(booking_id), db_session_factory, broadcaster, recheck_interval_s=0.05)

    assert (await anext(stream))["status"] == "pending"
    await set_state(db_session_factory, booking_id, status=BookingStatus.FAILED, version=2, failure_code="offer_expired")
    assert (await anext(stream))["status"] == "failed"
    with pytest.raises(StopAsyncIteration):
        await anext(stream)
