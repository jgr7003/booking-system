"""From identity DTOs to the public schemas."""

import uuid

from app.identity.api.schemas.auth import (
    AccountNotFoundResponse,
    AuthMethodsResponse,
    DeviceSessionListResponse,
    DeviceSessionResponse,
    MeResponse,
    OrganizationSummary,
    ProviderOption,
    SignedInResponse,
    TokenResponse,
    TravellerProfileSummary,
)
from app.identity.domain.dtos.oidc import AccountNotFound, SignedIn
from app.identity.domain.dtos.tokens import DeviceSessionView, TokenPair
from app.identity.domain.dtos.users import UserRef
from app.organizations.public import Installation, OrganizationRef
from app.travellers.public import TravellerProfile


def to_token_response(pair: TokenPair, return_to: str | None = None) -> TokenResponse:
    """Builds the answer of a sign in or a refresh.

    Args:
        pair: The new tokens.
        return_to: Path of the app to go back to, if any.

    Returns:
        The response.
    """
    return TokenResponse(
        access_token=pair.access_token,
        expires_in=pair.expires_in,
        refresh_token=pair.refresh_token,
        session_id=pair.session_id,
        return_to=return_to,
    )


def to_me_response(
    user: UserRef, organization: OrganizationRef | None, profile: TravellerProfile | None, session_id: uuid.UUID
) -> MeResponse:
    """Builds the view of the signed-in user.

    Args:
        user: The user.
        organization: Their organization, if any.
        profile: Their passenger data for their own trips, if they booked for themselves.
        session_id: Device session of the request.

    Returns:
        The response.
    """
    return MeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        organization=OrganizationSummary(id=organization.id, name=organization.name) if organization else None,
        has_password=user.has_password,
        phone_number=user.phone_number,
        language=user.language,
        traveller_profile=(
            TravellerProfileSummary(title=profile.title, born_on=profile.born_on, gender=profile.gender)
            if profile
            else None
        ),
        session_id=session_id,
    )


def to_device_sessions_response(
    sessions: list[DeviceSessionView], current_session_id: uuid.UUID
) -> DeviceSessionListResponse:
    """Builds the list of connected devices.

    Args:
        sessions: Open sessions of the user.
        current_session_id: Session of the request, marked as `current`.

    Returns:
        The response.
    """
    return DeviceSessionListResponse(
        sessions=[
            DeviceSessionResponse(
                id=s.id,
                device_name=s.device_name,
                created_at=s.created_at,
                last_seen_at=s.last_seen_at,
                last_ip=s.last_ip,
                current=s.id == current_session_id,
            )
            for s in sessions
        ]
    )


def to_callback_response(result: SignedIn | AccountNotFound) -> SignedInResponse | AccountNotFoundResponse:
    """Builds the answer of the provider's callback.

    Args:
        result: The session, or the identity waiting for the decision.

    Returns:
        The response.
    """
    if isinstance(result, SignedIn):
        return SignedInResponse(tokens=to_token_response(result.tokens, result.return_to))
    return to_account_not_found_response(result)


def to_account_not_found_response(result: AccountNotFound) -> AccountNotFoundResponse:
    """Builds the «no encontramos tu cuenta» answer.

    Args:
        result: The identity waiting for the decision.

    Returns:
        The response.
    """
    return AccountNotFoundResponse(
        attempt_id=result.attempt_id,
        email=result.email,
        display_name=result.display_name,
        can_create=result.can_create,
    )


def to_auth_methods_response(installation: Installation, providers: list[tuple[str, str]]) -> AuthMethodsResponse:
    """Builds the sign-in methods of an installation.

    Args:
        installation: The installation.
        providers: `(slug, display_name)` of its enabled providers.

    Returns:
        The response.
    """
    return AuthMethodsResponse(
        organization_name=installation.organization.name if installation.organization else None,
        password_enabled=installation.settings.password_login_enabled,
        signup_enabled=installation.organization is None,
        providers=[ProviderOption(slug=slug, display_name=name) for slug, name in providers],
    )
