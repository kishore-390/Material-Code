"""dynamic organizations + upload history

Adds description/logo_url to cpse_organizations and a new upload_batches
table for async bulk-upload tracking. Purely additive: no drops, no data
touched, existing rows get NULL for the two new nullable columns.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-03 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cpse_organizations", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("cpse_organizations", sa.Column("logo_url", sa.String(500), nullable=True))

    op.create_table(
        "upload_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cpse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cpse_organizations.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("total_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="VALIDATING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_upload_batches_cpse_id", "upload_batches", ["cpse_id"])
    op.create_index("ix_upload_batches_status", "upload_batches", ["status"])


def downgrade() -> None:
    op.drop_index("ix_upload_batches_status", table_name="upload_batches")
    op.drop_index("ix_upload_batches_cpse_id", table_name="upload_batches")
    op.drop_table("upload_batches")
    op.drop_column("cpse_organizations", "logo_url")
    op.drop_column("cpse_organizations", "description")
