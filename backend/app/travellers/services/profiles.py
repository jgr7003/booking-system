"""Use cases of the users' traveller profiles."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.travellers.domain.dtos import Gender, Title, TravellerProfile
from app.travellers.repositories.profiles import ProfileRepository


async def get_profile(session: AsyncSession, user_id: uuid.UUID) -> TravellerProfile | None:
    """Reads the passenger data a user keeps for their own trips.

    Args:
        session: An open session.
        user_id: Id of the user.

    Returns:
        The profile, or `None` if the user never booked for themselves.
    """
    profile = await ProfileRepository(session).get(user_id)
    if profile is None:
        return None
    # Validated when saved; validating again could reject old data that was valid then.
    return TravellerProfile.model_construct(
        title=Title(profile.title), born_on=profile.born_on, gender=Gender(profile.gender)
    )


async def save_profile(session: AsyncSession, user_id: uuid.UUID, profile: TravellerProfile) -> None:
    """Keeps the passenger data of a user who books for themselves, inside the caller's transaction.

    Only for the account holder: a booking for someone else never calls it, so that person's
    data stay only in that booking.

    Args:
        session: Session of the caller's transaction.
        user_id: Id of the user.
        profile: The data the user just booked with.
    """
    await ProfileRepository(session).save(user_id, profile)
