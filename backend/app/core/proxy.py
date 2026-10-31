"""What the client really sent, through the proxies in front of the API.

In development the Vite dev server forwards `/api` (03-usuarios-y-acceso.md §5); in other
environments it is a load balancer. They tell the original host and the client's address in
`X-Forwarded-*` headers, which are believed only from the networks in `TRUSTED_PROXIES`.
"""

from ipaddress import ip_address

from fastapi import Request

from app.core.config import get_settings


def from_trusted_proxy(request: Request) -> bool:
    """Whether the direct client is one of the trusted proxies.

    Args:
        request: The incoming request.

    Returns:
        `True` if its `X-Forwarded-*` headers can be believed.
    """
    networks = get_settings().trusted_proxies
    if not networks or request.client is None:
        return False
    try:
        address = ip_address(request.client.host)
    except ValueError:
        return False
    return any(address in network for network in networks)


def original_host(request: Request) -> str:
    """The `Host` the client asked for, port included.

    Args:
        request: The incoming request.

    Returns:
        `X-Forwarded-Host` from a trusted proxy (the first one of a chain), or the `Host` header.
    """
    forwarded = request.headers.get("x-forwarded-host")
    if forwarded and from_trusted_proxy(request):
        return forwarded.split(",")[0].strip()
    return request.headers.get("host", "")


def client_ip(request: Request) -> str | None:
    """Address of the client, for logs, the device list and blocking abusive addresses.

    Args:
        request: The incoming request.

    Returns:
        The first address of `X-Forwarded-For` from a trusted proxy, or the direct client's.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and from_trusted_proxy(request):
        candidate = forwarded.split(",")[0].strip()
        try:
            return str(ip_address(candidate))
        except ValueError:
            pass
    return request.client.host if request.client else None
