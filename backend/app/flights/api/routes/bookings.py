"""Endpoints of flight bookings."""

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import get_session_factory
from app.core.messaging.broadcaster import EventBroadcaster
from app.core.messaging.dependencies import get_broadcaster
from app.flights.api.dependencies import booking_owner, existing_booking, get_booking_service, idempotency_key
from app.flights.api.mappers.bookings import to_booking_response
from app.flights.api.schemas.bookings import BookingResponse
from app.flights.domain.dtos.bookings import BookingOwner, BookingRequest, PriceDecisionRequest
from app.flights.services.booking_events import booking_status_stream
from app.flights.services.bookings import BookingService
from app.identity.public import Principal, current_principal

router = APIRouter(prefix="/bookings")


# FastAPI publishes the docstring as the endpoint's description in Swagger, so it is written for
# API consumers instead of following the Google sections.
@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={200: {"model": BookingResponse, "description": "Retry with the same key: the existing booking."}},
)
async def create_booking(
    request: BookingRequest,
    key: Annotated[uuid.UUID, Depends(idempotency_key)],
    owner: Annotated[BookingOwner, Depends(booking_owner)],
    service: Annotated[BookingService, Depends(get_booking_service)],
    response: Response,
) -> BookingResponse:
    """Books a fare for one traveler, on behalf of the signed-in user.

    Needs a session (`Authorization: DPoP` and its proof): the booking belongs to the user and
    their organization, and only they can read it.

    The booking is processed in the background: the answer comes right away (`202`, `pending`)
    and the changes of state arrive by `GET /bookings/{id}/events` (SSE). Send a new UUID in
    `Idempotency-Key` for each checkout attempt and the same one for its retries: a retry answers
    `200` with the existing booking and never books twice. The same key with another body is
    `422 idempotency_key_reused`; without the header, `400 idempotency_key_required`.

    The fare is reconfirmed before charging. If its price changed, nothing is charged and the
    booking goes to `awaiting_price_approval` until the traveler answers with
    `POST /bookings/{id}/price-decision`.
    """
    booking, created = await service.create(key, request, owner)
    if not created:
        response.status_code = status.HTTP_200_OK
    return to_booking_response(booking)


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: uuid.UUID,
    owner: Annotated[BookingOwner, Depends(booking_owner)],
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> BookingResponse:
    """Returns a booking of the signed-in user and its current state. Use it when the event stream isn't available.

    A booking of another user or organization is `404 booking_not_found`, as if it didn't exist.
    """
    return to_booking_response(await service.get(booking_id, owner))


@router.post("/{booking_id}/price-decision", response_model=BookingResponse, status_code=status.HTTP_202_ACCEPTED)
async def decide_price(
    booking_id: uuid.UUID,
    request: PriceDecisionRequest,
    owner: Annotated[BookingOwner, Depends(booking_owner)],
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> BookingResponse:
    """Answers a new price of a booking in `awaiting_price_approval`.

    `accept` books at the new price (`price` must be the `offered_price`); if it changes again,
    the traveler is asked again. `reject` cancels the booking. Repeating the same answer is
    harmless. A booking that isn't waiting for an answer is `409 price_decision_not_applicable`;
    a price other than the offered one is `422 price_mismatch`.
    """
    return to_booking_response(await service.decide_price(booking_id, request, owner))


@router.get("/{booking_id}/events", response_class=EventSourceResponse)
async def booking_events(
    booking_id: Annotated[uuid.UUID, Depends(existing_booking)],
    principal: Annotated[Principal, Depends(current_principal)],
    owner: Annotated[BookingOwner, Depends(booking_owner)],
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    broadcaster: Annotated[EventBroadcaster, Depends(get_broadcaster)],
) -> AsyncIterator[ServerSentEvent]:
    """Streams the state of a booking (Server-Sent Events).

    The first event is the current state; then one event per change, until the booking is final
    (`confirmed`, `failed` or `cancelled`), when the stream closes. Each event is
    `event: status`, `id: <version>` and `data: {"booking_id", "status", "version"}`: read the
    full booking with `GET /bookings/{id}` when it arrives. On reconnection the current state is
    sent again. A `: ping` comment keeps the connection alive.

    Needs a session, like the other booking endpoints; send the headers with `fetch` (an
    `EventSource` can't send them). The stream also closes when the access token expires: reconnect
    with a fresh one.
    """
    stream = booking_status_stream(booking_id, owner, session_factory, broadcaster)
    try:
        while (remaining := principal.expires_at - time.time()) > 0:
            try:
                state = await asyncio.wait_for(anext(stream), remaining)
            except (StopAsyncIteration, TimeoutError):
                return
            yield ServerSentEvent(event="status", id=str(state["version"]), data=state)
    finally:
        await stream.aclose()
