"""
The one shape every source database connector must produce, and the
abstract interface app.connectors.sync_engine drives - it never knows or
cares whether a CPSE's data came from Postgres, MySQL, Oracle or SQL
Server (spec section 26).
"""
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# Required canonical fields every column_mapping MUST supply a source column
# for. Everything else in CanonicalMaterialRecord is optional - a CPSE's
# source schema is free to simply not track e.g. packaging or criticality.
REQUIRED_CANONICAL_FIELDS = ("original_material_code", "original_description", "uom")

# Every field a SourceConnection.column_mapping entry is allowed to name.
CANONICAL_FIELDS = REQUIRED_CANONICAL_FIELDS + (
    "material_type",
    "material_grade",
    "dimensions",
    "technical_specification",
    "manufacturer",
    "standard",
    "function",
    "classification",
    "packaging",
    "criticality",
    "quantity",
    "is_active",
    "source_created_at",
    "source_updated_at",
)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_identifier(name: str, *, what: str) -> str:
    """
    Table/column names can never be passed as bound SQL parameters - they
    have to be interpolated into the query text. This allowlist check is
    what makes that safe: a SourceConnection's table_name/column_mapping is
    ADMIN-configured, not end-user input, but this still closes the SQL
    injection surface outright (spec section 31) rather than trusting
    configuration to always be benign.
    """
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid {what} '{name}': must match {_IDENTIFIER_RE.pattern}")
    return name


class CanonicalMaterialRecord(BaseModel):
    """The normalized shape produced by every connector, before normalization/AI ever runs."""

    model_config = ConfigDict(extra="ignore")

    original_material_code: str = Field(min_length=1)
    original_description: str = Field(min_length=1)
    uom: str
    material_type: Optional[str] = None
    material_grade: Optional[str] = None
    dimensions: Optional[str] = None
    technical_specification: Optional[str] = None
    manufacturer: Optional[str] = None
    standard: Optional[str] = None
    function: Optional[str] = None
    classification: Optional[str] = None
    packaging: Optional[str] = None
    criticality: Optional[str] = None
    quantity: Optional[float] = None
    is_active: bool = True
    source_created_at: Optional[datetime] = None
    source_updated_at: Optional[datetime] = None


class CanonicalRecordPage(BaseModel):
    items: list[CanonicalMaterialRecord]
    has_more: bool = False
    total: Optional[int] = None


class ConnectionTestResult(BaseModel):
    connected: bool
    database_version: Optional[str] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None


def row_to_canonical(row: dict[str, Any], column_mapping: dict[str, str]) -> CanonicalMaterialRecord:
    """Shared row -> CanonicalMaterialRecord mapping used by every SQL-based
    connector, so the mapping logic itself never has to be reimplemented per
    database dialect. The query that produced `row` already aliases each
    source column to its canonical field name (`SELECT source_col AS
    canonical_field`, see SQLSourceConnector._select_columns_sql), so `row`
    is keyed by canonical field names already - this just filters out
    anything not in the recognized canonical field set before validation."""
    values = {field: row[field] for field in column_mapping if field in CANONICAL_FIELDS and field in row}
    return CanonicalMaterialRecord.model_validate(values)


class SourceConnector(ABC):
    """
    Read-only source database connector interface (spec section 26). Every
    concrete implementation only ever issues SELECT statements - there is no
    write/insert/update/delete method on this interface at all, which is
    what makes "never modifies the source CPSE database" true by
    construction rather than by convention.
    """

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """A fast, side-effect-free connectivity check - used by "Test Connection" in the UI."""

    @abstractmethod
    def fetch_all(self, *, page: int = 1, page_size: int = 500) -> CanonicalRecordPage:
        """One page of the full source table (for a full sync)."""

    @abstractmethod
    def fetch_changed_since(self, since: datetime, *, page: int = 1, page_size: int = 500) -> CanonicalRecordPage:
        """One page of rows whose cursor column is newer than `since` (for an incremental sync)."""

    @abstractmethod
    def close(self) -> None:
        """Releases the underlying connection/engine."""

    def __enter__(self) -> "SourceConnector":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
