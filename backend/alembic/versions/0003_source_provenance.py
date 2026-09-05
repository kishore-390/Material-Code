"""source-system provenance on materials

Adds nullable source_system/source_database/source_material_code/
last_synced_at columns to materials, so a material fetched from an
external CPSE database (IOCL/ONGC "fetch by code" flow) can be told
apart from one entered manually or via CSV/Excel, and so re-syncing the
same source record is idempotent. Purely additive: no drops, no data
touched, existing rows get NULL for the new columns.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-04 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("materials", sa.Column("source_system", sa.String(100), nullable=True))
    op.add_column("materials", sa.Column("source_database", sa.String(100), nullable=True))
    op.add_column("materials", sa.Column("source_material_code", sa.String(100), nullable=True))
    op.add_column("materials", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_materials_source_database", "materials", ["source_database"])
    op.create_index("ix_materials_source_material_code", "materials", ["source_material_code"])
    op.create_index(
        "ix_materials_source_identity", "materials", ["source_database", "source_material_code"]
    )


def downgrade() -> None:
    op.drop_index("ix_materials_source_identity", table_name="materials")
    op.drop_index("ix_materials_source_material_code", table_name="materials")
    op.drop_index("ix_materials_source_database", table_name="materials")
    op.drop_column("materials", "last_synced_at")
    op.drop_column("materials", "source_material_code")
    op.drop_column("materials", "source_database")
    op.drop_column("materials", "source_system")
