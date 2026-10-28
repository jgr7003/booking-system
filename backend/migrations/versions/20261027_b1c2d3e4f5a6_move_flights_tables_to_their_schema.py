"""move flights tables to their schema

Each module keeps its tables in its own PostgreSQL schema (docs/architecture/00-global.md §4.1).
`SET SCHEMA` moves the tables with their indexes and constraints, without copying data.

Revision ID: b1c2d3e4f5a6
Revises: 4ae4f4da894e
Create Date: 2026-10-27 09:30:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = 'b1c2d3e4f5a6'
down_revision: str | None = '4ae4f4da894e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Applies this migration."""
    op.execute("CREATE SCHEMA IF NOT EXISTS flights")
    op.execute("ALTER TABLE public.cities SET SCHEMA flights")
    op.execute("ALTER TABLE public.airports SET SCHEMA flights")


def downgrade() -> None:
    """Reverts this migration."""
    op.execute("ALTER TABLE flights.airports SET SCHEMA public")
    op.execute("ALTER TABLE flights.cities SET SCHEMA public")
    op.execute("DROP SCHEMA flights")
