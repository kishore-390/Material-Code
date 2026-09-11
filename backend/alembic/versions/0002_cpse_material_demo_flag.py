"""add is_demo_data to cpse_materials (demo-only CSV import provenance)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-07 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cpse_materials",
        sa.Column("is_demo_data", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_cpse_materials_is_demo_data", "cpse_materials", ["is_demo_data"])


def downgrade() -> None:
    op.drop_index("ix_cpse_materials_is_demo_data", table_name="cpse_materials")
    op.drop_column("cpse_materials", "is_demo_data")
