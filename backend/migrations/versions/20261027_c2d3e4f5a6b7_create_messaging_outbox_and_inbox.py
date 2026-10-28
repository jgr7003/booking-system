"""create messaging outbox and inbox

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-10-27 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'c2d3e4f5a6b7'
down_revision: str | None = 'b1c2d3e4f5a6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Applies this migration."""
    op.execute("CREATE SCHEMA IF NOT EXISTS messaging")
    op.create_table('outbox',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('exchange', sa.Text(), nullable=False),
    sa.Column('routing_key', sa.Text(), nullable=False),
    sa.Column('aggregate_id', sa.UUID(), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_outbox')),
    schema='messaging'
    )
    op.create_index('ix_outbox_pending', 'outbox', ['created_at'], unique=False, schema='messaging', postgresql_where=sa.text('published_at IS NULL'))
    op.create_table('inbox',
    sa.Column('message_id', sa.UUID(), nullable=False),
    sa.Column('consumer', sa.Text(), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('message_id', 'consumer', name=op.f('pk_inbox')),
    schema='messaging'
    )


def downgrade() -> None:
    """Reverts this migration."""
    op.drop_table('inbox', schema='messaging')
    op.drop_index('ix_outbox_pending', table_name='outbox', schema='messaging', postgresql_where=sa.text('published_at IS NULL'))
    op.drop_table('outbox', schema='messaging')
    op.execute("DROP SCHEMA messaging")
