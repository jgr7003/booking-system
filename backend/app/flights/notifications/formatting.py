"""Spanish formats of the emails, the same ones the web shows ("mar 10 nov 2026", "59,82 USD")."""

from datetime import date, datetime
from decimal import Decimal

from app.core.money import Money

# Short weekday names, Monday first (as `date.weekday()`).
WEEKDAYS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")

# Short month names.
MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def short_date(day: date) -> str:
    """"mar 10 nov 2026"."""
    return f"{weekday_date(day)} {day.year}"


def weekday_date(day: date) -> str:
    """"mar 10 nov"."""
    return f"{WEEKDAYS[day.weekday()]} {day.day} {MONTHS[day.month - 1]}"


def day_month(day: date) -> str:
    """"10 nov"."""
    return f"{day.day} {MONTHS[day.month - 1]}"


def money(amount: Money) -> str:
    """"1.234,56 USD": amount first, in its own currency, never converted."""
    quantized = Decimal(amount.amount).quantize(Decimal("0.01"))
    whole, cents = f"{quantized:,.2f}".split(".")
    return f"{whole.replace(',', '.')},{cents} {amount.currency}"


def penalty(amount: Money) -> str:
    """"40 USD", "150,50 GBP": without ",00", as the fare matrix shows penalties."""
    text = money(amount)
    return text.replace(",00 ", " ")


def duration(minutes: int | None) -> str:
    """"57 min", "1 h 55 min", "13 h"; "Sin dato" if unknown."""
    if minutes is None:
        return "Sin dato"
    hours, rest = divmod(minutes, 60)
    if hours == 0:
        return f"{rest} min"
    return f"{hours} h" if rest == 0 else f"{hours} h {rest} min"


def local_time(moment: datetime) -> str:
    """"06:58": flight times are local to their airport and are shown as they come."""
    return moment.strftime("%H:%M")
