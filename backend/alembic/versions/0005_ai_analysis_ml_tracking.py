"""ml probability/status tracking on ai_analysis

Adds nullable ml_probability/ml_status to ai_analysis so each analysis
event records what the XGBoost ranker actually predicted (or that it was
unavailable) at the time of that decision - a permanent, auditable record
rather than a value recomputed on the fly for display only. Purely
additive: no drops, no data touched, existing rows get NULL.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-04 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ai_analysis", sa.Column("ml_probability", sa.Float(), nullable=True))
    op.add_column("ai_analysis", sa.Column("ml_status", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_analysis", "ml_status")
    op.drop_column("ai_analysis", "ml_probability")
