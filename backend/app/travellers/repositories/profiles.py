"""Persistence of the users' traveller profiles in PostgreSQL."""

import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.travellers.domain.dtos import TravellerProfile
from app.travellers.domain.models import Profile


class ProfileRepository:
    """Reads and writes `travellers.profiles`, inside the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        """Initializes the repository.

        Args:
            session: Session of the transaction to work in. The repository never commits.
        """
        self._session = session

    async def get(self, user_id: uuid.UUID) -> Profile | None:
        """Reads the profile of a user.

        Args:
            user_id: Id of the user.

        Returns:
            The profile, or `None` if the user never booked for themselves.
        """
        return await self._session.get(Profile, user_id)

    async def save(self, user_id: uuid.UUID, profile: TravellerProfile) -> None:
        """Creates or replaces the profile of a user in one statement (two bookings at once can't clash).

        Args:
            user_id: Id of the user.
            profile: The data to keep.
        """
        values = {"title": profile.title.value, "born_on": profile.born_on, "gender": profile.gender.value}
        statement = insert(Profile).values(user_id=user_id, **values)
        statement = statement.on_conflict_do_update(
            index_elements=[Profile.user_id], set_={**values, "updated_at": func.now()}
        )
        await self._session.execute(statement)
