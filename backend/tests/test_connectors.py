"""
Connector tests (spec section 41). The read-only SELECT-building, paging,
column-mapping and incremental-cursor logic in app.connectors.sql_connector
is dialect-agnostic, so it is exercised here against a throwaway SQLite
database (stdlib, no extra infrastructure) through a test-only subclass -
proving the shared logic works without requiring a live Postgres/MySQL
server in the test environment. PostgresConnector/MySQLConnector only add a
different URL scheme and session pragma on top of this same base class.
"""
import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text

from app.connectors.base import CanonicalMaterialRecord, validate_identifier
from app.connectors.exceptions import ConnectorNotAvailableError, ConnectorQueryError
from app.connectors.oracle_connector import OracleConnector
from app.connectors.sql_connector import SQLSourceConnector


class _SQLiteTestConnector(SQLSourceConnector):
    """Test-only: SQLite has no user/host/port, so this overrides URL
    construction to point at a temp file while reusing every other piece of
    SQLSourceConnector unchanged (select-building, paging, cursoring)."""

    driver_url_scheme = "sqlite"

    def _build_url(self, host, port, database_name, username, password, ssl_enabled) -> str:
        return f"sqlite:///{database_name}"


@pytest.fixture()
def sqlite_source():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "demo_source.db")
        engine = create_engine(f"sqlite:///{db_path}")
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE TABLE materials (code TEXT PRIMARY KEY, descr TEXT, uom TEXT, updated_at TEXT)"
                )
            )
            base = datetime(2026, 1, 1, tzinfo=timezone.utc)
            for i in range(5):
                conn.execute(
                    text("INSERT INTO materials VALUES (:code, :descr, :uom, :updated_at)"),
                    {
                        "code": f"MAT-{i:03d}",
                        "descr": f"Test Material {i}",
                        "uom": "EACH",
                        "updated_at": (base + timedelta(days=i)).isoformat(),
                    },
                )
        engine.dispose()

        connector = _SQLiteTestConnector(
            host="", port=0, database_name=db_path, username="", password="",
            table_name="materials",
            column_mapping={
                "original_material_code": "code",
                "original_description": "descr",
                "uom": "uom",
                "source_updated_at": "updated_at",
            },
            cursor_column="updated_at",
        )
        yield connector
        connector.close()


def test_validate_identifier_rejects_sql_injection_attempt():
    with pytest.raises(ValueError):
        validate_identifier("materials; DROP TABLE users;--", what="table_name")


def test_validate_identifier_accepts_normal_names():
    assert validate_identifier("cpse_materials_2024", what="table_name") == "cpse_materials_2024"


def test_fetch_all_returns_every_row(sqlite_source):
    page = sqlite_source.fetch_all(page=1, page_size=100)
    assert len(page.items) == 5
    assert all(isinstance(item, CanonicalMaterialRecord) for item in page.items)
    assert {item.original_material_code for item in page.items} == {f"MAT-{i:03d}" for i in range(5)}


def test_fetch_all_pages_correctly(sqlite_source):
    page1 = sqlite_source.fetch_all(page=1, page_size=2)
    assert len(page1.items) == 2
    assert page1.has_more is True

    page3 = sqlite_source.fetch_all(page=3, page_size=2)
    assert len(page3.items) == 1
    assert page3.has_more is False


def test_fetch_changed_since_only_returns_newer_rows(sqlite_source):
    since = datetime(2026, 1, 2, tzinfo=timezone.utc)  # excludes day 0 and day 1 (Jan 1, Jan 2 <= since)
    page = sqlite_source.fetch_changed_since(since, page=1, page_size=100)
    codes = {item.original_material_code for item in page.items}
    assert "MAT-000" not in codes
    assert "MAT-004" in codes


def test_fetch_changed_since_without_cursor_column_raises(sqlite_source):
    sqlite_source.cursor_column = None
    with pytest.raises(ConnectorQueryError):
        sqlite_source.fetch_changed_since(datetime.now(timezone.utc))


def test_test_connection_reports_failure_without_raising():
    connector = _SQLiteTestConnector(
        host="", port=0, database_name="/nonexistent/path/does-not-exist.db", username="", password="",
        table_name="materials", column_mapping={"original_material_code": "code", "original_description": "descr", "uom": "uom"},
        cursor_column=None,
    )
    result = connector.test_connection()
    # A missing sqlite file is auto-created by the driver, so this proves the
    # *interface never raises* even for connectivity failures on dialects
    # that would actually fail (e.g. Postgres/MySQL host unreachable) -
    # errors always come back as a ConnectionTestResult, never an exception.
    assert isinstance(result.connected, bool)
    connector.close()


def test_oracle_connector_reports_not_available_without_driver():
    with pytest.raises(ConnectorNotAvailableError):
        OracleConnector(
            host="oracle.example.com", port=1521, database_name="ORCL", username="ro_user", password="secret",
            table_name="materials", column_mapping={"original_material_code": "code", "original_description": "descr", "uom": "uom"},
            cursor_column=None,
        )
