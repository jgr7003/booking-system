import uuid
from datetime import date

import pytest

from app.travellers.public import Gender, Title, TravellerProfile, get_profile, save_profile

pytestmark = pytest.mark.anyio


async def test_a_user_without_bookings_for_themselves_has_no_profile(db_session_factory):
    async with db_session_factory() as session:
        assert await get_profile(session, uuid.uuid4()) is None


async def test_keeps_the_profile_and_replaces_it_with_the_latest_data(db_session_factory):
    user_id = uuid.uuid4()
    first = TravellerProfile(title=Title.MS, born_on=date(1990, 5, 20), gender=Gender.FEMALE)
    latest = TravellerProfile(title=Title.MRS, born_on=date(1990, 5, 21), gender=Gender.FEMALE)

    async with db_session_factory() as session, session.begin():
        await save_profile(session, user_id, first)
    async with db_session_factory() as session, session.begin():
        await save_profile(session, user_id, latest)

    async with db_session_factory() as session:
        assert await get_profile(session, user_id) == latest


async def test_saves_nothing_when_the_callers_transaction_rolls_back(db_session_factory):
    user_id = uuid.uuid4()
    async with db_session_factory() as session:
        profile = TravellerProfile(title=Title.MR, born_on=date(1985, 1, 2), gender=Gender.MALE)
        await save_profile(session, user_id, profile)
        await session.rollback()

    async with db_session_factory() as session:
        assert await get_profile(session, user_id) is None
