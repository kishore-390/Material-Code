"""PostgreSQL read-only source connector. Uses psycopg (already a
dependency for the central database itself), so no additional driver is
required to activate this connector."""
from sqlalchemy import text

from app.connectors.sql_connector import SQLSourceConnector


class PostgresConnector(SQLSourceConnector):
    driver_url_scheme = "postgresql+psycopg"

    def _build_url(self, host, port, database_name, username, password, ssl_enabled) -> str:
        url = super()._build_url(host, port, database_name, username, password, ssl_enabled)
        return f"{url}?sslmode=require" if ssl_enabled else url

    def _apply_read_only_session(self, conn) -> None:
        # Session-level enforcement in addition to the read-only DB account -
        # any accidental write in this connector would fail at the database
        # itself, not just be absent from the code (spec section G/H).
        conn.execute(text("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY"))
