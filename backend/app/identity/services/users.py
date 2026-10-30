"""Use cases of users that don't depend on how they sign in."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.dtos.users import NewUser, UserRef
from app.identity.domain.errors.users import UserAlreadyExistsError
from app.identity.domain.models.users import User
from app.identity.repositories.users import UserRepository


def to_user_ref(user: User) -> UserRef:
    """Converts a database row into a DTO.

    Args:
        user: The row, with its password loaded.

    Returns:
        The user.
    """
    return UserRef(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        display_name=user.display_name,
        email_verified=user.email_verified_at is not None,
        has_password=user.password is not None,
        phone_number=user.phone_number,
        language=user.language,
    )


async def create_user(session: AsyncSession, new: NewUser) -> User:
    """Creates a user inside the caller's transaction.

    Args:
        session: Session of the caller's transaction.
        new: Validated data of the user.

    Returns:
        The new user.

    Raises:
        UserAlreadyExistsError: The installation already has a user with that email.
    """
    repository = UserRepository(session)
    if await repository.find_by_email(new.organization_id, new.email) is not None:
        raise UserAlreadyExistsError("There is already an account with that email.")
    return await repository.add(new)


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> UserRef | None:
    """Reads a user.

    Args:
        session: An open session.
        user_id: Id of the user.

    Returns:
        The user, or `None`.
    """
    user = await UserRepository(session).get(user_id)
    return to_user_ref(user) if user else None
