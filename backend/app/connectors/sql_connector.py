"""
Shared implementation for every SQLAlchemy-reachable relational connector
(Postgres, MySQL today; the same base would serve any future dialect with a
pure-Python driver). Only the engine URL scheme and the dialect-specific
read-only session pragma differ per database type - the query building,
paging, and row mapping are identical, which is exactly the point of the
connector architecture (spec section 26): the AI pipeline and sync engine
never see any of this.
"""
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.connectors.base import (
    CanonicalRecordPage,
    ConnectionTestResult,
    SourceConnector,
    row_to_canonical,
    validate_identifier,
)
from app.connectors.exceptions import ConnectorConnectionError, ConnectorQueryError

logger = logging.getLogger(__name__)


class SQLSourceConnector(SourceConnector):
    driver_url_scheme: str = ""  # set by subclass, e.g. "postgresql+psycopg"

    def __init__(
        self,
        *,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        table_name: str,
        column_mapping: dict[str, str],
        cursor_column: str | None,
        ssl_enabled: bool = True,
    ):
        self.table_name = validate_identifier(table_name, what="table_name")
        self.column_mapping = {
            field: validate_identifier(col, what=f"column_mapping[{field}]")
            for field, col in column_mapping.items()
        }
        self.cursor_column = validate_identifier(cursor_column, what="cursor_column") if cursor_column else None

        url = self._build_url(host, port, database_name, username, password, ssl_enabled)
        self.engine: Engine = create_engine(url, pool_pre_ping=True, pool_size=1, max_overflow=0)

    def _build_url(self, host: str, port: int, database_name: str, username: str, password: str, ssl_enabled: bool) -> str:
        from urllib.parse import quote_plus

        return f"{self.driver_url_scheme}://{quote_plus(username)}:{quote_plus(password)}@{host}:{port}/{database_name}"

    def _apply_read_only_session(self, conn) -> None:
        """Dialect-specific best-effort session-level read-only enforcement,
        on top of the read-only DB account itself - defense in depth, not a
        substitute for granting the account SELECT-only privileges."""

    def _select_columns_sql(self) -> str:
        return ", ".join(f"{col} AS {field}" for field, col in self.column_mapping.items())

    def test_connection(self) -> ConnectionTestResult:
        started = time.monotonic()
        try:
            with self.engine.connect() as conn:
                self._apply_read_only_session(conn)
                version = conn.execute(text("SELECT 1")).scalar()
            latency_ms = round((time.monotonic() - started) * 1000, 1)
            return ConnectionTestResult(connected=True, database_version=str(version), latency_ms=latency_ms)
        except Exception as exc:  # noqa: BLE001 - a failed connection test is a normal, expected outcome
            latency_ms = round((time.monotonic() - started) * 1000, 1)
            return ConnectionTestResult(connected=False, latency_ms=latency_ms, error=str(exc))

    def _fetch(self, *, where_sql: str | None, params: dict, page: int, page_size: int) -> CanonicalRecordPage:
        offset = max(0, (page - 1) * page_size)
        sql = f"SELECT {self._select_columns_sql()} FROM {self.table_name}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        order_by = self.cursor_column or next(iter(self.column_mapping.values()))
        sql += f" ORDER BY {order_by} LIMIT :limit OFFSET :offset"
        params = {**params, "offset": offset, "limit": page_size}

        try:
            with self.engine.connect() as conn:
                self._apply_read_only_session(conn)
                rows = conn.execute(text(sql), params).mappings().all()
        except Exception as exc:  # noqa: BLE001
            raise ConnectorQueryError(f"Query against {self.table_name} failed: {exc}") from exc

        items = [row_to_canonical(dict(row), self.column_mapping) for row in rows]
        return CanonicalRecordPage(items=items, has_more=len(items) == page_size)

    def fetch_all(self, *, page: int = 1, page_size: int = 500) -> CanonicalRecordPage:
        return self._fetch(where_sql=None, params={}, page=page, page_size=page_size)

    def fetch_changed_since(self, since: datetime, *, page: int = 1, page_size: int = 500) -> CanonicalRecordPage:
        if not self.cursor_column:
            raise ConnectorQueryError(
                f"{self.table_name} has no cursor_column configured - incremental sync is unavailable "
                "for this source connection; only full sync can be run."
            )
        since = since.astimezone(timezone.utc) if since.tzinfo else since
        return self._fetch(
            # Bound as an explicit ISO string rather than a raw datetime object
            # so every dialect's driver compares it the same way, rather than
            # depending on each DBAPI's own (sometimes deprecated/inconsistent)
            # implicit datetime adaptation.
            where_sql=f"{self.cursor_column} > :since",
            params={"since": since.isoformat()},
            page=page,
            page_size=page_size,
        )

    def close(self) -> None:
        self.engine.dispose()
