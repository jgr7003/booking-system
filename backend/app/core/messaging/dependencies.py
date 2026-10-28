"""FastAPI dependencies of the messaging infrastructure."""

from fastapi import Request

from app.core.messaging.broadcaster import EventBroadcaster


def get_broadcaster(request: Request) -> EventBroadcaster:
    """FastAPI dependency that provides the event broadcaster of this API instance.

    Args:
        request: The incoming request, used to reach the broadcaster in the app state.

    Returns:
        The broadcaster created in the lifespan.
    """
    return request.app.state.broadcaster
