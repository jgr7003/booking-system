"""HTTP client shared by every provider adapter."""

import httpx2
from fastapi import Request


def get_http_client(request: Request) -> httpx2.AsyncClient:
    """FastAPI dependency that provides the shared HTTP client.

    Tests override this dependency with a client backed by `httpx2.MockTransport`.

    Args:
        request: The incoming request, used to reach the application state.

    Returns:
        The client created in `app.core.lifespan`.
    """
    return request.app.state.http_client
