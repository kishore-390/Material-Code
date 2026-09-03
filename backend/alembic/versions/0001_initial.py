"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEXT_EMBEDDING_DIM = 384
IMAGE_EMBEDDING_DIM = 512


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE SEQUENCE IF NOT EXISTS common_material_code_seq START WITH 1 INCREMENT BY 1")

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_roles_name", "roles", ["name"])

    op.create_table(
        "cpse_organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cpse_organizations_code", "cpse_organizations", ["code"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("cpse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cpse_organizations.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "common_material_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("material_type", sa.String(150), nullable=False),
        sa.Column("category", sa.String(150), nullable=False),
        sa.Column("standard_description", sa.Text(), nullable=False),
        sa.Column("standard_specification", sa.Text(), nullable=True),
        sa.Column("uom", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="AUTO_GENERATED"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_common_material_codes_code", "common_material_codes", ["code"])
    op.create_index("ix_common_material_codes_category", "common_material_codes", ["category"])
    op.create_index("ix_common_material_codes_status", "common_material_codes", ["status"])

    op.create_table(
        "materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("material_code", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("normalized_description", sa.Text(), nullable=True),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("normalized_specification", sa.Text(), nullable=True),
        sa.Column("category", sa.String(150), nullable=False),
        sa.Column("normalized_category", sa.String(150), nullable=True),
        sa.Column("uom", sa.String(50), nullable=False),
        sa.Column("normalized_uom", sa.String(50), nullable=True),
        sa.Column("cpse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cpse_organizations.id"), nullable=False),
        sa.Column("manufacturer", sa.String(255), nullable=True),
        sa.Column("brand", sa.String(150), nullable=True),
        sa.Column("material_type", sa.String(150), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("common_code_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("common_material_codes.id"), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_materials_material_code", "materials", ["material_code"])
    op.create_index("ix_materials_cpse_id", "materials", ["cpse_id"])
    op.create_index("ix_materials_category", "materials", ["category"])
    op.create_index("ix_materials_uom", "materials", ["uom"])
    op.create_index("ix_materials_normalized_description", "materials", ["normalized_description"])
    op.create_index("ix_materials_status", "materials", ["status"])
    op.create_index("ix_materials_common_code_id", "materials", ["common_code_id"])
    op.create_index("ix_materials_code_cpse", "materials", ["material_code", "cpse_id"], unique=True)

    op.create_table(
        "material_attributes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attr_key", sa.String(150), nullable=False),
        sa.Column("attr_value", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_material_attributes_material_id", "material_attributes", ["material_id"])

    op.create_table(
        "material_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_material_images_material_id", "material_images", ["material_id"])

    op.create_table(
        "material_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("text_embedding", Vector(TEXT_EMBEDDING_DIM), nullable=True),
        sa.Column("image_embedding", Vector(IMAGE_EMBEDDING_DIM), nullable=True),
        sa.Column("embedding_model", sa.String(150), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_material_embeddings_material_id", "material_embeddings", ["material_id"])
    # HNSW rather than IVFFlat: IVFFlat's cluster count has to be tuned to the
    # row count (its k-means-style clustering is unstable when "lists" is
    # anywhere near or above the number of rows per category, which is exactly
    # this dataset's scale). HNSW gives accurate, stable nearest-neighbor
    # results without that tuning, at any scale from hundreds to millions of rows.
    op.execute(
        "CREATE INDEX ix_material_embeddings_text_vector ON material_embeddings "
        "USING hnsw (text_embedding vector_cosine_ops)"
    )

    op.create_table(
        "material_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("description_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("specification_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("category_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("uom_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("image_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("attribute_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("vector_distance", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_material_matches_material_id", "material_matches", ["material_id"])
    op.create_index("ix_material_matches_candidate_material_id", "material_matches", ["candidate_material_id"])

    op.create_table(
        "ai_analysis",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("best_candidate_material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id"), nullable=True),
        sa.Column("final_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("description_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("specification_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("category_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("uom_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("image_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("attribute_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("recommended_common_code", sa.String(100), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="COMPLETED"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_analysis_material_id", "ai_analysis", ["material_id"])
    op.create_index("ix_ai_analysis_decision", "ai_analysis", ["decision"])

    op.create_table(
        "harmonization_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id"), nullable=True),
        sa.Column("ai_analysis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_analysis.id"), nullable=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("request_type", sa.String(20), nullable=False, server_default="AI_AUTO"),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("common_code_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("common_material_codes.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_harmonization_requests_material_id", "harmonization_requests", ["material_id"])
    op.create_index("ix_harmonization_requests_status", "harmonization_requests", ["status"])

    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("harmonization_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("harmonization_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("candidate_material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id"), nullable=True),
        sa.Column("ai_score", sa.Float(), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_approval_requests_harmonization_request_id", "approval_requests", ["harmonization_request_id"])
    op.create_index("ix_approval_requests_material_id", "approval_requests", ["material_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])

    op.create_table(
        "approval_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_approval_actions_approval_request_id", "approval_actions", ["approval_request_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_type", sa.String(20), nullable=False, server_default="USER"),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_name", sa.String(255), nullable=False, server_default="AI ENGINE"),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role_target", sa.String(50), nullable=True),
        sa.Column("type", sa.String(60), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("related_entity_type", sa.String(100), nullable=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_role_target", "notifications", ["role_target"])
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])

    op.create_table(
        "system_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_system_settings_key", "system_settings", ["key"])


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("notifications")
    op.drop_table("audit_logs")
    op.drop_table("approval_actions")
    op.drop_table("approval_requests")
    op.drop_table("harmonization_requests")
    op.drop_table("ai_analysis")
    op.drop_table("material_matches")
    op.execute("DROP INDEX IF EXISTS ix_material_embeddings_text_vector")
    op.drop_table("material_embeddings")
    op.drop_table("material_images")
    op.drop_table("material_attributes")
    op.drop_table("materials")
    op.drop_table("common_material_codes")
    op.drop_table("users")
    op.drop_table("cpse_organizations")
    op.drop_table("roles")
    op.execute("DROP SEQUENCE IF EXISTS common_material_code_seq")
