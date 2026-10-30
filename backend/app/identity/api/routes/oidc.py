"""Endpoints of sign in through OIDC providers (Authorization Code + PKCE)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.identity.api.dependencies import device_info, device_key, get_oidc_login
from app.identity.api.mappers.auth import (
    to_account_not_found_response,
    to_auth_methods_response,
    to_callback_response,
    to_token_response,
)
from app.identity.api.schemas.auth import (
    AccountNotFoundResponse,
    AuthMethodsResponse,
    AuthorizeResponse,
    SignedInResponse,
    TokenResponse,
)
from app.identity.domain.dtos.oidc import AuthorizeRequest, CallbackRequest, SignupDecision
from app.identity.domain.dtos.tokens import DeviceInfo
from app.identity.services.oidc_login import OidcLogin
from app.organizations.public import Installation, current_installation

router = APIRouter(prefix="/auth")


def named(device: DeviceInfo, device_name: str | None) -> DeviceInfo:
    """The device with the name the client sent, if any."""
    return device.model_copy(update={"device_name": device_name}) if device_name else device


# FastAPI publishes the docstring as the endpoint's description in Swagger, so it is written for
# API consumers instead of following the Google sections.
@router.get("/methods", response_model=AuthMethodsResponse)
async def methods(
    installation: Annotated[Installation, Depends(current_installation)],
    login: Annotated[OidcLogin, Depends(get_oidc_login)],
) -> AuthMethodsResponse:
    """How people sign in to this installation: email and password (if allowed) and one button per provider."""
    return to_auth_methods_response(installation, await login.providers(installation))


@router.post("/oidc/{provider}/authorize", response_model=AuthorizeResponse)
async def authorize(
    provider: str,
    body: AuthorizeRequest,
    installation: Annotated[Installation, Depends(current_installation)],
    jkt: Annotated[str, Depends(device_key)],
    login: Annotated[OidcLogin, Depends(get_oidc_login)],
) -> AuthorizeResponse:
    """Starts a sign in through a provider; open `authorization_url` in the browser.

    Needs a `DPoP` proof: only this device can finish the sign in. The provider sends the browser
    back to `/auth/callback` of this app with `code` and `state`, which go to
    `POST /auth/oidc/{provider}/callback`. Unknown provider: `404 provider_not_found`.
    """
    url = await login.start(
        installation, provider, return_to=body.return_to, jkt=jkt, another_account=body.another_account
    )
    return AuthorizeResponse(authorization_url=url)


@router.post("/oidc/{provider}/callback", response_model=SignedInResponse | AccountNotFoundResponse)
async def callback(
    provider: str,
    body: CallbackRequest,
    installation: Annotated[Installation, Depends(current_installation)],
    device: Annotated[DeviceInfo, Depends(device_info)],
    login: Annotated[OidcLogin, Depends(get_oidc_login)],
) -> SignedInResponse | AccountNotFoundResponse:
    """Finishes the sign in with the `code` and `state` the provider sent back.

    `status: signed_in` brings the tokens. `status: account_not_found` shows «No encontramos tu
    cuenta»: create it (`POST /auth/signup/pending/{attempt_id}`, only if `can_create`) or try
    another account (`DELETE` on the same path); those two answer `400 invalid_login_attempt` if the
    decision expired or comes from another device. Needs a `DPoP` proof of the device that started
    the sign in. Any failure of the sign in itself (expired or used sign in, another device, an answer of the provider
    that isn't valid, an unverified email, a blocked address) is `401 login_failed`, always with
    the same message: «No pudimos iniciar sesión».
    """
    result = await login.finish(
        installation, provider, code=body.code, state=body.state, device=named(device, body.device_name)
    )
    return to_callback_response(result)


@router.get("/signup/pending/{attempt_id}", response_model=AccountNotFoundResponse)
async def pending_signup(
    attempt_id: uuid.UUID,
    installation: Annotated[Installation, Depends(current_installation)],
    jkt: Annotated[str, Depends(device_key)],
    login: Annotated[OidcLogin, Depends(get_oidc_login)],
) -> AccountNotFoundResponse:
    """The identity waiting for the «create account» decision, to show it again after a reload."""
    return to_account_not_found_response(await login.pending_identity(installation, attempt_id, jkt))


@router.post("/signup/pending/{attempt_id}", response_model=TokenResponse)
async def create_account(
    attempt_id: uuid.UUID,
    body: SignupDecision,
    installation: Annotated[Installation, Depends(current_installation)],
    device: Annotated[DeviceInfo, Depends(device_info)],
    login: Annotated[OidcLogin, Depends(get_oidc_login)],
) -> TokenResponse:
    """«Crear cuenta»: creates the account with what the provider verified and signs this device in.

    The account starts without a password; an email lets the person create one. Phone and language
    are optional. Only for private travellers: in an organization, `403 signup_not_allowed`.
    """
    result = await login.create_account(installation, attempt_id, named(device, body.device_name), body)
    return to_token_response(result.tokens, result.return_to)


@router.delete("/signup/pending/{attempt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def discard_signup(
    attempt_id: uuid.UUID,
    installation: Annotated[Installation, Depends(current_installation)],
    jkt: Annotated[str, Depends(device_key)],
    login: Annotated[OidcLogin, Depends(get_oidc_login)],
) -> None:
    """«Usar otra cuenta»: forgets the identity; start the sign in again (Google shows its account picker)."""
    await login.discard(installation, attempt_id, jkt)
