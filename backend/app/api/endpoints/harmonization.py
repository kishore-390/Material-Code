import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import MappingDecisionStatus, MappingType, MaterialStatus, RoleName
from app.models.harmonization import CommonMaterialMapping
from app.models.material import CPSEMaterial
from app.models.user import User
from app.schemas.duplicate import DuplicateListResponse, DuplicatePairDetailOut, DuplicatePairOut
from app.schemas.harmonization import CommonMaterialOut
from app.schemas.material import CPSEMaterialOut
from app.services import duplicate_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/harmonization", tags=["Harmonization"])

# Nav sections (spec section 17): AI Recommendations, Duplicate Materials,
# Near Duplicates, Functional Equivalence, Technical Conflicts - each a thin
# filtered view over the SAME app.services.duplicate_service data (spec
# section 37 single source of truth), never a separate detection mechanism.
_VIEW_MAPPING_TYPES: dict[str, tuple[str, ...] | None] = {
    "recommendations": None,
    "duplicates": (MappingType.IDENTICAL.value, MappingType.DUPLICATE.value),
    "near-duplicates": (MappingType.NEAR_DUPLICATE.value,),
    "functional-equivalence": (MappingType.FUNCTIONALLY_EQUIVALENT.value,),
}


def _list_view(db: Session, current_user: User, mapping_types, q, cpse_id, page, page_size, decision_status=None):
    pairs = duplicate_service.list_duplicate_pairs(db, mapping_types=mapping_types)
    if decision_status:
        pairs = [p for p in pairs if p.decision_status == decision_status]

    total_duplicates = len(pairs)
    pending_validation = sum(1 for p in pairs if p.decision_status == "PENDING_VALIDATION")
    approved = sum(1 for p in pairs if p.decision_status in ("APPROVED", "EDITED_AND_APPROVED"))
    common_materials_generated = len({p.common_material.id for p in pairs})

    if q:
        needle = q.strip().lower()
        pairs = [
            p
            for p in pairs
            if needle in p.source.original_material_code.lower()
            or needle in p.source.original_description.lower()
            or needle in p.matched.original_material_code.lower()
            or needle in p.matched.original_description.lower()
        ]
    if cpse_id:
        pairs = [p for p in pairs if p.source.cpse_id == cpse_id or p.matched.cpse_id == cpse_id]

    total_filtered = len(pairs)
    start = (page - 1) * page_size
    page_items = pairs[start : start + page_size]

    items = [
        DuplicatePairOut(
            mapping_id=p.mapping_id,
            common_material=CommonMaterialOut.model_validate(p.common_material),
            source_material=CPSEMaterialOut.model_validate(p.source),
            matched_material=CPSEMaterialOut.model_validate(p.matched),
            mapping_type=p.mapping_type,
            decision_status=p.decision_status,
            confidence_score=p.confidence_score,
        )
        for p in page_items
    ]
    return DuplicateListResponse(
        items=items,
        total=total_filtered,
        page=page,
        page_size=page_size,
        total_duplicates=total_duplicates,
        pending_validation=pending_validation,
        approved=approved,
        common_materials_generated=common_materials_generated,
    )


