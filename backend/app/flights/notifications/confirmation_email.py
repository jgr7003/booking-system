"""Email "Tu reserva está confirmada" (design board "Correo de confirmación", Propuesta A v2)."""

from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.flights.api.schemas.bookings import BookingResponse, OrderResponse
from app.flights.domain.dtos.itinerary import Place, Slice
from app.flights.domain.dtos.offers import FareCondition
from app.flights.notifications.formatting import (
    day_month,
    duration,
    local_time,
    money,
    penalty,
    short_date,
    weekday_date,
)

# Titles as the design writes them before the name.
TITLES = {"mr": "Sr.", "mrs": "Sra.", "ms": "Sra./Srta.", "miss": "Srta.", "dr": "Dr./Dra."}

# Connections shorter than this are highlighted, as in the results and the web confirmation.
SHORT_CONNECTION_MINUTES = 60

# Colors of "Qué incluye" (Propuesta A tokens).
TONE_COLORS = {"ok": "#0B6B44", "bad": "#A11D12", "warn": "#8A4B00", "na": "#4B5563"}

_templates = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    # HTML templates escape every value (names come from the traveler); plain text ones don't.
    autoescape=select_autoescape(enabled_extensions=("html.j2",), default_for_string=False),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass(frozen=True)
class RenderedEmail:
    """A rendered email, ready to hand to the notifications module."""

    # Subject line.
    subject: str

    # HTML body.
    html: str

    # Plain-text body.
    text: str


@dataclass(frozen=True)
class IncludedItem:
    """A row of "Qué incluye tu tarifa"."""

    # What it is, e.g. "Maleta de bodega".
    label: str

    # What the fare gives, e.g. "✓ 1 incluida" or "Sin dato".
    value: str

    # `ok`, `bad`, `warn` or `na` (unknown, shown in italics).
    tone: str

    @property
    def color(self) -> str:
        """Text color of the value."""
        return TONE_COLORS[self.tone]


@dataclass(frozen=True)
class SegmentView:
    """One flight of a slice."""

    flight: str
    operator: str
    aircraft: str
    departure_time: str
    departure_place: str
    arrival_time: str
    arrival_place: str
    # Connection after this flight, e.g. "Conexión en Frankfurt (FRA) · 55 min"; empty for the last.
    connection: str = ""
    connection_is_short: bool = False


@dataclass(frozen=True)
class SliceView:
    """"IDA" or "VUELTA" with its flights."""

    label: str
    route: str
    summary: str
    segments: list[SegmentView]
    included: list[IncludedItem] = field(default_factory=list)


def render_booking_confirmed(booking: BookingResponse, *, app_url: str) -> RenderedEmail:
    """Renders the confirmation email of a confirmed booking.

    It uses the same public view and rules as the confirmation screen: unknown values are
    "Sin dato", times are local and amounts are in their own currency.

    Args:
        booking: Public view of the booking; it must be confirmed, with its order.
        app_url: Public URL of the web app, for the "Ver tu reserva" link.

    Returns:
        Subject, HTML and plain text.

    Raises:
        ValueError: The booking isn't confirmed.
    """
    order = booking.order
    if order is None or booking.booking_reference is None:
        raise ValueError(f"booking {booking.id} isn't confirmed")
    context = _context(booking, order, booking.booking_reference, app_url)
    return RenderedEmail(
        subject=context["subject"],
        html=_templates.get_template("booking_confirmed.html.j2").render(context),
        text=_templates.get_template("booking_confirmed.txt.j2").render(context),
    )


def _context(booking: BookingResponse, order: OrderResponse, reference: str, app_url: str) -> dict:
    """Everything the templates show, already formatted."""
    first, last = order.slices[0], order.slices[-1]
    round_trip = len(order.slices) > 1
    arrow = "⇄" if round_trip else "→"
    origin, destination = _city(first.origin), _city(first.destination if round_trip else last.destination)
    departure = first.segments[0].departing_at.date()
    passenger = f"{booking.passenger.given_name} {booking.passenger.family_name}"
    owner = order.owner.name
    total = money(booking.price)

    slices = [_slice(s, ("IDA" if i == 0 else "VUELTA") if round_trip else "IDA", order) for i, s in enumerate(order.slices)]
    same_included = all(s.included == slices[0].included for s in slices)
    fare_names = sorted({s.fare_brand or "Tarifa" for s in order.slices})

    preview = " y ".join(
        f"{'Ida' if i == 0 else 'vuelta'} {weekday_date(s.segments[0].departing_at.date())}"
        for i, s in enumerate(order.slices)
    )
    return {
        "subject": f"Reserva confirmada · {reference} · {origin} {arrow} {destination}, {day_month(departure)}",
        "preview": f"{preview} · {owner} · {total}",
        "reference": reference,
        "greeting_name": f"{TITLES.get(booking.passenger.title, '')} {passenger}".strip(),
        "passenger": passenger,
        "total": total,
        "paid_on": short_date(order.paid_at.date()) if order.paid_at else None,
        "tickets": [t.number for t in order.tickets],
        "owner": owner,
        "conditions_url": order.owner.conditions_of_carriage_url,
        "trip_kind": "ida y vuelta" if round_trip else "solo ida",
        "route": f"{origin} {arrow} {destination}",
        "slices": slices,
        "same_included": same_included,
        "round_trip": round_trip,
        "fare_names": " / ".join(fare_names),
        "booking_url": f"{app_url.rstrip('/')}/bookings/{booking.id}",
    }


