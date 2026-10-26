"""HTTP access to the Duffel API."""

import logging
from typing import Any

import httpx2

from app.flights.core.config import DuffelSettings
from app.flights.domain.errors import InvalidSearchError, ProviderError, ProviderTimeoutError

logger = logging.getLogger(__name__)


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
        return await self._post(
            "/air/offer_requests",
            json={"data": payload},
            params={"supplier_timeout": self._settings.supplier_timeout_ms},
        )

    async def _post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Sends an authenticated POST and unwraps the `data` envelope.

        Args:
            path: API path, e.g. `/air/offer_requests`.
            **kwargs: Extra arguments for `httpx2.AsyncClient.post` (`json`, `params`...).

        Returns:
            The `data` object of the response.

        Raises:
            InvalidSearchError: Duffel rejected the request (400/422).
            ProviderTimeoutError: Duffel didn't answer in time.
            ProviderError: Any other failure.
        """
        try:
            response = await self._http.post(
                f"{self._settings.api_url}{path}",
                headers=self._headers(),
                timeout=self._settings.http_timeout_s,
                **kwargs,
            )
        except httpx2.TimeoutException as exc:
            raise ProviderTimeoutError("The flight provider didn't answer in time.") from exc
        except httpx2.RequestError as exc:
            logger.warning("Duffel request to %s failed: %s", path, exc)
            raise ProviderError("The flight provider is unreachable.") from exc

        if response.is_success:
            return response.json()["data"]
        raise self._error_for(path, response)

    def _headers(self) -> dict[str, str]:
        """Builds the headers Duffel requires on every request."""
        return {
            "Authorization": f"Bearer {self._settings.api_token.get_secret_value()}",
            "Duffel-Version": self._settings.api_version,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }

    @staticmethod
    def _error_for(path: str, response: httpx2.Response) -> Exception:
        """Logs a failed response and translates it into a domain error.

        Only validation messages reach the client; anything else becomes a generic message so
        provider internals never leak.

        Args:
            path: API path that failed, for the log.
            response: The unsuccessful response.

        Returns:
            The domain error to raise.
        """
        errors = _parse_errors(response)
        logger.warning(
            "Duffel %s answered %s: %s (request_id=%s)",
            path,
            response.status_code,
            [(e.get("code"), e.get("message")) for e in errors],
            response.headers.get("x-request-id"),
        )
        if response.status_code in (400, 422):
            messages = "; ".join(e["message"] for e in errors if e.get("message"))
            return InvalidSearchError(messages or "The flight provider rejected the search criteria.")
        return ProviderError("The flight provider failed to process the request.")


def _parse_errors(response: httpx2.Response) -> list[dict[str, Any]]:
    """Extracts Duffel's `errors` list, or an empty list if the body isn't Duffel's JSON."""
    try:
        return response.json().get("errors") or []
    except ValueError:
        return []
