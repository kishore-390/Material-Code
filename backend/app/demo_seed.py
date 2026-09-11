"""
Demonstration data for SIH presentation purposes ONLY (spec section 33).

Run with:  docker compose exec backend python -m app.demo_seed

This is deliberately SEPARATE from app.seed. It does three things, in order:

1. Creates a handful of demo CPSEs and, for each, a plainly-named
   `demo_source_<cpse_code>` table holding realistic-looking sample material
   rows - standing in for "the CPSE's own external database". In a real
   deployment this table would live in a genuinely separate database on the
   CPSE's own infrastructure; for this demo it lives in the same Postgres
   instance so the demo needs no extra infrastructure to provision, while
   still being read through the REAL PostgresConnector and REAL sync engine
   - never a fixture shortcut that bypasses the actual ingestion pipeline.
2. Registers a SourceConnection per demo CPSE (is_demo=True) and runs a real
   full sync against it, so cpse_materials/embeddings/AI analysis/mappings
   are all populated by the actual pipeline, not hand-inserted.
3. Adds a few procurement_history rows (is_demo_data=True) for the resulting
   materials, so the Collaborative Procurement analytics has something real
   to aggregate.

The central database has ZERO CPSEs/materials/common materials/mappings
until this script (or a real connector sync) is run - see app.seed.
"""
import logging
import os
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text

from app.core.config import settings
from app.db.base import Base  # noqa: F401
from app.db.session import SessionLocal, engine
from app.models.cpse import CPSE
from app.models.material import CPSEMaterial
from app.models.procurement import ProcurementHistory
from app.models.source_connection import SourceConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demo_seed")

# Demo-only: reuses the central database's own admin credentials (already
# guaranteed present in .env for the stack to run at all) rather than
# inventing new env vars for a table that lives in the same instance. A real
# CPSE connection MUST use a dedicated read-only account (spec section G) -
# is_demo=True on these rows makes that shortcut impossible to mistake for
# a real one.
_USERNAME_REF = "POSTGRES_USER"
_SECRET_REF = "POSTGRES_PASSWORD"

DEMO_CPSES = [
    {"code": "IOCL", "name": "Indian Oil Corporation Limited", "sector": "Oil & Gas"},
    {"code": "ONGC", "name": "Oil and Natural Gas Corporation", "sector": "Oil & Gas"},
    {"code": "BPCL", "name": "Bharat Petroleum Corporation Limited", "sector": "Oil & Gas"},
]

_NOW = datetime.now(timezone.utc)

