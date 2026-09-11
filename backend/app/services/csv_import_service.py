"""
DEMO-ONLY CSV import (SIH26099 demonstration mechanism).

This is NOT a production ingestion path. Production CPSE material data only
ever arrives through app.connectors.sync_engine (secure read-only database
connectors, spec section 2A-2D). This module exists purely so a live
demonstration can populate the National Material Master with realistic rows
without a real CPSE database to connect to - every row it creates is marked
CPSEMaterial.is_demo_data = True and is fed through the EXACT SAME canonical
ingestion pipeline a real sync uses:

    CSV row -> CanonicalMaterialRecord -> app.services.material_ingestion
    (the same upsert core app.connectors.sync_engine uses) -> Celery
    ai_analysis -> app.connectors.sync_engine.trigger_batch_settlement

There is no separate CSV-specific AI pipeline, scoring, decision engine, or
common-code generator anywhere in this file - all of that continues to live
exclusively in app.ai / app.services.decision_engine / code_generator,
unchanged.

Security note: CSV column NAMES are never used to build SQL - csv.DictReader
maps them generically and every field this module reads is addressed by a
fixed, hardcoded key (see REQUIRED_COLUMNS), never interpolated into a
query. The only database write path is app.services.material_ingestion,
which uses the SQLAlchemy ORM exclusively.
"""
import csv
import io
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.connectors.base import CanonicalMaterialRecord
from app.models.cpse import CPSE
from app.models.enums import Criticality
from app.services import material_ingestion
from app.services.audit_service import log_action

REQUIRED_COLUMNS = (
    "cpse_code",
    "original_material_code",
    "original_description",
    "material_type",
    "material_grade",
    "dimensions",
    "technical_specification",
    "uom",
    "manufacturer",
    "standard",
    "function",
    "classification",
    "packaging",
    "criticality",
    "quantity",
)
_REQUIRED_NON_EMPTY = ("cpse_code", "original_material_code", "original_description", "material_type", "uom")
_VALID_CRITICALITY = {c.value for c in Criticality}

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB - a demo CSV, not a bulk data feed
MAX_ROWS = 5000
PREVIEW_ROWS = 20


@dataclass
class RowResult:
    row_number: int
    raw: dict[str, str]
    errors: list[str] = field(default_factory=list)
    cpse_id: uuid.UUID | None = None
    record: CanonicalMaterialRecord | None = None

    @property
    def is_valid(self) -> bool:
        return not self.errors


@dataclass
class CsvValidationResult:
    filename: str
    total_rows: int
    rows: list[RowResult]
    file_errors: list[str]

    @property
    def valid_rows(self) -> list[RowResult]:
        return [r for r in self.rows if r.is_valid]

    @property
    def invalid_rows(self) -> list[RowResult]:
        return [r for r in self.rows if not r.is_valid]

    @property
    def is_importable(self) -> bool:
        return not self.file_errors and len(self.valid_rows) > 0


class CsvImportError(Exception):
    """Raised for file-level problems (bad encoding, missing columns, too
    large, too many rows) that make the file impossible to parse at all -
    distinct from per-row validation errors, which never raise."""


def _decode(raw_bytes: bytes) -> str:
    try:
        return raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvImportError("File is not valid UTF-8 text. Please export the CSV as UTF-8.") from exc


def _parse_criticality(value: str) -> tuple[str | None, str | None]:
    value = (value or "").strip()
    if not value:
        return None, None
    upper = value.upper()
    if upper not in _VALID_CRITICALITY:
        return None, f"Invalid criticality '{value}' - must be one of {sorted(_VALID_CRITICALITY)}"
    return upper, None


def _parse_quantity(value: str) -> tuple[float | None, str | None]:
    value = (value or "").strip()
    if not value:
        return None, None
    try:
        return float(value), None
    except ValueError:
        return None, f"Invalid quantity '{value}' - must be numeric"


