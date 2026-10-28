"""HTTP access to the Duffel API."""

import logging
from typing import Any

import httpx2

from app.flights.core.config import DuffelSettings
from app.flights.domain.errors.provider import (
    OfferAlreadyBookedError,
    OfferExpiredError,
    OfferUnavailableError,
    OrderRejectedError,
    ProviderError,
    ProviderTimeoutError,
)
from app.flights.domain.errors.search import InvalidSearchError

logger = logging.getLogger(__name__)

# Duffel error codes of an offer that can't be booked anymore because it expired, as documented.
# In test mode an expired offer answers like a missing one instead (`not_found`, see
# `docs/providers/duffel-busqueda-y-reserva.md` §4.6), which maps to `OfferUnavailableError`.
OFFER_EXPIRED_CODES = frozenset({"offer_no_longer_available", "offer_expired"})

# Duffel error code of a missing resource, e.g. an offer id that expired or never existed.
NOT_FOUND = "not_found"

# Duffel error code of a second order from the same offer request.
OFFER_REQUEST_ALREADY_BOOKED = "offer_request_already_booked"


class DuffelRejection(Exception):
    """Duffel answered 4xx with its `errors` list. Each method translates it into a domain error.

    Attributes:
        status_code: HTTP status of the answer.
        codes: The `code` of each error.
        messages: The `message` of each error, safe to show (validation messages).
    """

    def __init__(self, status_code: int, errors: list[dict[str, Any]]) -> None:
        """Initializes the rejection.

        Args:
            status_code: HTTP status of the answer.
            errors: Duffel's `errors` list.
        """
        super().__init__(status_code)
        self.status_code = status_code
        self.codes = {e.get("code") for e in errors}
        self.messages = [e["message"] for e in errors if e.get("message")]


