"""
Oracle read-only source connector - interface-complete, activation-pending.

Oracle requires the `oracledb` driver (pure-Python "thin" mode is
available, no Instant Client needed for most setups) which is not part of
this project's default dependency set to keep the base install lightweight
and dependency-friction-free. The connector architecture is proven
extensible by this class existing and implementing the full SourceConnector
interface identically to Postgres/MySQL; only the driver import is deferred.

To activate: `pip install oracledb` and set database_type=ORACLE on the
SourceConnection - no other code change is required.
"""
from app.connectors.exceptions import ConnectorNotAvailableError
from app.connectors.sql_connector import SQLSourceConnector


class OracleConnector(SQLSourceConnector):
    driver_url_scheme = "oracle+oracledb"

    def __init__(self, *args, **kwargs):
        try:
            import oracledb  # noqa: F401
        except ImportError as exc:
            raise ConnectorNotAvailableError(
                "The Oracle connector requires the 'oracledb' package. Install it with "
                "`pip install oracledb` to activate this connector."
            ) from exc
        super().__init__(*args, **kwargs)
