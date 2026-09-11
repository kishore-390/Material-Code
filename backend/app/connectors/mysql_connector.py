"""MySQL/MariaDB read-only source connector. Uses PyMySQL, a pure-Python
driver with no system-level client library requirement, so it installs
cleanly in any environment."""
from sqlalchemy import text

from app.connectors.sql_connector import SQLSourceConnector


class MySQLConnector(SQLSourceConnector):
    driver_url_scheme = "mysql+pymysql"

    def _build_url(self, host, port, database_name, username, password, ssl_enabled) -> str:
        url = super()._build_url(host, port, database_name, username, password, ssl_enabled)
        return f"{url}?ssl_verify_cert=true" if ssl_enabled else url

    def _apply_read_only_session(self, conn) -> None:
        conn.execute(text("SET SESSION TRANSACTION READ ONLY"))
