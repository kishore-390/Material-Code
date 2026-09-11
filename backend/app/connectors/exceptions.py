"""
Exceptions raised by app.connectors.* - typed by failure category so
app.connectors.sync_engine can record an accurate last_sync_status/
last_error and the API layer can react appropriately (spec section 30).
"""


class ConnectorError(Exception):
    """Base class for every source-connector failure."""


class ConnectorConnectionError(ConnectorError):
    """Network failure, DNS failure, connection refused, or a timeout reaching the source database."""


class ConnectorAuthError(ConnectorError):
    """The source database rejected the read-only credentials."""


class ConnectorQueryError(ConnectorError):
    """The configured table/column mapping does not match the source schema, or the query otherwise failed."""


class ConnectorNotAvailableError(ConnectorError):
    """
    This connector's optional vendor driver (e.g. oracledb, pyodbc) is not
    installed. Raised lazily, only when the connector is actually used -
    never at import time - so the presence of an Oracle/SQL Server
    SourceConnection row never breaks the app for CPSEs using Postgres/MySQL.
    """
