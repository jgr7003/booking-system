"""Endpoints of the signed-in user and their connected devices."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import get_db_session, get_session_factory
from app.identity.api.dependencies import current_principal, get_session_cache
from app.identity.api.mappers.auth import to_device_sessions_response, to_me_response
from app.identity.api.schemas.auth import DeviceSessionListResponse, MeResponse
from app.identity.domain.dtos.tokens import Principal, RevocationReason
from app.identity.domain.errors.sessions import DeviceSessionNotFoundError
from app.identity.domain.errors.tokens import SessionRevokedError
from app.identity.services.sessions import (
    SessionStatusCache,
    list_device_sessions,
    revoke_device_sessions,
    revoke_user_sessions,
)
from app.identity.services.users import get_user
from app.organizations.public import get_organization
from app.travellers.public import get_profile

router = APIRouter(prefix="/me")


# FastAPI publishes the docstring as the endpoint's description in Swagger, so it is written for
# API consumers instead of following the Google sections.
@router.get("", response_model=MeResponse)
async def me(
    principal: Annotated[Principal, Depends(current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MeResponse:
    """The signed-in user, read fresh (the access token may be up to 10 minutes old).

    `traveller_profile` holds the passenger data of their last booking for themselves (title, date
    of birth and gender), to fill the next one; `null` until they book for themselves.
    """
    user = await get_user(session, principal.user_id)
    if user is None:
        raise SessionRevokedError("The session was closed.")
    organization = await get_organization(session, user.organization_id) if user.organization_id else None
    profile = await get_profile(session, user.id)
    return to_me_response(user, organization, profile, principal.session_id)


@router.get("/sessions", response_model=DeviceSessionListResponse)
async def sessions(
    principal: Annotated[Principal, Depends(current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DeviceSessionListResponse:
    """Devices with an open session, most recently used first. `current` marks this one."""
    return to_device_sessions_response(await list_device_sessions(session, principal.user_id), principal.session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def close_session(
    session_id: uuid.UUID,
    principal: Annotated[Principal, Depends(current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    cache: Annotated[SessionStatusCache, Depends(get_session_cache)],
) -> None:
    """Closes the session of one of the user's devices; on its next request it gets `401 session_revoked`.

    A session of another user, or one already closed, is `404 session_not_found`.
    """
    if session_id not in {s.id for s in await list_device_sessions(session, principal.user_id)}:
        raise DeviceSessionNotFoundError("There is no such open session.")
    await revoke_device_sessions(session_factory, cache, [session_id], RevocationReason.USER_REVOKED)


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def close_other_sessions(
    scope: Annotated[Literal["others"], Query(description="Only `others` is supported: every device but this one.")],
    principal: Annotated[Principal, Depends(current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    cache: Annotated[SessionStatusCache, Depends(get_session_cache)],
) -> None:
    """Closes the sessions of every device of the user except this one."""
    async with session.begin():
        await revoke_user_sessions(
            session, cache, principal.user_id, RevocationReason.USER_REVOKED, keep=principal.session_id
        )
