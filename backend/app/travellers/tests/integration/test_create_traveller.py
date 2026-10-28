import pytest
from sqlalchemy import func, select

from app.travellers.domain.models import IdentityDocument, Traveller
from app.travellers.public import TravellerDetails, create_traveller

pytestmark = pytest.mark.anyio

# Personal data of a fictitious traveller with a passport.
DETAILS = TravellerDetails.model_validate(
    {
        "given_name": "Ana",
        "family_name": "Prueba",
        "born_on": "1990-05-20",
        "gender": "f",
        "email": "ana.prueba@example.com",
        "phone_number": "+5491112345678",
        "identity_documents": [{"number": "AB1234567", "issuing_country_code": "AR", "expires_on": "2032-01-01"}],
    }
)


async def test_saves_the_traveller_and_their_documents_in_the_callers_transaction(db_session_factory):
    async with db_session_factory() as session, session.begin():
        ref = await create_traveller(session, DETAILS)

    async with db_session_factory() as session:
        traveller = await session.get(Traveller, ref.id)
        assert (traveller.given_name, traveller.family_name, traveller.email) == ("Ana", "Prueba", "ana.prueba@example.com")
        assert [(d.type, d.number, d.issuing_country_code) for d in traveller.identity_documents] == [
            ("passport", "AB1234567", "AR")
        ]


async def test_saves_nothing_when_the_callers_transaction_rolls_back(db_session_factory):
    async with db_session_factory() as session:
        await create_traveller(session, DETAILS)
        await session.rollback()

    async with db_session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Traveller)) == 0
        assert await session.scalar(select(func.count()).select_from(IdentityDocument)) == 0


async def test_each_call_creates_a_new_traveller_because_there_are_no_accounts_yet(db_session_factory):
    async with db_session_factory() as session, session.begin():
        first = await create_traveller(session, DETAILS)
        second = await create_traveller(session, DETAILS)

    assert first.id != second.id
