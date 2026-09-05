"""technical conflict detection on ai_analysis

Adds nullable technical_conflict/conflict_reason to ai_analysis so a
detected specification-level incompatibility (grade, dimension, thread
size, voltage, pressure mismatch) between a material and its best
candidate is permanently recorded alongside the score that produced it,
rather than recomputed on the fly for display only. Purely additive: no
drops, no data touched, existing rows get NULL/false defaults.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-05 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_analysis",
        sa.Column("technical_conflict", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("ai_analysis", sa.Column("conflict_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_analysis", "conflict_reason")
    op.drop_column("ai_analysis", "technical_conflict")