# Deliberately overlapping/near-duplicate rows across CPSEs (mirrors spec
# section 42's own worked examples) so a real sync + real AI pipeline run
# produces real IDENTICAL/DUPLICATE/TECHNICAL_CONFLICT/NOT_EQUIVALENT
# outcomes to demonstrate - never hand-inserted mapping results.
DEMO_ROWS = {
    "IOCL": [
        dict(material_code="IOCL001", description="SS Hex Bolt M10x50", category="Fastener", grade="SS304",
             dimensions="M10x50", specification="ASTM F593", uom="PC", manufacturer="Steelfast", standard="ASTM F593",
             function="Fastening", packaging="Loose", criticality="NORMAL", quantity=5000),
        dict(material_code="IOCL002", description="Gate Valve 2 inch", category="Valve", grade=None,
             dimensions="2 inch", specification="Cast Steel Gate Valve", uom="EACH", manufacturer="ValveCorp",
             standard="API 600", function="Flow Isolation", packaging=None, criticality="CRITICAL", quantity=120),
        dict(material_code="IOCL003", description="Deep Groove Ball Bearing 6205", category="Bearing", grade=None,
             dimensions="6205", specification="Deep Groove Ball Bearing", uom="EACH", manufacturer="SKF",
             standard="ISO 15", function="Rotational Support", packaging=None, criticality="NORMAL", quantity=800),
    ],
    "ONGC": [
        dict(material_code="ONGC001", description="Stainless Steel Bolt 10mm x 50mm", category="Fastener", grade="SS304",
             dimensions="10mm x 50mm", specification="ASTM F593", uom="PC", manufacturer="Steelfast", standard="ASTM F593",
             function="Fastening", packaging="Loose", criticality="NORMAL", quantity=3200),
        dict(material_code="ONGC002", description="Gate Valve 3 inch", category="Valve", grade=None,
             dimensions="3 inch", specification="Cast Steel Gate Valve", uom="EACH", manufacturer="ValveCorp",
             standard="API 600", function="Flow Isolation", packaging=None, criticality="CRITICAL", quantity=95),
        dict(material_code="ONGC003", description="Ball Bearing 6205", category="Bearing", grade=None,
             dimensions="6205", specification="Ball Bearing", uom="EACH", manufacturer="SKF",
             standard="ISO 15", function="Rotational Support", packaging=None, criticality="NORMAL", quantity=450),
        dict(material_code="ONGC004", description="Industrial Pump Centrifugal 5HP", category="Pump", grade=None,
             dimensions=None, specification="Centrifugal Pump", uom="EACH", manufacturer="PumpWorks",
             standard=None, function="Fluid Transfer", packaging=None, criticality="NORMAL", quantity=30),
    ],
    "BPCL": [
        dict(material_code="BPCL001", description="Hex Head SS304 Bolt 10mm x 50mm", category="Fastener", grade="SS316",
             dimensions="M10x50", specification="ASTM F593", uom="BOX", manufacturer="Steelfast", standard="ASTM F593",
             function="Fastening", packaging="Box of 100", criticality="NORMAL", quantity=40),
        dict(material_code="BPCL002", description="Electrical Cable 3 Core 25 sq mm", category="Cable", grade=None,
             dimensions="25 sq mm", specification="3 Core PVC Insulated", uom="METER", manufacturer="CableCo",
             standard="IS 694", function="Power Transmission", packaging=None, criticality="NORMAL", quantity=15000),
    ],
}


def _demo_table_name(cpse_code: str) -> str:
    return f"demo_source_{cpse_code.lower()}"


def _create_demo_source_table_and_data(db) -> None:
    for cpse_code, rows in DEMO_ROWS.items():
        table = _demo_table_name(cpse_code)
        db.execute(text(f"DROP TABLE IF EXISTS {table}"))
        db.execute(
            text(
                f"""
                CREATE TABLE {table} (
                    material_code VARCHAR(100) PRIMARY KEY,
                    description TEXT NOT NULL,
                    category VARCHAR(150),
                    grade VARCHAR(100),
                    dimensions VARCHAR(255),
                    specification TEXT,
                    uom VARCHAR(50) NOT NULL,
                    manufacturer VARCHAR(255),
                    standard VARCHAR(150),
                    function VARCHAR(255),
                    packaging VARCHAR(150),
                    criticality VARCHAR(30),
                    quantity FLOAT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    updated_at TIMESTAMPTZ DEFAULT now()
                )
                """
            )
        )
        for row in rows:
            db.execute(
                text(
                    f"""
                    INSERT INTO {table}
                        (material_code, description, category, grade, dimensions, specification, uom,
                         manufacturer, standard, function, packaging, criticality, quantity, is_active, updated_at)
                    VALUES
                        (:material_code, :description, :category, :grade, :dimensions, :specification, :uom,
                         :manufacturer, :standard, :function, :packaging, :criticality, :quantity, TRUE, :updated_at)
                    """
                ),
                {**row, "updated_at": _NOW - timedelta(days=1)},
            )
        logger.info("Created demo source table %s with %d rows", table, len(rows))
    db.commit()


_COLUMN_MAPPING = {
    "original_material_code": "material_code",
    "original_description": "description",
    "classification": "category",
    "material_type": "category",
    "material_grade": "grade",
    "dimensions": "dimensions",
    "technical_specification": "specification",
    "uom": "uom",
    "manufacturer": "manufacturer",
    "standard": "standard",
    "function": "function",
    "packaging": "packaging",
    "criticality": "criticality",
    "quantity": "quantity",
    "is_active": "is_active",
    "source_updated_at": "updated_at",
}


