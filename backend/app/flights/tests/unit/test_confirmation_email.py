import copy

from app.flights.api.schemas.bookings import BookingResponse
from app.flights.notifications.confirmation_email import render_booking_confirmed
from app.flights.tests.support import load_fixture

APP_URL = "http://localhost:5173"


def roundtrip() -> dict:
    """The real round trip Bogotá ⇄ Cali confirmed in Duffel test (public view), as JSON."""
    return copy.deepcopy(load_fixture("bookings/confirmed_roundtrip.json"))


def render(data: dict):
    """Renders the confirmation email of a booking given as JSON."""
    return render_booking_confirmed(BookingResponse.model_validate(data), app_url=APP_URL)


def test_subject_and_preview_summarize_the_round_trip():
    email = render(roundtrip())

    assert email.subject == "Reserva confirmada · GNA3VA · Bogota ⇄ Cali, 10 nov"
    assert "Ida mar 10 nov y vuelta dom 15 nov · British Airways · 59,82 USD" in email.html


def test_each_slice_has_its_label_date_and_operator():
    html = render(roundtrip()).html

    assert "IDA" in html and "VUELTA" in html
    assert "mar 10 nov 2026 · Directo · 57 min · Economy Basic" in html
    assert "dom 15 nov 2026 · Directo · 57 min · Economy Basic" in html
    assert html.count("Operado por <strong") == 2
    assert "El Dorado International Airport (Bogota) · T2" in html


def test_it_shows_what_the_fare_includes_once_when_both_slices_match():
    html = render(roundtrip()).html

    assert html.count("Qué incluye tu tarifa Basic") == 1
    assert "Igual en la ida y en la vuelta." in html
    assert "✓ 1 incluida" in html
    assert "✗ No permite" in html


def test_it_links_to_the_booking_and_shows_the_sale_price_only():
    data = roundtrip()
    email = render(data)

    assert f'href="{APP_URL}/bookings/{data["id"]}"' in email.html
    assert "Precio final" in email.html and "59,82 USD" in email.html
    for private in ("cost", "markup", "tok_fake"):
        assert private not in email.html


def test_the_plain_text_has_code_slices_total_and_link():
    data = roundtrip()
    text = render(data).text

    assert "CÓDIGO DE RESERVA: GNA3VA" in text
    assert "IDA · de Bogota (BOG) a Cali (CLO)" in text
    assert "VUELTA · de Cali (CLO) a Bogota (BOG)" in text
    assert "PRECIO FINAL: 59,82 USD" in text
    assert f"{APP_URL}/bookings/{data['id']}" in text


def test_one_way_uses_an_arrow_and_says_solo_ida():
    data = roundtrip()
    data["order"]["slices"] = data["order"]["slices"][:1]

    email = render(data)

    assert email.subject == "Reserva confirmada · GNA3VA · Bogota → Cali, 10 nov"
    assert "Tu viaje · solo ida" in email.html
    assert "VUELTA" not in email.html
    assert "Igual en la ida y en la vuelta." not in email.html


def test_a_short_connection_is_highlighted():
    data = roundtrip()
    outbound = data["order"]["slices"][0]
    second = copy.deepcopy(outbound["segments"][0])
    second["flight_number"] = "1517"
    outbound["segments"].append(second)
    outbound["connections"] = [{"airport": "CLO", "duration_minutes": 45}]
    outbound["stops"] = 1

    html = render(data).html

    assert "Conexión en Cali (CLO) · 45 min" in html
    assert "Conexión corta" in html
    assert "1 escala" in html


def test_missing_data_is_sin_dato_never_assumed():
    data = roundtrip()
    for slice_ in data["order"]["slices"]:
        for segment in slice_["segments"]:
            segment["aircraft"] = None
            segment["origin"]["terminal"] = None
            for passenger in segment["passengers"]:
                passenger["baggage"] = {"checked": None, "carry_on": None}
    data["order"]["conditions"] = {"change": {"allowed": None}, "refund": {"allowed": None}}

    html = render(data).html

    assert "Avión: sin dato" in html
    assert "terminal s/d" in html
    assert html.count(">Sin dato<") >= 4


def test_names_are_escaped():
    data = roundtrip()
    data["passenger"]["family_name"] = "<script>"

    assert "<script>" not in render(data).html