def build_sample_csv() -> str:
    """
    A ready-to-import demo CSV covering the same 6 required decision
    categories as tests/test_harmonization_cases.py (spec section 42):
    IDENTICAL/DUPLICATE-equivalent wording, an equivalent pair, a
    dimension-based TECHNICAL_CONFLICT, unrelated NOT_EQUIVALENT materials,
    a grade-based TECHNICAL_CONFLICT, and a packaging difference that must
    NOT be treated as a conflict. Uses IOCL/ONGC - the CPSE codes
    app.demo_seed already creates - so it only works after the demo seed (or
    any onboarding of those two CPSE codes) has run, consistent with "the
    CSV import can only target existing CPSEs."

    Deliberately uses item types (grease nipples, hose clamps, flange
    couplings, safety helmets, generators, pipe elbows, O-rings) that do NOT
    overlap with app.demo_seed's own fixture descriptions (bolts, valves,
    bearings, pumps, cable) - app.demo_seed's rows are real, already-embedded
    CPSEMaterial candidates in the very database this CSV imports into, so
    reusing its wording would make these rows match THOSE instead of each
    other and silently defeat the demonstration.
    """
    rows = [
        # Pair 1: IDENTICAL - same item, different wording/units
        dict(cpse_code="IOCL", original_material_code="IOCL-CSV-01", original_description="Grease Nipple Straight 1/4 BSP",
             material_type="Lubrication Fitting", material_grade="", dimensions="1/4 BSP", technical_specification="Straight hydraulic grease nipple",
             uom="PC", manufacturer="LubeTech", standard="DIN 71412", function="Lubrication", classification="Lubrication Fitting",
             packaging="Loose", criticality="NORMAL", quantity="2000"),
        dict(cpse_code="ONGC", original_material_code="ONGC-CSV-01", original_description="Straight Grease Nipple 1/4 inch BSP Thread",
             material_type="Lubrication Fitting", material_grade="", dimensions="1/4 BSP", technical_specification="Straight hydraulic grease nipple",
             uom="PC", manufacturer="LubeTech", standard="DIN 71412", function="Lubrication", classification="Lubrication Fitting",
             packaging="Loose", criticality="NORMAL", quantity="1500"),
        # Pair 2: equivalent hose clamps
        dict(cpse_code="IOCL", original_material_code="IOCL-CSV-02", original_description="Hydraulic Hose Clamp 25mm",
             material_type="Hydraulic Fitting", material_grade="", dimensions="25mm", technical_specification="",
             uom="EACH", manufacturer="HydroFit", standard="", function="Hose Retention", classification="Hydraulic Fitting",
             packaging="", criticality="NORMAL", quantity="600"),
        dict(cpse_code="ONGC", original_material_code="ONGC-CSV-02", original_description="Hose Clamp 25 mm Hydraulic",
             material_type="Hydraulic Fitting", material_grade="", dimensions="25mm", technical_specification="",
             uom="EACH", manufacturer="HydroFit", standard="", function="Hose Retention", classification="Hydraulic Fitting",
             packaging="", criticality="NORMAL", quantity="350"),
        # Pair 3: TECHNICAL_CONFLICT - conflicting nominal flange sizes
        dict(cpse_code="IOCL", original_material_code="IOCL-CSV-03", original_description="Flange Coupling 4 inch",
             material_type="Pipe Fitting", material_grade="", dimensions="4 inch", technical_specification="",
             uom="EACH", manufacturer="FlangeWorks", standard="ANSI B16.5", function="Pipe Joining", classification="Pipe Fitting",
             packaging="", criticality="CRITICAL", quantity="80"),
        dict(cpse_code="ONGC", original_material_code="ONGC-CSV-03", original_description="Flange Coupling 6 inch",
             material_type="Pipe Fitting", material_grade="", dimensions="6 inch", technical_specification="",
             uom="EACH", manufacturer="FlangeWorks", standard="ANSI B16.5", function="Pipe Joining", classification="Pipe Fitting",
             packaging="", criticality="CRITICAL", quantity="55"),
        # Pair 4: NOT_EQUIVALENT - unrelated materials
        dict(cpse_code="IOCL", original_material_code="IOCL-CSV-04", original_description="PPE Safety Helmet Yellow",
             material_type="Safety Equipment", material_grade="", dimensions="", technical_specification="",
             uom="EACH", manufacturer="SafeGuard", standard="IS 2925", function="Head Protection", classification="Safety Equipment",
             packaging="", criticality="NORMAL", quantity="500"),
        dict(cpse_code="ONGC", original_material_code="ONGC-CSV-04", original_description="Diesel Generator 25kVA",
             material_type="Power Equipment", material_grade="", dimensions="", technical_specification="25kVA diesel genset",
             uom="EACH", manufacturer="PowerGen", standard="", function="Backup Power", classification="Power Equipment",
             packaging="", criticality="NORMAL", quantity="4"),
        # Pair 5: TECHNICAL_CONFLICT - conflicting material grade
        dict(cpse_code="IOCL", original_material_code="IOCL-CSV-05", original_description="Carbon Steel Pipe Elbow 90 Degree CS-A106",
             material_type="Pipe Fitting", material_grade="A106", dimensions="90 degree", technical_specification="",
             uom="PC", manufacturer="", standard="", function="", classification="Pipe Elbow",
             packaging="", criticality="NORMAL", quantity="300"),
        dict(cpse_code="ONGC", original_material_code="ONGC-CSV-05", original_description="Carbon Steel Pipe Elbow 90 Degree CS-A335",
             material_type="Pipe Fitting", material_grade="A335", dimensions="90 degree", technical_specification="",
             uom="PC", manufacturer="", standard="", function="", classification="Pipe Elbow",
             packaging="", criticality="NORMAL", quantity="180"),
        # Pair 6: packaging difference must NOT be a conflict
        dict(cpse_code="IOCL", original_material_code="IOCL-CSV-06", original_description="O-Ring Seal 50mm NBR",
             material_type="Seal", material_grade="NBR", dimensions="50mm", technical_specification="",
             uom="PC", manufacturer="", standard="", function="", classification="Seal",
             packaging="Loose, Pack of 1", criticality="NORMAL", quantity="150"),
        dict(cpse_code="ONGC", original_material_code="ONGC-CSV-06", original_description="O-Ring Seal 50mm NBR",
             material_type="Seal", material_grade="NBR", dimensions="50mm", technical_specification="",
             uom="BOX", manufacturer="", standard="", function="", classification="Seal",
             packaging="Box of 50", criticality="NORMAL", quantity="3"),
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=REQUIRED_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def validate_csv(db: Session, *, filename: str, raw_bytes: bytes) -> CsvValidationResult:
    """
    Full structural + data + cross-reference validation, with NOTHING
    inserted into the database - this is the "show errors/preview before
    import" step. Returns every row's outcome so the frontend can render
    valid/invalid counts and a preview without a second round trip.
    """
    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise CsvImportError(f"File exceeds the {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB demo import limit.")
    if not raw_bytes.strip():
        raise CsvImportError("File is empty.")

    text = _decode(raw_bytes)
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = [f.strip() for f in (reader.fieldnames or [])]
    missing = [c for c in REQUIRED_COLUMNS if c not in fieldnames]
    if missing:
        raise CsvImportError(f"CSV is missing required column(s): {', '.join(missing)}")

    cpse_by_code = {c.code.upper(): c for c in db.query(CPSE).all()}

    rows: list[RowResult] = []
    seen_keys: dict[tuple[str, str], list[int]] = {}

    for line_number, raw_row in enumerate(reader, start=2):
        if line_number - 1 > MAX_ROWS:
            raise CsvImportError(f"CSV has more than {MAX_ROWS} data rows - split it into smaller demo files.")

        data = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw_row.items() if k in REQUIRED_COLUMNS}
        result = RowResult(row_number=line_number, raw=data)

        for col in _REQUIRED_NON_EMPTY:
            if not data.get(col):
                result.errors.append(f"'{col}' is required")

        cpse_code = (data.get("cpse_code") or "").upper()
        cpse = cpse_by_code.get(cpse_code)
        if data.get("cpse_code") and cpse is None:
            result.errors.append(
                f"Unknown CPSE code '{data['cpse_code']}' - the demo CSV import can only target CPSEs already "
                "onboarded under Participating CPSEs, never create new ones."
            )

        criticality, crit_err = _parse_criticality(data.get("criticality", ""))
        if crit_err:
            result.errors.append(crit_err)
        quantity, qty_err = _parse_quantity(data.get("quantity", ""))
        if qty_err:
            result.errors.append(qty_err)

        material_code = data.get("original_material_code", "")
        if cpse is not None and material_code:
            key = (cpse_code, material_code)
            seen_keys.setdefault(key, []).append(line_number)

            existing = material_ingestion.find_existing(db, cpse_id=cpse.id, original_material_code=material_code)
            if existing is not None and not existing.is_demo_data:
                result.errors.append(
                    f"Material code '{material_code}' at {cpse_code} already exists as real production data "
                    "synced from a database connector - the demo CSV import cannot overwrite it."
                )

        if cpse is not None and not result.errors:
            result.cpse_id = cpse.id
            result.record = CanonicalMaterialRecord(
                original_material_code=material_code,
                original_description=data.get("original_description", ""),
                uom=data.get("uom", ""),
                material_type=data.get("material_type") or None,
                material_grade=data.get("material_grade") or None,
                dimensions=data.get("dimensions") or None,
                technical_specification=data.get("technical_specification") or None,
                manufacturer=data.get("manufacturer") or None,
                standard=data.get("standard") or None,
                function=data.get("function") or None,
                classification=data.get("classification") or None,
                packaging=data.get("packaging") or None,
                criticality=criticality,
                quantity=quantity,
                is_active=True,
            )

        rows.append(result)

    for key, line_numbers in seen_keys.items():
        if len(line_numbers) > 1:
            for row in rows:
                if row.record is not None and (row.raw.get("cpse_code", "").upper(), row.raw.get("original_material_code", "")) == key:
                    row.errors.append(f"Duplicate original_material_code within this CSV (also on row(s) {[n for n in line_numbers if n != row.row_number]})")
                    row.record = None
                    row.cpse_id = None

    return CsvValidationResult(filename=filename, total_rows=len(rows), rows=rows, file_errors=[])


