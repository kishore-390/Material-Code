"""initial schema - AI-Powered National Unified Material Master

Revision ID: 0001
Revises:
Create Date: 2026-09-06 00:00:00

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
        "cpses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synchronization_status", sa.String(30), nullable=False, server_default="NEVER_SYNCED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cpses_code", "cpses", ["code"])
    op.create_index("ix_cpses_sector", "cpses", ["sector"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("cpse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cpses.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "source_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cpse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cpses.id"), nullable=False),
        sa.Column("connection_name", sa.String(150), nullable=False),
        sa.Column("database_type", sa.String(20), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("database_name", sa.String(150), nullable=False),
        sa.Column("username_reference", sa.String(150), nullable=False),
        sa.Column("secret_reference", sa.String(150), nullable=False),
        sa.Column("ssl_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("read_only", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("table_name", sa.String(150), nullable=False),
        sa.Column("column_mapping", postgresql.JSONB(), nullable=False),
        sa.Column("cursor_column", sa.String(100), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sync_interval_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("last_sync_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(30), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_synced_cursor", sa.String(60), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_source_connections_cpse_id", "source_connections", ["cpse_id"])

    op.create_table(
        "sync_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_connection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sync_type", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="RUNNING"),
        sa.Column("records_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_successful_cursor", sa.String(60), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sync_history_source_connection_id", "sync_history", ["source_connection_id"])
    op.create_index("ix_sync_history_status", "sync_history", ["status"])

    op.create_table(
        "common_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("common_code", sa.String(100), nullable=False, unique=True),
        sa.Column("standardized_description", sa.Text(), nullable=False),
        sa.Column("standardized_specification", sa.Text(), nullable=True),
        sa.Column("material_type", sa.String(150), nullable=False),
        sa.Column("material_grade", sa.String(100), nullable=True),
        sa.Column("dimensions", sa.String(255), nullable=True),
        sa.Column("standardized_uom", sa.String(50), nullable=False),
        sa.Column("standard", sa.String(150), nullable=True),
        sa.Column("function", sa.String(255), nullable=True),
        sa.Column("criticality", sa.String(30), nullable=False, server_default="UNSPECIFIED"),
        sa.Column("classification", sa.String(150), nullable=False),
        sa.Column("classification_path", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_common_materials_common_code", "common_materials", ["common_code"])
    op.create_index("ix_common_materials_classification", "common_materials", ["classification"])
    op.create_index("ix_common_materials_status", "common_materials", ["status"])

    op.create_table(
        "cpse_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cpse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cpses.id"), nullable=False),
        sa.Column("original_material_code", sa.String(100), nullable=False),
        sa.Column("original_description", sa.Text(), nullable=False),
        sa.Column("normalized_description", sa.Text(), nullable=True),
        sa.Column("material_type", sa.String(150), nullable=True),
        sa.Column("material_grade", sa.String(100), nullable=True),
        sa.Column("dimensions", sa.String(255), nullable=True),
        sa.Column("technical_specification", sa.Text(), nullable=True),
        sa.Column("normalized_specification", sa.Text(), nullable=True),
        sa.Column("uom", sa.String(50), nullable=False),
        sa.Column("normalized_uom", sa.String(50), nullable=True),
        sa.Column("manufacturer", sa.String(255), nullable=True),
        sa.Column("standard", sa.String(150), nullable=True),
        sa.Column("function", sa.String(255), nullable=True),
        sa.Column("classification", sa.String(150), nullable=True),
        sa.Column("normalized_classification", sa.String(150), nullable=True),
        sa.Column("classification_path", postgresql.JSONB(), nullable=True),
        sa.Column("packaging", sa.String(150), nullable=True),
        sa.Column("criticality", sa.String(30), nullable=False, server_default="UNSPECIFIED"),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "source_connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("source_connections.id"), nullable=True
        ),
        sa.Column("sync_history_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sync_history.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cpse_materials_original_material_code", "cpse_materials", ["original_material_code"])
    op.create_index("ix_cpse_materials_cpse_id", "cpse_materials", ["cpse_id"])
    op.create_index("ix_cpse_materials_material_type", "cpse_materials", ["material_type"])
    op.create_index("ix_cpse_materials_uom", "cpse_materials", ["uom"])
    op.create_index("ix_cpse_materials_normalized_description", "cpse_materials", ["normalized_description"])
    op.create_index("ix_cpse_materials_classification", "cpse_materials", ["classification"])
    op.create_index("ix_cpse_materials_status", "cpse_materials", ["status"])
    op.create_index("ix_cpse_materials_source_connection_id", "cpse_materials", ["source_connection_id"])
    op.create_index("ix_cpse_materials_sync_history_id", "cpse_materials", ["sync_history_id"])
    op.create_index(
        "ix_cpse_materials_code_cpse", "cpse_materials", ["original_material_code", "cpse_id"], unique=True
    )

    op.create_table(
        "material_attributes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cpse_materials.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("attr_key", sa.String(150), nullable=False),
        sa.Column("attr_value", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_material_attributes_material_id", "material_attributes", ["material_id"])

    op.create_table(
        "material_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cpse_materials.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("text_embedding", Vector(TEXT_EMBEDDING_DIM), nullable=True),
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
        sa.Column(
            "material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cpse_materials.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "candidate_material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cpse_materials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("description_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("specification_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("classification_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("uom_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("attribute_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("grade_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("dimension_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("standard_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("manufacturer_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("function_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("criticality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("vector_distance", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_material_matches_material_id", "material_matches", ["material_id"])
    op.create_index("ix_material_matches_candidate_material_id", "material_matches", ["candidate_material_id"])

    op.create_table(
        "ai_analysis",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cpse_materials.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "best_candidate_material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cpse_materials.id"), nullable=True
        ),
        sa.Column("final_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("description_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("specification_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("classification_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("uom_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("attribute_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("grade_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("dimension_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("standard_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("manufacturer_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("function_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("criticality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("recommended_common_code", sa.String(100), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="COMPLETED"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("ml_probability", sa.Float(), nullable=True),
        sa.Column("ml_status", sa.String(20), nullable=True),
        sa.Column("technical_conflict", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("conflict_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_analysis_material_id", "ai_analysis", ["material_id"])
    op.create_index("ix_ai_analysis_decision", "ai_analysis", ["decision"])

    op.create_table(
        "common_material_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "common_material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("common_materials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cpse_material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cpse_materials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "matched_against_material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cpse_materials.id"), nullable=True
        ),
        sa.Column("ai_analysis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_analysis.id"), nullable=True),
        sa.Column("mapping_type", sa.String(40), nullable=False),
        sa.Column("decision_status", sa.String(30), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("common_material_id", "cpse_material_id", name="uq_mapping_common_cpse_material"),
    )
    op.create_index("ix_common_material_mappings_common_material_id", "common_material_mappings", ["common_material_id"])
    op.create_index("ix_common_material_mappings_cpse_material_id", "common_material_mappings", ["cpse_material_id"])
    op.create_index("ix_common_material_mappings_mapping_type", "common_material_mappings", ["mapping_type"])
    op.create_index("ix_common_material_mappings_decision_status", "common_material_mappings", ["decision_status"])

    op.create_table(
        "approval_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "mapping_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("common_material_mappings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_approval_actions_mapping_id", "approval_actions", ["mapping_id"])

    op.create_table(
        "procurement_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cpse_material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cpse_materials.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("procurement_reference", sa.String(150), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("uom", sa.String(50), nullable=True),
        sa.Column("unit_price", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("vendor", sa.String(255), nullable=True),
        sa.Column("plant_location", sa.String(255), nullable=True),
        sa.Column("is_demo_data", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_procurement_history_cpse_material_id", "procurement_history", ["cpse_material_id"])
    op.create_index("ix_procurement_history_purchase_date", "procurement_history", ["purchase_date"])
    op.create_index("ix_procurement_history_is_demo_data", "procurement_history", ["is_demo_data"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_type", sa.String(20), nullable=False, server_default="USER"),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_name", sa.String(255), nullable=False, server_default="AI ENGINE"),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("before_state", postgresql.JSONB(), nullable=True),
        sa.Column("after_state", postgresql.JSONB(), nullable=True),
        sa.Column("reason", sa.String(1000), nullable=True),
        sa.Column("ai_model_version", sa.String(150), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
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
    op.drop_table("procurement_history")
    op.drop_table("approval_actions")
    op.drop_table("common_material_mappings")
    op.drop_table("ai_analysis")
    op.drop_table("material_matches")
    op.execute("DROP INDEX IF EXISTS ix_material_embeddings_text_vector")
    op.drop_table("material_embeddings")
    op.drop_table("material_attributes")
    op.drop_table("cpse_materials")
    op.drop_table("common_materials")
    op.drop_table("sync_history")
    op.drop_table("source_connections")
    op.drop_table("users")
    op.drop_table("cpses")
    op.drop_table("roles")
    op.execute("DROP SEQUENCE IF EXISTS common_material_code_seq")
