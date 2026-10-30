"""Endpoints of the platform's tokens: public keys, refresh and sign out."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import get_session_factory
from app.identity.api.dependencies import client_ip, current_principal, device_key, get_session_cache
from app.identity.api.mappers.auth import to_token_response
from app.identity.api.schemas.auth import RefreshRequest, TokenResponse
from app.identity.domain.dtos.tokens import Principal, RevocationReason
from app.identity.services.sessions import SessionStatusCache, refresh_device_session, revoke_device_sessions
from app.identity.tokens.signing import public_jwks
from app.organizations.public import Installation, current_installation

router = APIRouter(prefix="/auth")


# FastAPI publishes the docstring as the endpoint's description in Swagger, so it is written for
# API consumers instead of following the Google sections.
@router.get("/jwks.json")
async def jwks() -> dict[str, Any]:
    """Public keys that sign the access tokens (ES256), by `kid`.

    Anyone can verify a token with them; only the platform can sign. During a key rotation the old
    key stays here until the tokens it signed expire.
    """
    return public_jwks()


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    jkt: Annotated[str, Depends(device_key)],
    installation: Annotated[Installation, Depends(current_installation)],
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    cache: Annotated[SessionStatusCache, Depends(get_session_cache)],
) -> TokenResponse:
    """Exchanges the refresh token for a new pair; the old refresh token stops working.

    Needs a `DPoP` proof signed by the same device key the session was opened with. A refresh token
    used twice, or from another device, closes the session: `401 session_revoked`, and the device
    must sign in again. Unknown token: `401 invalid_token`.
    """
    pair = await refresh_device_session(
        session_factory,
        cache,
        refresh_token=body.refresh_token,
        jkt=jkt,
        issuer=installation.host,
        organization_id=installation.organization_id,
        ip=client_ip(request),
    )
    return to_token_response(pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    principal: Annotated[Principal, Depends(current_principal)],
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    cache: Annotated[SessionStatusCache, Depends(get_session_cache)],
) -> None:
    """Closes the session of this device. Its tokens stop working at once."""
    await revoke_device_sessions(session_factory, cache, [principal.session_id], RevocationReason.LOGOUT)