class DuffelClient:
    """Thin HTTP layer over the Duffel API: auth, headers, timeouts and error translation.

    It speaks Duffel's JSON format; turning that into platform DTOs is `mapper`'s job.
    """

    def __init__(self, http: httpx2.AsyncClient, settings: DuffelSettings) -> None:
        """Initializes the client.

        Args:
            http: Shared HTTP client (a mocked one in tests).
            settings: URL, token, API version and timeouts.
        """
        self._http = http
        self._settings = settings

    async def create_offer_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Runs a search (`POST /air/offer_requests`).

        Args:
            payload: Offer request in Duffel's format, without the `data` envelope.

        Returns:
            The `data` object of Duffel's answer: the offer request with its offers.

        Raises:
            InvalidSearchError: Duffel rejected the payload (400/422).
            ProviderTimeoutError: Duffel didn't answer within `http_timeout_s`.
            ProviderError: Any other failure (network, authentication, 5xx...).
        """
        try:
            return await self._request(
                "POST",
                "/air/offer_requests",
                json={"data": payload},
                params={"supplier_timeout": self._settings.supplier_timeout_ms},
            )
        except DuffelRejection as rejection:
            if rejection.status_code in (400, 422):
                raise InvalidSearchError(
                    "; ".join(rejection.messages) or "The flight provider rejected the search criteria."
                ) from rejection
            raise ProviderError("The flight provider failed to process the request.") from rejection

    async def get_offer(self, offer_id: str) -> dict[str, Any]:
        """Reads an offer with its current price (`GET /air/offers/{id}`).

        Args:
            offer_id: Duffel id of the offer (`off_...`).

        Returns:
            The `data` object: the offer.

        Raises:
            OfferExpiredError: The offer expired.
            OfferUnavailableError: The offer doesn't exist.
            ProviderTimeoutError: Duffel didn't answer in time.
            ProviderError: Any other failure.
        """
        try:
            return await self._request("GET", f"/air/offers/{offer_id}")
        except DuffelRejection as rejection:
            raise _offer_error(rejection) from rejection

    async def list_orders(self, offer_id: str) -> list[dict[str, Any]]:
        """Lists the orders created from an offer (`GET /air/orders?offer_id=...`).

        Args:
            offer_id: Duffel id of the offer.

        Returns:
            The orders; empty if the offer wasn't booked.

        Raises:
            ProviderTimeoutError: Duffel didn't answer in time.
            ProviderError: Any failure.
        """
        try:
            return await self._request("GET", "/air/orders", params={"offer_id": offer_id})
        except DuffelRejection as rejection:
            raise ProviderError("The flight provider failed to list the orders.") from rejection

    async def create_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Books an offer (`POST /air/orders`).

        Duffel ignores `Idempotency-Key` headers (verified in test mode, see
        `docs/providers/duffel-busqueda-y-reserva.md` §4.6), so a retry must reconcile first.

        Args:
            payload: Order in Duffel's format, without the `data` envelope.

        Returns:
            The `data` object: the order.

        Raises:
            OfferAlreadyBookedError: The offer request was already booked (maybe by us).
            OfferExpiredError: The offer expired.
            OfferUnavailableError: The offer doesn't exist.
            OrderRejectedError: Duffel rejected the order for any other reason (400/422).
            ProviderTimeoutError: Duffel didn't answer in time; the order may exist.
            ProviderError: Any other failure; the order may exist.
        """
        try:
            return await self._request(
                "POST", "/air/orders", json={"data": payload}, timeout=self._settings.order_timeout_s
            )
        except DuffelRejection as rejection:
            if OFFER_REQUEST_ALREADY_BOOKED in rejection.codes:
                raise OfferAlreadyBookedError("The offer was already booked.") from rejection
            if rejection.codes & OFFER_EXPIRED_CODES or NOT_FOUND in rejection.codes or rejection.status_code == 404:
                raise _offer_error(rejection) from rejection
            if rejection.status_code in (400, 422):
                raise OrderRejectedError(
                    "; ".join(rejection.messages) or "The flight provider rejected the order."
                ) from rejection
            raise ProviderError("The flight provider failed to process the order.") from rejection

    async def _request(self, method: str, path: str, *, timeout: float | None = None, **kwargs: Any) -> Any:
        """Sends an authenticated request and unwraps the `data` envelope.

        Args:
            method: HTTP method.
            path: API path, e.g. `/air/offer_requests`.
            timeout: Seconds to wait; `http_timeout_s` if not given.
            **kwargs: Extra arguments for `httpx2.AsyncClient.request` (`json`, `params`...).

        Returns:
            The `data` member of the response.

        Raises:
            DuffelRejection: Duffel answered 400, 404 or 422.
            ProviderTimeoutError: Duffel didn't answer in time.
            ProviderError: Any other failure (network, authentication, 5xx...).
        """
        try:
            response = await self._http.request(
                method,
                f"{self._settings.api_url}{path}",
                headers=self._headers(),
                timeout=timeout if timeout is not None else self._settings.http_timeout_s,
                **kwargs,
            )
        except httpx2.TimeoutException as exc:
            raise ProviderTimeoutError("The flight provider didn't answer in time.") from exc
        except httpx2.RequestError as exc:
            logger.warning("Duffel request to %s failed: %s", path, exc)
            raise ProviderError("The flight provider is unreachable.") from exc

        if response.is_success:
            return response.json()["data"]
        errors = _parse_errors(response)
        logger.warning(
            "Duffel %s %s answered %s: %s (request_id=%s)",
            method,
            path,
            response.status_code,
            [(e.get("code"), e.get("message")) for e in errors],
            response.headers.get("x-request-id"),
        )
        if response.status_code in (400, 404, 422):
            raise DuffelRejection(response.status_code, errors)
        raise ProviderError("The flight provider failed to process the request.")

    def _headers(self) -> dict[str, str]:
        """Builds the headers Duffel requires on every request."""
        return {
            "Authorization": f"Bearer {self._settings.api_token.get_secret_value()}",
            "Duffel-Version": self._settings.api_version,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }


def _offer_error(rejection: DuffelRejection) -> Exception:
    """Translates a rejection about an offer: expired, missing or a generic provider error."""
    if rejection.codes & OFFER_EXPIRED_CODES:
        return OfferExpiredError("The offer expired.")
    if rejection.status_code == 404 or NOT_FOUND in rejection.codes:
        return OfferUnavailableError("The offer doesn't exist anymore; it probably expired.")
    return ProviderError("The flight provider failed to read the offer.")


def _parse_errors(response: httpx2.Response) -> list[dict[str, Any]]:
    """Extracts Duffel's `errors` list, or an empty list if the body isn't Duffel's JSON."""
    try:
        return response.json().get("errors") or []
    except ValueError:
        return []
