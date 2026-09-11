"""
SQL Server read-only source connector - interface-complete, activation-pending.

SQL Server requires the `pyodbc` driver plus a platform ODBC driver
(msodbcsql), which is a system-level install this sandbox cannot guarantee.
As with Oracle, the interface is fully implemented against the same
SourceConnector contract; only the driver import is deferred so an
Oracle/SQL-Server SourceConnection row never breaks the app for CPSEs
using Postgres/MySQL.

To activate: install the Microsoft ODBC Driver for SQL Server plus
`pip install pyodbc`, and set database_type=SQLSERVER on the
SourceConnection - no other code change is required.
"""
from app.connectors.exceptions import ConnectorNotAvailableError
from app.connectors.sql_connector import SQLSourceConnector


class MSSQLConnector(SQLSourceConnector):
    driver_url_scheme = "mssql+pyodbc"

    def __init__(self, *args, **kwargs):
        try:
            import pyodbc  # noqa: F401
        except ImportError as exc:
            raise ConnectorNotAvailableError(
                "The SQL Server connector requires the 'pyodbc' package and the Microsoft ODBC "
                "Driver for SQL Server. Install both to activate this connector."
            ) from exc
        super().__init__(*args, **kwargs)

    def _build_url(self, host, port, database_name, username, password, ssl_enabled) -> str:
        url = super()._build_url(host, port, database_name, username, password, ssl_enabled)
        return f"{url}?driver=ODBC+Driver+17+for+SQL+Server"
