"""
Shared CPSEMaterial upsert core (spec section 29 idempotency).

Used identically by BOTH real ingestion paths - the production source
connector sync engine (app.connectors.sync_engine) and the demo-only CSV
import (app.services.csv_import_service) - so the two paths can never
diverge in their idempotency/governance behavior. The only differences
between callers are provenance fields (source_connection_id/sync_history_id
for a real sync vs is_demo_data for a CSV import) and audit log action
names - never the upsert logic itself.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.connectors.base import CanonicalMaterialRecord
from app.models.enums import MappingDecisionStatus, MaterialStatus
from app.models.material import CPSEMaterial
from app.services import attribute_extraction, normalization
from app.services.audit_service import log_action

TRACKED_FIELDS = (
    "original_description", "material_type", "technical_specification", "uom", "manufacturer",
    "standard", "function", "classification", "packaging", "criticality", "quantity", "is_active",
)


def apply_extracted_and_normalized_fields(material: CPSEMaterial, record: CanonicalMaterialRecord) -> None:
    extracted = attribute_extraction.extract_missing_attributes(
        description=record.original_description,
        specification=record.technical_specification,
        material_grade=record.material_grade,
        dimensions=record.dimensions,
        standard=record.standard,
    )
    material.material_grade = record.material_grade or extracted.get("material_grade")
    material.dimensions = record.dimensions or extracted.get("dimensions")
    material.standard = record.standard or extracted.get("standard")

    material.normalized_description = normalization.normalize_description(record.original_description)
    material.normalized_specification = normalization.normalize_specification(record.technical_specification)
    material.normalized_classification = normalization.normalize_classification(record.classification or record.material_type)
    material.normalized_uom = normalization.normalize_uom(record.uom)


def _incoming_fields(record: CanonicalMaterialRecord) -> dict:
    return {
        "original_description": record.original_description,
        "material_type": record.material_type,
        "technical_specification": record.technical_specification,
        "uom": record.uom,
        "manufacturer": record.manufacturer,
        "standard": record.standard,
        "function": record.function,
        "classification": record.classification or record.material_type,
        "packaging": record.packaging,
        "criticality": record.criticality or "UNSPECIFIED",
        "quantity": record.quantity,
        "is_active": record.is_active,
    }


def find_existing(db: Session, *, cpse_id: uuid.UUID, original_material_code: str) -> CPSEMaterial | None:
    return (
        db.query(CPSEMaterial)
        .filter(
            CPSEMaterial.original_material_code == original_material_code,
            CPSEMaterial.cpse_id == cpse_id,
        )
        .first()
    )


def upsert_cpse_material(
    db: Session,
    *,
    cpse_id: uuid.UUID,
    record: CanonicalMaterialRecord,
    actor_name: str,
    actor_type: str = "SYSTEM",
    source_connection_id: uuid.UUID | None = None,
    sync_history_id: uuid.UUID | None = None,
    is_demo_data: bool = False,
    created_action: str = "MATERIAL_SYNCED_CREATED",
    updated_action: str = "MATERIAL_SYNCED_UPDATED",
    log_details_extra: dict | None = None,
) -> tuple[str, CPSEMaterial | None]:
    """
    Idempotent upsert keyed on (cpse_id, original_material_code) - spec
    section 29. Returns (outcome, material_to_reanalyze) where outcome is
    one of created/updated/skipped/failed and material_to_reanalyze is None
    whenever the AI pipeline should NOT be re-triggered (nothing changed, or
    the material's mapping is already human-APPROVED and must be protected
    from any accidental status/mapping side effect of a rescan).
    """
    now = datetime.now(timezone.utc)
    details_extra = log_details_extra or {}
    existing = find_existing(db, cpse_id=cpse_id, original_material_code=record.original_material_code)

    if existing is None:
        material = CPSEMaterial(
            cpse_id=cpse_id,
            original_material_code=record.original_material_code,
            original_description=record.original_description,
            material_type=record.material_type,
            technical_specification=record.technical_specification,
            uom=record.uom,
            manufacturer=record.manufacturer,
            standard=record.standard,
            function=record.function,
            classification=record.classification or record.material_type,
            packaging=record.packaging,
            criticality=record.criticality or "UNSPECIFIED",
            quantity=record.quantity,
            is_active=record.is_active,
            status=MaterialStatus.PENDING.value,
            source_created_at=record.source_created_at,
            source_updated_at=record.source_updated_at,
            last_synced_at=now,
            source_connection_id=source_connection_id,
            sync_history_id=sync_history_id,
            is_demo_data=is_demo_data,
        )
        apply_extracted_and_normalized_fields(material, record)
        db.add(material)
        db.flush()
        db.commit()
        log_action(
            db,
            action=created_action,
            entity_type="cpse_material",
            entity_id=material.id,
            actor_name=actor_name,
            actor_type=actor_type,
            details={"material_code": record.original_material_code, **details_extra},
        )
        return "created", material

    incoming = _incoming_fields(record)
    changed = any(getattr(existing, f) != incoming[f] for f in TRACKED_FIELDS)

    if not changed:
        existing.last_synced_at = now
        if sync_history_id is not None:
            existing.sync_history_id = sync_history_id
        db.commit()
        return "skipped", None

    for f in TRACKED_FIELDS:
        setattr(existing, f, incoming[f])
    existing.source_updated_at = record.source_updated_at or existing.source_updated_at
    existing.last_synced_at = now
    if source_connection_id is not None:
        existing.source_connection_id = source_connection_id
    if sync_history_id is not None:
        existing.sync_history_id = sync_history_id
    apply_extracted_and_normalized_fields(existing, record)

    has_approved_mapping = any(
        m.decision_status in (MappingDecisionStatus.APPROVED.value, MappingDecisionStatus.EDITED_AND_APPROVED.value)
        for m in existing.mappings
    )
    if has_approved_mapping:
        # Governance rule (spec section 10): a human-APPROVED mapping must
        # never be silently reassigned. Update the material's own content
        # (above) but do NOT re-run the AI pipeline on it - flag it visibly
        # for manual re-evaluation instead.
        db.commit()
        log_action(
            db,
            action="MATERIAL_CHANGED_AFTER_APPROVAL",
            entity_type="cpse_material",
            entity_id=existing.id,
            actor_name=actor_name,
            actor_type=actor_type,
            reason="Source content changed after this material's mapping was approved - approved mapping preserved; a Material Expert should review whether it still holds.",
            details={"material_code": record.original_material_code, **details_extra},
        )
        return "updated", None

    existing.status = MaterialStatus.PENDING.value
    db.commit()
    log_action(
        db,
        action=updated_action,
        entity_type="cpse_material",
        entity_id=existing.id,
        actor_name=actor_name,
        actor_type=actor_type,
        details={"material_code": record.original_material_code, **details_extra},
    )
    return "updated", existing