def _resolve_host_port_db() -> tuple[str, int, str]:
    host = os.environ.get("POSTGRES_HOST", "postgres")
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    database_name = os.environ.get("POSTGRES_DB", "material_harmonization")
    return host, port, database_name


def _create_cpses_and_connections(db) -> dict[str, CPSE]:
    host, port, database_name = _resolve_host_port_db()
    cpses: dict[str, CPSE] = {}
    for spec in DEMO_CPSES:
        cpse = db.query(CPSE).filter(CPSE.code == spec["code"]).first()
        if not cpse:
            cpse = CPSE(code=spec["code"], name=spec["name"], sector=spec["sector"])
            db.add(cpse)
            db.flush()
        cpses[spec["code"]] = cpse

        table = _demo_table_name(spec["code"])
        existing = db.query(SourceConnection).filter(SourceConnection.table_name == table).first()
        if not existing:
            db.add(
                SourceConnection(
                    cpse_id=cpse.id,
                    connection_name=f"{spec['code']} Demo Source (PostgreSQL)",
                    database_type="POSTGRESQL",
                    host=host,
                    port=port,
                    database_name=database_name,
                    username_reference=_USERNAME_REF,
                    secret_reference=_SECRET_REF,
                    ssl_enabled=False,
                    table_name=table,
                    column_mapping=_COLUMN_MAPPING,
                    cursor_column="updated_at",
                    sync_interval_seconds=300,
                    enabled=True,
                    is_demo=True,
                )
            )
    db.commit()
    return cpses


def _run_demo_syncs(db) -> None:
    """
    Runs each demo CPSE's sync through the exact same connector + sync
    engine + automatic-settlement path a real deployment uses (spec section
    26-28) - nothing here is a shortcut around that pipeline. `wait_for_
    settlement=True` blocks until each connection's own post-sync
    harmonization pass has genuinely finished (real completion tracking,
    not a fixed delay - see app.connectors.sync_engine) before moving to the
    next CPSE, so materials from a CPSE synced later in this loop always
    find an already-embedded, already-settled candidate from a CPSE synced
    earlier - deterministic convergence across CPSEs without depending on
    inter-batch timing. A real deployment does not need this: independent,
    naturally-spaced CPSE sync schedules already give each batch's own
    settling pass time to finish before the next CPSE's sync begins.
    """
    from app.connectors import sync_engine

    connections = db.query(SourceConnection).filter(SourceConnection.is_demo.is_(True)).all()
    for connection in connections:
        batch = sync_engine.run_full_sync(db, connection, wait_for_settlement=True)
        logger.info("Synced %s: %s (discovered=%d inserted=%d)", connection.connection_name, batch.status, batch.records_discovered, batch.records_inserted)


def _add_demo_procurement(db) -> None:
    materials = db.query(CPSEMaterial).join(SourceConnection, CPSEMaterial.source_connection_id == SourceConnection.id).filter(
        SourceConnection.is_demo.is_(True)
    ).all()
    for i, material in enumerate(materials):
        if db.query(ProcurementHistory).filter(ProcurementHistory.cpse_material_id == material.id).first():
            continue
        db.add(
            ProcurementHistory(
                cpse_material_id=material.id,
                procurement_reference=f"DEMO-PO-{i + 1:04d}",
                purchase_date=date.today() - timedelta(days=30 * (i % 6 + 1)),
                quantity=material.quantity or 100.0,
                uom=material.uom,
                unit_price=None,
                vendor=material.manufacturer,
                plant_location=f"{material.cpse.code} Plant",
                is_demo_data=True,
            )
        )
    db.commit()
    logger.info("Added demo procurement history for %d materials", len(materials))


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not os.environ.get(_USERNAME_REF) or not os.environ.get(_SECRET_REF):
            raise RuntimeError(
                f"{_USERNAME_REF}/{_SECRET_REF} must be set in the environment (they already should be, "
                "for the central database itself) before running the demo seed."
            )
        _create_demo_source_table_and_data(db)
        _create_cpses_and_connections(db)
        _run_demo_syncs(db)
        _add_demo_procurement(db)
        logger.info("Demo seed complete. This data is clearly marked is_demo=True / is_demo_data=True throughout.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
