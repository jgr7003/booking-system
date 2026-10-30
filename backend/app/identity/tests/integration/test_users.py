"""Users against the test PostgreSQL."""

import uuid

import anyio
import pytest
from sqlalchemy import select

from app.identity.commands import add_organization_user
from app.identity.domain.dtos.users import NewUser
from app.identity.domain.errors.users import UserAlreadyExistsError
from app.identity.domain.models.users import User
from app.identity.services.users import create_user
from app.organizations.public import NewOrganization, create_organization

pytestmark = pytest.mark.anyio


async def test_email_is_unique_among_private_travellers(db_session_factory):
    async with db_session_factory() as session, session.begin():
        await create_user(session, NewUser(organization_id=None, email="Ana@Example.test", display_name="Ana"))

    async with db_session_factory() as session:
        with pytest.raises(UserAlreadyExistsError):
            await create_user(session, NewUser(organization_id=None, email="ana@example.test", display_name="Ana"))


async def test_database_rejects_two_private_travellers_with_the_same_email(db_session_factory):
    """The constraint, not only the service, guards the rule (NULLS NOT DISTINCT)."""
    async with db_session_factory() as session:
        session.add_all(
            [
                User(organization_id=None, email="ana@example.test", display_name="Ana", status="active"),
                User(organization_id=None, email="ana@example.test", display_name="Ana", status="active"),
            ]
        )
        with pytest.raises(Exception, match="uq_users_organization_id_email"):
            await session.flush()


async def test_same_email_may_exist_in_two_installations(db_session_factory):
    async with db_session_factory() as session, session.begin():
        await create_user(session, NewUser(organization_id=None, email="ana@acme.test", display_name="Ana"))
        await create_user(session, NewUser(organization_id=uuid.uuid4(), email="ana@acme.test", display_name="Ana"))

    async with db_session_factory() as session:
        count = len((await session.scalars(select(User).where(User.email == "ana@acme.test"))).all())
    assert count == 2


async def test_command_gives_access_to_an_organization_with_a_verified_email(db_session_factory):
    async with db_session_factory() as session, session.begin():
        await create_organization(session, NewOrganization(slug="acme", name="Acme", hostnames=["acme.localhost"]))

    code = await anyio.to_thread.run_sync(
        add_organization_user.main, ["--org", "acme", "--email", "Viajero@Acme.test", "--name", "Viajero"]
    )

    assert code == 0
    async with db_session_factory() as session:
        user = await session.scalar(select(User).where(User.email == "viajero@acme.test"))
    assert user.organization_id is not None
    assert user.email_verified_at is not None
    assert user.password is None


async def test_command_fails_for_an_unknown_organization(db_engine):
    code = await anyio.to_thread.run_sync(
        add_organization_user.main, ["--org", "nadie", "--email", "a@b.test", "--name", "A"]
    )

    assert code == 1