@router.get("/recommendations", response_model=DuplicateListResponse)
def list_recommendations(
    q: str | None = None, cpse_id: uuid.UUID | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    return _list_view(db, current_user, _VIEW_MAPPING_TYPES["recommendations"], q, cpse_id, page, page_size)


@router.get("/duplicates", response_model=DuplicateListResponse)
def list_duplicates(
    q: str | None = None, cpse_id: uuid.UUID | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    return _list_view(db, current_user, _VIEW_MAPPING_TYPES["duplicates"], q, cpse_id, page, page_size)


@router.get("/near-duplicates", response_model=DuplicateListResponse)
def list_near_duplicates(
    q: str | None = None, cpse_id: uuid.UUID | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    return _list_view(db, current_user, _VIEW_MAPPING_TYPES["near-duplicates"], q, cpse_id, page, page_size)


@router.get("/functional-equivalence", response_model=DuplicateListResponse)
def list_functional_equivalence(
    q: str | None = None, cpse_id: uuid.UUID | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    return _list_view(db, current_user, _VIEW_MAPPING_TYPES["functional-equivalence"], q, cpse_id, page, page_size)


@router.get("/technical-conflicts", response_model=DuplicateListResponse)
def list_technical_conflicts(
    q: str | None = None, cpse_id: uuid.UUID | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    return _list_view(db, current_user, None, q, cpse_id, page, page_size, decision_status="TECHNICAL_CONFLICT")


@router.get("/pairs/{mapping_id}", response_model=DuplicatePairDetailOut)
def get_pair(mapping_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pair = duplicate_service.get_duplicate_pair_by_mapping_id(db, mapping_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return DuplicatePairDetailOut(
        mapping_id=pair.mapping_id,
        common_material=CommonMaterialOut.model_validate(pair.common_material),
        source_material=CPSEMaterialOut.model_validate(pair.source),
        matched_material=CPSEMaterialOut.model_validate(pair.matched),
        mapping_type=pair.mapping_type,
        decision_status=pair.decision_status,
        confidence_score=pair.confidence_score,
        breakdown=pair.breakdown,
        sbert_similarity=pair.sbert_similarity,
        ml_probability=pair.ml_probability,
        ml_status=pair.ml_status,
    )


@router.post("/scan")
def scan_material_masters(
    cpse_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value)),
):
    """
    Re-runs the EXISTING per-material AI pipeline (spec section 28) for
    every material that does not yet have a human-APPROVED mapping. No
    separate/duplicate AI logic - this is pure orchestration over the
    single-material pipeline (app.ai.analyzer.analyze_material) the rest of
    the app already uses for every newly-synced material.

    Deliberately NOT "no mapping at all": a material already linked to an
    AI_RECOMMENDED/PENDING_VALIDATION/MANUAL_REVIEW/TECHNICAL_CONFLICT
    mapping is re-included so a better candidate discovered later (e.g.
    another CPSE's matching material that synced afterward) can still
    settle it into the right group. A material with an APPROVED or
    EDITED_AND_APPROVED mapping is excluded here, and is separately,
    unconditionally guarded in analyzer._handle_decision so an approved
    mapping can never be silently reassigned even if it were re-included by
    mistake - two independent layers protecting the same invariant.
    """
    approved_statuses = (MappingDecisionStatus.APPROVED.value, MappingDecisionStatus.EDITED_AND_APPROVED.value)
    query = db.query(CPSEMaterial).filter(
        ~CPSEMaterial.mappings.any(CommonMaterialMapping.decision_status.in_(approved_statuses)),
        CPSEMaterial.status != MaterialStatus.PROCESSING.value,
    )
    if cpse_id:
        query = query.filter(CPSEMaterial.cpse_id == cpse_id)
    materials = query.all()
    material_ids = [str(m.id) for m in materials]

    mode = "QUEUED"
    if material_ids:
        try:
            from app.workers.tasks import bulk_ai_analysis

            bulk_ai_analysis.delay(material_ids)
        except Exception:  # noqa: BLE001 - no broker reachable (isolated test/dev setup)
            from app.ai.analyzer import analyze_material

            for mid in material_ids:
                analyze_material(db, uuid.UUID(mid))
            mode = "PROCESSED_INLINE"

    log_action(
        db,
        action="HARMONIZATION_SCAN_TRIGGERED",
        entity_type="cpse_material",
        entity_id=None,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        actor_type="USER",
        details={"materials_queued": len(material_ids), "cpse_id": str(cpse_id) if cpse_id else None},
    )
    return {"queued": len(material_ids), "material_ids": [m.id for m in materials], "mode": mode}


@router.post("/scan-status")
def scan_status(
    material_ids: list[uuid.UUID] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Real, DB-derived progress for a previously triggered scan - never a
    fabricated percentage."""
    if not material_ids:
        return {"total": 0, "completed": 0}

    terminal_statuses = {MaterialStatus.ANALYZED.value, MaterialStatus.HARMONIZED.value, MaterialStatus.FAILED.value}
    materials = db.query(CPSEMaterial.status).filter(CPSEMaterial.id.in_(material_ids)).all()
    completed = sum(1 for (s,) in materials if s in terminal_statuses)
    return {"total": len(material_ids), "completed": completed}
