"""confidence/decision traceability on common material codes

Adds nullable confidence_score/decision_status to common_material_codes so
the Common Material Master can show the AI confidence and decision that
produced (or most recently reused) each code, without touching the
materials table or any other existing data. Purely additive.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-04 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("common_material_codes", sa.Column("confidence_score", sa.Float(), nullable=True))
    op.add_column("common_material_codes", sa.Column("decision_status", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("common_material_codes", "decision_status")
    op.drop_column("common_material_codes", "confidence_score")