@dataclass
class ImportRowOutcome:
    row_number: int
    cpse_code: str
    original_material_code: str
    outcome: str
    common_material_code: str | None = None
    mapping_type: str | None = None
    decision_status: str | None = None


@dataclass
class ImportSummary:
    batch_id: uuid.UUID
    filename: str
    total_rows: int
    valid_count: int
    invalid_count: int
    created: int
    updated: int
    skipped: int
    failed: int
    results: list[ImportRowOutcome]


def import_valid_rows(
    db: Session,
    validation: CsvValidationResult,
    *,
    actor_id: uuid.UUID | None,
    actor_name: str,
) -> ImportSummary:
    """
    Feeds every valid row through app.services.material_ingestion (the same
    upsert core app.connectors.sync_engine uses), then hands the whole batch
    to app.connectors.sync_engine.trigger_batch_settlement - the identical
    real completion-tracked settlement mechanism a live database sync uses,
    never a fixed delay or a demo-only shortcut. `wait=True` is used (as
    app.demo_seed already does for its own demo syncs) so this call's
    response can immediately report each row's final governance outcome for
    the frontend's result page, instead of leaving the caller to poll.
    """
    from app.connectors.sync_engine import trigger_batch_settlement
    from app.models.harmonization import CommonMaterialMapping
    from app.models.enums import MappingDecisionStatus

    batch_id = uuid.uuid4()
    counts = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
    to_analyze: list[uuid.UUID] = []
    results: list[ImportRowOutcome] = []
    outcome_by_material_id: dict[uuid.UUID, ImportRowOutcome] = {}

    for row in validation.valid_rows:
        assert row.record is not None and row.cpse_id is not None
        try:
            outcome, material = material_ingestion.upsert_cpse_material(
                db,
                cpse_id=row.cpse_id,
                record=row.record,
                actor_name=actor_name,
                actor_type="USER",
                is_demo_data=True,
                created_action="MATERIAL_CSV_IMPORTED_CREATED",
                updated_action="MATERIAL_CSV_IMPORTED_UPDATED",
                log_details_extra={"import_batch_id": str(batch_id), "source": "DEMO_CSV_IMPORT", "filename": validation.filename},
            )
        except Exception as exc:  # noqa: BLE001 - one bad row must not fail the whole import
            db.rollback()
            outcome, material = "failed", None
            row.errors.append(str(exc))
        counts[outcome] += 1
        row_outcome = ImportRowOutcome(
            row_number=row.row_number,
            cpse_code=row.raw.get("cpse_code", ""),
            original_material_code=row.raw.get("original_material_code", ""),
            outcome=outcome,
        )
        results.append(row_outcome)
        if material is not None:
            to_analyze.append(material.id)
            outcome_by_material_id[material.id] = row_outcome

    trigger_batch_settlement(db, to_analyze, wait=True)

    for material_id in to_analyze:
        mapping = (
            db.query(CommonMaterialMapping)
            .filter(
                CommonMaterialMapping.cpse_material_id == material_id,
                CommonMaterialMapping.decision_status != MappingDecisionStatus.REJECTED.value,
            )
            .order_by(CommonMaterialMapping.created_at.desc())
            .first()
        )
        if mapping is not None:
            row_outcome = outcome_by_material_id[material_id]
            row_outcome.mapping_type = mapping.mapping_type
            row_outcome.decision_status = mapping.decision_status
            row_outcome.common_material_code = mapping.common_material.common_code

    invalid_count = len(validation.invalid_rows)
    log_action(
        db,
        action="CSV_DEMO_IMPORT_COMPLETED",
        entity_type="csv_import_batch",
        entity_id=batch_id,
        actor_id=actor_id,
        actor_name=actor_name,
        actor_type="USER",
        details={
            "filename": validation.filename,
            "total_rows": validation.total_rows,
            "valid_count": len(validation.valid_rows),
            "invalid_count": invalid_count,
            **counts,
        },
    )

    return ImportSummary(
        batch_id=batch_id,
        filename=validation.filename,
        total_rows=validation.total_rows,
        valid_count=len(validation.valid_rows),
        invalid_count=invalid_count,
        created=counts["created"],
        updated=counts["updated"],
        skipped=counts["skipped"],
        failed=counts["failed"],
        results=results,
    )