def _slice(slice_: Slice, label: str, order: OrderResponse) -> SliceView:
    """View of one slice: route, summary line, flights and what the fare includes."""
    segments = slice_.segments
    first_passenger = segments[0].passengers[0] if segments[0].passengers else None
    cabin = first_passenger.cabin_name if first_passenger and first_passenger.cabin_name else None
    stops = "Directo" if slice_.stops == 0 else ("1 escala" if slice_.stops == 1 else f"{slice_.stops} escalas")
    fare = slice_.fare_brand or "Tarifa"
    views = []
    for i, segment in enumerate(segments):
        connection = slice_.connections[i] if i < len(segments) - 1 and i < len(slice_.connections) else None
        arrives_next_day = (segment.arriving_at.date() - segment.departing_at.date()).days
        views.append(
            SegmentView(
                flight=f"{segment.marketing_carrier.code} {segment.flight_number}",
                operator=segment.operating_carrier.name,
                aircraft=segment.aircraft or "Avión: sin dato",
                departure_time=local_time(segment.departing_at),
                departure_place=_airport(segment.origin),
                arrival_time=local_time(segment.arriving_at) + (f" +{arrives_next_day}" if arrives_next_day > 0 else ""),
                arrival_place=_airport(segment.destination),
                connection=(
                    f"Conexión en {_city(_place_of(connection.airport, segment.destination))} ({connection.airport}) · "
                    f"{duration(connection.duration_minutes)}"
                    if connection
                    else ""
                ),
                connection_is_short=bool(
                    connection
                    and connection.duration_minutes is not None
                    and connection.duration_minutes < SHORT_CONNECTION_MINUTES
                ),
            )
        )
    return SliceView(
        label=label,
        route=f"de {_city(slice_.origin)} ({slice_.origin.code}) a {_city(slice_.destination)} ({slice_.destination.code})",
        summary=" · ".join(
            [
                short_date(segments[0].departing_at.date()),
                stops,
                duration(slice_.duration_minutes),
                f"{cabin} {fare}" if cabin else fare,
            ]
        ),
        segments=views,
        included=_included(slice_, order),
    )


def _included(slice_: Slice, order: OrderResponse) -> list[IncludedItem]:
    """"Qué incluye tu tarifa" for one slice: bags of the slice and conditions of the order."""
    carry_on = _lowest([p.baggage.carry_on for s in slice_.segments for p in s.passengers])
    checked = _lowest([p.baggage.checked for s in slice_.segments for p in s.passengers])
    benefits = slice_.benefits
    return [
        _bag("Equipaje de mano", carry_on, "incluido", "incluidos", "No incluido"),
        _bag("Maleta de bodega", checked, "incluida", "incluidas", "No incluida"),
        _condition("Cambios", order.conditions.change),
        _condition("Reembolso", order.conditions.refund),
        _benefits(benefits.advance_seat_selection, benefits.priority_boarding),
    ]


def _bag(label: str, quantity: int | None, one: str, many: str, none: str) -> IncludedItem:
    """`None` → «Sin dato»; 0 → «✗ No incluida»; n → «✓ n incluida(s)»."""
    if quantity is None:
        return IncludedItem(label, "Sin dato", "na")
    if quantity == 0:
        return IncludedItem(label, f"✗ {none}", "bad")
    return IncludedItem(label, f"✓ {quantity} {one if quantity == 1 else many}", "ok")


def _condition(label: str, condition: FareCondition) -> IncludedItem:
    """Change or refund: «✗ No permite», «✓ Gratis», «Con cargo · 40 USD» or «Sin dato»."""
    if condition.allowed is False:
        return IncludedItem(label, "✗ No permite", "bad")
    if condition.allowed is not True or condition.penalty is None:
        return IncludedItem(label, "Sin dato", "na")
    if condition.penalty.amount == 0:
        return IncludedItem(label, "✓ Gratis", "ok")
    return IncludedItem(label, f"Con cargo · {penalty(condition.penalty)}", "warn")


def _benefits(seat: bool | None, boarding: bool | None) -> IncludedItem:
    """«Asiento y embarque prioritario», joined when both are known and equal."""
    label = "Asiento y embarque prioritario"
    if seat is None and boarding is None:
        return IncludedItem(label, "Sin dato", "na")
    if seat is boarding:
        return IncludedItem(label, "✓ Incluidos" if seat else "✗ No incluidos", "ok" if seat else "bad")
    mark = lambda value: "Sin dato" if value is None else ("✓" if value else "✗")  # noqa: E731
    return IncludedItem(label, f"Asiento {mark(seat)} · Embarque {mark(boarding)}", "na")


def _lowest(values: list[int | None]) -> int | None:
    """The lowest quantity of every segment; unknown if any is unknown."""
    if not values or any(v is None for v in values):
        return None
    return min(v for v in values if v is not None)


def _city(place: Place) -> str:
    """City of a place, or its IATA code when the provider doesn't say."""
    return place.city or place.code


def _place_of(code: str, arrival: Place) -> Place:
    """The connection airport: the arrival of the flight before it, when the codes match."""
    return arrival if arrival.code == code else Place(code=code, name=code)


def _airport(place: Place) -> str:
    """"El Dorado International Airport (Bogota) · T2", with «terminal s/d» when unknown."""
    city = f" ({place.city})" if place.city else ""
    terminal = f"T{place.terminal}" if place.terminal else "terminal s/d"
    return f"{place.name}{city} · {terminal}"
