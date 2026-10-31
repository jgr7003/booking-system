"""blocked ips per installation

Revision ID: 53b82df3890e
Revises: 6196dd8edd78
Create Date: 2026-10-29 16:02:56.823561
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '53b82df3890e'
down_revision: str | None = '6196dd8edd78'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Applies this migration.

    The blocks become per installation. They only hold temporary blocks (60 min), so the table is
    recreated instead of migrating its rows.
    """
    op.drop_table("blocked_ips", schema="identity")
    _create(per_installation=True)


def downgrade() -> None:
    """Reverts this migration."""
    op.drop_table("blocked_ips", schema="identity")
    _create(per_installation=False)


def _create(*, per_installation: bool) -> None:
    """Creates `identity.blocked_ips`, per installation or (before this migration) per address only."""
    columns = [
        sa.Column("ip", postgresql.INET(), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("blocked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]
    if per_installation:
        columns = [
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("organization_id", sa.UUID(), nullable=True),
            *columns,
            sa.PrimaryKeyConstraint("id", name=op.f("pk_blocked_ips")),
            sa.UniqueConstraint(
                "organization_id", "ip", name=op.f("uq_blocked_ips_organization_id_ip"), postgresql_nulls_not_distinct=True
            ),
        ]
    else:
        columns.append(sa.PrimaryKeyConstraint("ip", name=op.f("pk_blocked_ips")))
    op.create_table("blocked_ips", *columns, schema="identity")
