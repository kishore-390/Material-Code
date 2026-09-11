"""
Maps a SourceConnection's database_type to the connector implementation
that speaks it, and resolves its read-only credentials strictly from
environment variables (spec section 2D-2F). Adding a CPSE that uses an
already-supported database type needs NO code change here - only a new
source_connections row.
"""
import os

from app.connectors.base import SourceConnector
from app.connectors.mssql_connector import MSSQLConnector
from app.connectors.mysql_connector import MySQLConnector
from app.connectors.oracle_connector import OracleConnector
from app.connectors.postgres_connector import PostgresConnector
from app.models.source_connection import SourceConnection

_CONNECTOR_CLASSES: dict[str, type[SourceConnector]] = {
    "POSTGRESQL": PostgresConnector,
    "MYSQL": MySQLConnector,
    "ORACLE": OracleConnector,
    "SQLSERVER": MSSQLConnector,
}


def resolve_username(source_connection: SourceConnection) -> str:
    value = os.environ.get(source_connection.username_reference)
    if not value:
        raise ValueError(
            f"Environment variable '{source_connection.username_reference}' is not set - "
            "cannot resolve the read-only username for this source connection."
        )
    return value


def resolve_secret(source_connection: SourceConnection) -> str:
    value = os.environ.get(source_connection.secret_reference)
    if not value:
        raise ValueError(
            f"Environment variable '{source_connection.secret_reference}' is not set - "
            "cannot resolve the read-only password for this source connection."
        )
    return value


def build_connector(source_connection: SourceConnection) -> SourceConnector:
    connector_cls = _CONNECTOR_CLASSES.get(source_connection.database_type)
    if connector_cls is None:
        raise ValueError(f"Unsupported database_type '{source_connection.database_type}'")

    return connector_cls(
        host=source_connection.host,
        port=source_connection.port,
        database_name=source_connection.database_name,
        username=resolve_username(source_connection),
        password=resolve_secret(source_connection),
        table_name=source_connection.table_name,
        column_mapping=source_connection.column_mapping,
        cursor_column=source_connection.cursor_column,
        ssl_enabled=source_connection.ssl_enabled,
    )
