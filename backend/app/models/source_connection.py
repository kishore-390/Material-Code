import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin


class SourceConnection(Base, UUIDMixin, TimestampMixin):
    """
    Secure, read-only database connector configuration for one CPSE (spec
    section 2D-2I, 5.6). This table is the ENTIRE extensibility point for
    adding a new CPSE's data source: no application code changes needed,
    only a new row here plus a password living in an environment variable
    named by secret_reference - NEVER stored here, NEVER returned to any API
    response or the frontend.

    column_mapping documents, per CPSE, how that CPSE's own source table
    columns map onto CanonicalMaterialRecord fields (app.connectors.base) -
    since every CPSE's schema is unknown in advance, this mapping is what
    makes the connector architecture genuinely extensible without a code
    change per CPSE.
    """

    __tablename__ = "source_connections"

    cpse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cpses.id"), nullable=False, index=True
    )
    connection_name: Mapped[str] = mapped_column(String(150), nullable=False)
    database_type: Mapped[str] = mapped_column(String(20), nullable=False)  # POSTGRESQL|MYSQL|ORACLE|SQLSERVER

    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    database_name: Mapped[str] = mapped_column(String(150), nullable=False)

    # Name of an environment variable holding the read-only username/password -
    # never the credential itself. Resolved at call time by app.connectors.
    username_reference: Mapped[str] = mapped_column(String(150), nullable=False)
    secret_reference: Mapped[str] = mapped_column(String(150), nullable=False)

    ssl_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    read_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    table_name: Mapped[str] = mapped_column(String(150), nullable=False)
    column_mapping: Mapped[dict] = mapped_column(JSONB, nullable=False)
    cursor_column: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sync_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)

    last_sync_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_synced_cursor: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)

    # Marks a connector wired to app.demo_seed's demonstration source schema -
    # never a real CPSE connection (spec section 33).
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    cpse: Mapped["CPSE"] = relationship(back_populates="source_connections")
    sync_runs: Mapped[list["SyncHistory"]] = relationship(
        back_populates="source_connection", cascade="all, delete-orphan"
    )


class SyncHistory(Base, UUIDMixin, TimestampMixin):
    """One execution record of a synchronization run (spec section 5.7) -
    the audit trail behind every sync status the UI shows."""

    __tablename__ = "sync_history"

    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_connections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sync_type: Mapped[str] = mapped_column(String(20), nullable=False)  # FULL | INCREMENTAL
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING", index=True)

    records_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_successful_cursor: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    source_connection: Mapped["SourceConnection"] = relationship(back_populates="sync_runs")
