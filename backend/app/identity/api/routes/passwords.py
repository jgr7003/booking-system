"""Endpoints of email-and-password accounts and of the links sent by email."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.identity.api.dependencies import client_ip, device_info, get_password_accounts
from app.identity.api.mappers.auth import to_token_response
from app.identity.api.schemas.auth import LookupResponse, PasswordLinkResponse, TokenResponse
from app.identity.domain.dtos.passwords import (
    EmailRequest,
    EmailVerificationRequest,
    LinkTokenRequest,
    LoginRequest,
    LookupRequest,
    SetPasswordRequest,
    SignupRequest,
)
from app.identity.domain.dtos.tokens import DeviceInfo
from app.identity.services.passwords import PasswordAccounts
from app.organizations.public import Installation, current_installation

router = APIRouter(prefix="/auth")


def named(device: DeviceInfo, device_name: str | None) -> DeviceInfo:
    """The device with the name the client sent, if any."""
    return device.model_copy(update={"device_name": device_name}) if device_name else device


# FastAPI publishes the docstring as the endpoint's description in Swagger, so it is written for
# API consumers instead of following the Google sections.
@router.post("/password/lookup", response_model=LookupResponse)
async def lookup(
    body: LookupRequest,
    request: Request,
    installation: Annotated[Installation, Depends(current_installation)],
    accounts: Annotated[PasswordAccounts, Depends(get_password_accounts)],
) -> LookupResponse:
    """First step of the sign in: whether the email has an account here and whether it has a password.

    `exists: false` shows «No encontramos tu cuenta». `has_password: false` means the account signs
    in with an identity provider (or sets a password from `POST /auth/password/forgot`).
    Unknown emails count against the address. A blocked address gets `401 login_failed`. In an
    installation without passwords: `404`.
    """
    result = await accounts.lookup(installation, body.email, client_ip(request))
    return LookupResponse(exists=result.exists, has_password=result.has_password)


@router.post("/password/signup", status_code=status.HTTP_202_ACCEPTED)
async def sign_up(
    body: SignupRequest,
    request: Request,
    installation: Annotated[Installation, Depends(current_installation)],
    accounts: Annotated[PasswordAccounts, Depends(get_password_accounts)],
) -> None:
    """Creates a private traveller's account and emails a link to verify it.

    The account can't sign in until the link is opened (`POST /auth/email/verify`). An email that
    already has a verified account: `409 user_already_exists`. Only in the main installation;
    organizations create their users themselves (`404` there).
    """
    await accounts.sign_up(installation, body, client_ip(request))


@router.post("/email/verify", response_model=TokenResponse)
async def verify_email(
    body: EmailVerificationRequest,
    installation: Annotated[Installation, Depends(current_installation)],
    device: Annotated[DeviceInfo, Depends(device_info)],
    accounts: Annotated[PasswordAccounts, Depends(get_password_accounts)],
) -> TokenResponse:
    """Verifies the email with the token of the link and signs this device in.

    Needs a `DPoP` proof of the device. Unknown, expired or used link: `410 invalid_link`.
    """
    pair = await accounts.verify_email(installation, body.token, named(device, body.device_name))
    return to_token_response(pair)


@router.post("/password/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    installation: Annotated[Installation, Depends(current_installation)],
    device: Annotated[DeviceInfo, Depends(device_info)],
    accounts: Annotated[PasswordAccounts, Depends(get_password_accounts)],
) -> TokenResponse:
    """Signs this device in with email and password.

    Needs a `DPoP` proof of the device: the session is bound to its key. Any failure is `401
    login_failed` with the same message («No pudimos iniciar sesión»), so an attacker can't tell a
    wrong password from an unknown, blocked or unverified account. After `max_failed_logins` wrong
    passwords in a row (setting of the installation, 3 by default) the password sign in is blocked
    and the user gets an email to change it; too many failures from one address block it. In an
    installation without passwords: `404`.
    """
    pair = await accounts.sign_in(installation, body, named(device, body.device_name))
    return to_token_response(pair)


@router.post("/password/forgot", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    body: EmailRequest,
    request: Request,
    installation: Annotated[Installation, Depends(current_installation)],
    accounts: Annotated[PasswordAccounts, Depends(get_password_accounts)],
) -> None:
    """Emails a link to choose a new password, or to create the first one.

    Always answers `202`, whether the account exists or not.
    """
    await accounts.forgot_password(installation, body.email, client_ip(request))


@router.post("/password/set", status_code=status.HTTP_204_NO_CONTENT)
async def set_password(
    body: SetPasswordRequest,
    installation: Annotated[Installation, Depends(current_installation)],
    accounts: Annotated[PasswordAccounts, Depends(get_password_accounts)],
) -> None:
    """Sets the password from the token of an email link (first password or a reset).

    It also unblocks an account blocked by wrong passwords.

    A reset closes the session on every device of the user. Then sign in with
    `POST /auth/password/login`. Unknown, expired or used link: `410 invalid_link`.
    """
    await accounts.set_password(installation, body)


@router.post("/password/link", response_model=PasswordLinkResponse)
async def password_link(
    body: LinkTokenRequest,
    installation: Annotated[Installation, Depends(current_installation)],
    accounts: Annotated[PasswordAccounts, Depends(get_password_accounts)],
) -> PasswordLinkResponse:
    """What a link to create or recover the password is for, without using it.

    The screen shows the email of the account and, for a first password, what else it signs in with
    («Vas a poder seguir entrando también con Google»). Unknown, expired or used link: `410
    invalid_link`.
    """
    info = await accounts.link_info(installation, body.token)
    return PasswordLinkResponse(email=info.email, kind=info.kind, signs_in_with=info.signs_in_with)
