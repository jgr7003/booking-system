"""Bookings: states, the traveler's request and the passenger as the airline gets it."""

import uuid
from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from app.core.money import Money
from app.flights.domain.dtos.base import DTO
from app.flights.domain.validators.passengers import to_airline_name, validate_airline_name_length
from app.travellers.public import Gender, IdentityDocumentDetails, IdentityDocumentType, TravellerDetails


class BookingStatus(StrEnum):
    """State of a booking (see docs/superpowers/specs/2026-10-27-reserva-vuelos-design.md §5.2)."""

    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_PRICE_APPROVAL = "awaiting_price_approval"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    # The airline may have issued the booking, but it could not be confirmed or charged. It is not
    # final: it waits to be reconciled. See docs/architecture/02-reserva-vuelos.md §8.2.
    ISSUANCE_ERROR = "issuance_error"

    @property
    def is_final(self) -> bool:
        """Whether the booking can't change anymore (`issuance_error` can: it gets reconciled)."""
        return self in (BookingStatus.CONFIRMED, BookingStatus.FAILED, BookingStatus.CANCELLED)


class FailureCode(StrEnum):
    """Why a booking failed or ended in an issuance error."""

    OFFER_EXPIRED = "offer_expired"
    OFFER_UNAVAILABLE = "offer_unavailable"
    PASSENGER_REJECTED = "passenger_rejected"
    PAYMENT_DECLINED = "payment_declined"
    PROVIDER_REJECTED = "provider_rejected"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    # Of an `issuance_error`: the order exists but the charge could not be captured.
    CAPTURE_FAILED = "capture_failed"
    # Of an `issuance_error`: it could not be verified whether the airline issued the order.
    ORDER_UNVERIFIED = "order_unverified"


class PriceDecision(StrEnum):
    """What the traveler decided about a new price."""

    ACCEPT = "accept"
    REJECT = "reject"


class PassengerTitle(StrEnum):
    """Title airlines print on the ticket. Some airlines don't accept `dr`."""

    MR = "mr"
    MS = "ms"
    MRS = "mrs"
    MISS = "miss"
    DR = "dr"


class BookingPassenger(DTO):
    """The traveler of a booking: their personal data plus what the airline asks for."""

    title: PassengerTitle = Field(
        description="Title printed on the ticket.",
    )

    traveller: TravellerDetails = Field(
        description="Personal data, as written in the travel document.",
    )

    is_account_holder: bool = Field(
        default=False,
        description="Whether the signed-in user travels. Then their title, date of birth and gender are kept "
        "to fill their next booking; for someone else nothing is kept beyond this booking.",
    )

    @model_validator(mode="after")
    def check_airline_names(self) -> Self:
        """Validates the names against the airline's alphabet and length.

        Returns:
            The validated instance.

        Raises:
            ValueError: See `validators.to_airline_name` and `validators.validate_airline_name_length`.
        """
        validate_airline_name_length(
            to_airline_name(self.traveller.given_name),
            to_airline_name(self.traveller.family_name),
        )
        return self


class AirlinePassenger(DTO):
    """A passenger exactly as sent to the airline. The booking keeps it as a fixed copy."""

    title: PassengerTitle = Field(
        description="Title printed on the ticket.",
    )

    given_name: str = Field(
        description="Given name, transliterated (e.g. `JOSE`).",
    )

    family_name: str = Field(
        description="Family name, transliterated (e.g. `MUNOZ`).",
    )

    gender: Gender = Field(
        description="Gender as written in the identity document.",
    )

    born_on: date = Field(
        description="Date of birth.",
    )

    email: str = Field(
        description="Email of the passenger.",
    )

    phone_number: str = Field(
        description="Phone number in E.164 format.",
    )

    passport: IdentityDocumentDetails | None = Field(
        default=None,
        description="Passport, when the traveler gave one.",
    )

    @classmethod
    def from_booking(cls, passenger: BookingPassenger) -> Self:
        """Builds the airline's view of a booking passenger.

        Args:
            passenger: The validated passenger.

        Returns:
            The passenger with transliterated names.
        """
        traveller = passenger.traveller
        return cls(
            title=passenger.title,
            given_name=to_airline_name(traveller.given_name),
            family_name=to_airline_name(traveller.family_name),
            gender=traveller.gender,
            born_on=traveller.born_on,
            email=traveller.email,
            phone_number=traveller.phone_number,
            passport=traveller.document(IdentityDocumentType.PASSPORT),
        )


class BookingRequest(DTO):
    """What the traveler confirms on the passengers and payment screen."""

    offer_id: str = Field(
        description="Provider id of the chosen fare (`fares[].offer_id`).",
    )

    expected_price: Money = Field(
        description="Total sale price shown when confirming. If the airline changed it, nothing is "
        "charged and the booking waits for the traveler's approval.",
    )

    passenger: BookingPassenger = Field(
        description="The traveler.",
    )

    payment_token: str = Field(
        description="Token of the card from the payment form (simulated for now: `tok_fake_<last 4 digits>`). "
        "The card number never reaches the API.",
    )


class PriceDecisionRequest(DTO):
    """The traveler's answer to a new price."""

    decision: PriceDecision = Field(
        description="`accept` books at the new price; `reject` cancels the booking.",
    )

    price: Money = Field(
        description="The new price being answered (`offered_price` of the booking).",
    )


class BookingOwner(DTO):
    """Who may see a booking: its user, within their organization.

    Every read of a booking made for a user takes one, with no defaults, and filters by both
    fields: the organization so nobody ever sees another organization's bookings (nor a private
    traveller an organization's, or the other way around), and the user so each person sees only
    their own. When permissions exist, a role may relax the user filter inside its organization;
    the organization filter never goes away.
    """

    organization_id: uuid.UUID | None = Field(
        description="Organization of the user; `None` for a private traveller.",
    )

    user_id: uuid.UUID = Field(
        description="The user.",
    )
