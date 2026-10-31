import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.core.config import get_settings
from app.core.proxy import client_ip
from app.organizations.api.dependencies import request_host
from app.organizations.domain.dtos import NewOrganization, OrganizationSettings
from app.organizations.domain.validators import normalize_host
from app.organizations.services.organizations import installation_of


def make_request(host: str, forwarded: str | None = None, client: str = "203.0.113.7") -> Request:
    """A bare request with a `Host` header, an optional `X-Forwarded-Host` and a client address.

    Args:
        host: Value of the `Host` header.
        forwarded: Value of `X-Forwarded-Host`, if any.
        client: IP of the direct client.

    Returns:
        The request.
    """
    headers = [(b"host", host.encode())]
    if forwarded is not None:
        headers.append((b"x-forwarded-host", forwarded.encode()))
    return Request({"type": "http", "headers": headers, "client": (client, 1234)})


def test_settings_have_defaults_for_every_key():
    assert OrganizationSettings.model_validate({}).password_login_enabled is True


def test_settings_reject_an_undeclared_key():
    with pytest.raises(ValidationError):
        OrganizationSettings.model_validate({"habilitar_algo": True})


def test_main_platform_uses_the_default_settings():
    assert installation_of("localhost", None).settings == OrganizationSettings()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Acme.LocalHost:5173", "acme.localhost"), ("acme.localhost.", "acme.localhost"), ("[::1]:8000", "[::1]")],
)
def test_normalizes_the_host_header(raw, expected):
    assert normalize_host(raw) == expected


def test_new_organization_rejects_an_invalid_slug_or_hostname():
    with pytest.raises(ValidationError):
        NewOrganization(slug="Acme Corp", name="Acme", hostnames=["acme.localhost"])
    with pytest.raises(ValidationError):
        NewOrganization(slug="acme", name="Acme", hostnames=["acme_corp.localhost"])


def test_uses_the_host_header_by_default():
    assert request_host(make_request("acme.localhost:5173")) == "acme.localhost"


def test_ignores_forwarded_host_from_an_untrusted_client(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXIES", "172.16.0.0/12")
    get_settings.cache_clear()

    request = make_request("localhost", forwarded="acme.localhost", client="203.0.113.7")

    assert request_host(request) == "localhost"


def test_honors_forwarded_host_from_a_trusted_proxy(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXIES", "172.16.0.0/12")
    get_settings.cache_clear()

    request = make_request("api:8000", forwarded="acme.localhost:5173, proxy.internal", client="172.18.0.5")

    assert request_host(request) == "acme.localhost"


def test_client_ip_comes_from_a_trusted_proxy_only(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXIES", "172.16.0.0/12")
    get_settings.cache_clear()
    headers = [(b"host", b"localhost"), (b"x-forwarded-for", b"198.51.100.4, 10.0.0.1")]

    trusted = Request({"type": "http", "headers": headers, "client": ("172.18.0.5", 1)})
    direct = Request({"type": "http", "headers": headers, "client": ("203.0.113.7", 1)})

    assert client_ip(trusted) == "198.51.100.4"
    assert client_ip(direct) == "203.0.113.7"
