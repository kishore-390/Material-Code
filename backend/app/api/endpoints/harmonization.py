import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.approval import ApprovalRequest
from app.models.cpse import CPSEOrganization
from app.models.enums import ApprovalStatus, HarmonizationStatus, MaterialStatus, NotificationType, RoleName
from app.models.harmonization import CommonMaterialCode, HarmonizationRequest
from app.models.material import Material
from app.models.matching import AIAnalysis
from app.models.user import User
from app.schemas.harmonization import (
    HarmonizationActionRequest,
    HarmonizationRequestCreate,
    HarmonizationRequestOut,
    ScanStatusItem,
    ScanStatusRequest,
    ScanStatusResponse,
    ScanTriggerResponse,
)
from app.services.audit_service import log_action
from app.services.harmonization_service import approve_harmonization, reject_harmonization
from app.services.notification_service import notify_role

router = APIRouter(prefix="/harmonization", tags=["Harmonization"])


@router.post("/scan", response_model=ScanTriggerResponse)
def scan_material_masters(
    cpse_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value)),
):
    """
    "Scan Material Masters": queues the EXISTING per-material AI pipeline
    (embeddings -> pgvector candidate retrieval -> weighted scoring ->
    XGBoost blend -> decision engine -> conflict gate -> common-code
    generation, see app.ai.analyzer.analyze_material) for every material
    across every CPSE that has not yet been linked to a Common Material
    Code. No separate/duplicate AI logic - this is pure orchestration over
    the single-material pipeline the rest of the app already uses.
    """
    query = db.query(Material).filter(
        Material.common_code_id.is_(None),
        Material.status != MaterialStatus.PROCESSING.value,
    )
    if cpse_id:
        query = query.filter(Material.cpse_id == cpse_id)
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
        entity_type="material",
        entity_id=None,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        actor_type="USER",
        details={"materials_queued": len(material_ids), "cpse_id": str(cpse_id) if cpse_id else None},
    )

    return ScanTriggerResponse(queued=len(material_ids), material_ids=[m.id for m in materials], mode=mode)


FULL_DATABASE_SCAN_CPSES = ("IOCL", "ONGC")


@router.post("/full-database-scan", response_model=ScanTriggerResponse)
def full_database_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value)),
):
    """
    "AI Full Database Analysis" (prototype scope: IOCL + ONGC only).

    Deliberately NOT `WHERE common_code_id IS NULL` alone: a material
    already linked to an AUTO_GENERATED code (i.e. an AI recommendation
    that has never been human-approved) is re-included so a better
    candidate discovered later can still update it. A material linked to
    an APPROVED code is excluded here, and is separately, unconditionally
    guarded in analyzer._handle_decision so an approved mapping can never
    be silently reassigned even if it were re-included by mistake -
    two independent layers protecting the same invariant.

    Reuses the exact same per-material AI pipeline and Celery
    infrastructure as /scan (no separate/duplicate AI logic). Global
    cross-batch matching is guaranteed because each material's candidate
    retrieval (app.ai.similarity.find_candidate_materials) is a pgvector
    search over the ENTIRE materials table, not just materials queued in
    the same call - which batch a material happened to be queued in
    never limits which candidates it can be compared against.
    """
    approved_code_ids = db.query(CommonMaterialCode.id).filter(CommonMaterialCode.status == "APPROVED")
    query = (
        db.query(Material)
        .join(CPSEOrganization, Material.cpse_id == CPSEOrganization.id)
        .filter(CPSEOrganization.code.in_(FULL_DATABASE_SCAN_CPSES))
        .filter(Material.status != MaterialStatus.PROCESSING.value)
        .filter(or_(Material.common_code_id.is_(None), Material.common_code_id.notin_(approved_code_ids)))
    )
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
        action="FULL_DATABASE_SCAN_TRIGGERED",
        entity_type="material",
        entity_id=None,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        actor_type="USER",
        details={"materials_queued": len(material_ids), "scope": list(FULL_DATABASE_SCAN_CPSES)},
    )

    return ScanTriggerResponse(queued=len(material_ids), material_ids=[m.id for m in materials], mode=mode)


@router.post("/scan-status", response_model=ScanStatusResponse)
def scan_status(
    payload: ScanStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Real, DB-derived progress for a previously triggered scan - never a
    fabricated percentage. `completed` counts materials whose AI pipeline
    has reached a terminal state (ANALYZED / HARMONIZED / FAILED); anything
    still PENDING/PROCESSING is still in flight.
    """
    if not payload.material_ids:
        return ScanStatusResponse(total=0, completed=0, items=[])

    materials = db.query(Material).filter(Material.id.in_(payload.material_ids)).all()
    materials_by_id = {m.id: m for m in materials}

    analyses = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.material_id.in_(payload.material_ids))
        .order_by(AIAnalysis.material_id, AIAnalysis.created_at.desc())
        .all()
    )
    latest_by_material: dict[uuid.UUID, AIAnalysis] = {}
    for a in analyses:
        latest_by_material.setdefault(a.material_id, a)

    terminal_statuses = {MaterialStatus.ANALYZED.value, MaterialStatus.HARMONIZED.value, MaterialStatus.FAILED.value}
    items: list[ScanStatusItem] = []
    completed = 0
    for material_id in payload.material_ids:
        material = materials_by_id.get(material_id)
        if not material:
            continue
        analysis = latest_by_material.get(material_id)
        if material.status in terminal_statuses:
            completed += 1
        items.append(
            ScanStatusItem(
                material_id=material.id,
                material_code=material.material_code,
                cpse_code=material.cpse.code if material.cpse else "",
                description=material.description,
                category=material.category,
                material_status=material.status,
                latest_decision=analysis.decision if analysis else None,
                ai_confidence=analysis.final_score if analysis else None,
                technical_conflict=analysis.technical_conflict if analysis else False,
                conflict_reason=analysis.conflict_reason if analysis else None,
                best_candidate_material_code=(
                    analysis.best_candidate.material_code if analysis and analysis.best_candidate else None
                ),
                best_candidate_cpse_code=(
                    analysis.best_candidate.cpse.code if analysis and analysis.best_candidate and analysis.best_candidate.cpse else None
                ),
                common_code=material.common_code,
            )
        )

    return ScanStatusResponse(total=len(payload.material_ids), completed=completed, items=items)


@router.post("/request", response_model=HarmonizationRequestOut, status_code=201)
def create_harmonization_request(
    payload: HarmonizationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.CPSE_USER.value, RoleName.MATERIAL_EXPERT.value)),
):
    material = db.query(Material).filter(Material.id == payload.material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    candidate = None
    if payload.candidate_material_id:
        candidate = db.query(Material).filter(Material.id == payload.candidate_material_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate material not found")

    harmonization = HarmonizationRequest(
        material_id=material.id,
        candidate_material_id=candidate.id if candidate else None,
        requested_by=current_user.id,
        request_type="MANUAL",
        status=HarmonizationStatus.PENDING.value,
        notes=payload.notes,
    )
    db.add(harmonization)
    db.flush()

    approval = ApprovalRequest(
        harmonization_request_id=harmonization.id,
        material_id=material.id,
        candidate_material_id=candidate.id if candidate else None,
        ai_score=None,
        status=ApprovalStatus.PENDING.value,
        reason=payload.notes or "Manually submitted harmonization request.",
    )
    db.add(approval)
    db.commit()
    db.refresh(harmonization)

    log_action(
        db,
        action="HARMONIZATION_REQUESTED",
        entity_type="harmonization_request",
        entity_id=harmonization.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        actor_type="USER",
        details={"material_code": material.material_code},
    )
    notify_role(
        db,
        RoleName.MATERIAL_EXPERT.value,
        NotificationType.HUMAN_APPROVAL_REQUIRED.value,
        "Manual harmonization request submitted",
        f"{current_user.full_name} requested harmonization review for {material.material_code}.",
        "harmonization_request",
        harmonization.id,
    )

    return HarmonizationRequestOut(
        id=harmonization.id,
        material=harmonization.material,
        candidate=harmonization.candidate,
        request_type=harmonization.request_type,
        status=harmonization.status,
        ai_score=None,
        common_code=None,
        notes=harmonization.notes,
        created_at=harmonization.created_at,
        updated_at=harmonization.updated_at,
    )


@router.get("", response_model=list[HarmonizationRequestOut])
def list_harmonization_requests(
    status_filter: str | None = Query(None, alias="status"),
    cpse_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(HarmonizationRequest)
    if status_filter:
        query = query.filter(HarmonizationRequest.status == status_filter)
    if current_user.role.name == RoleName.CPSE_USER.value and current_user.cpse_id:
        query = query.join(Material, HarmonizationRequest.material_id == Material.id).filter(
            Material.cpse_id == current_user.cpse_id
        )
    elif cpse_id:
        query = query.join(Material, HarmonizationRequest.material_id == Material.id).filter(
            Material.cpse_id == cpse_id
        )
    items = query.order_by(HarmonizationRequest.created_at.desc()).all()

    results = []
    for h in items:
        approval = (
            db.query(ApprovalRequest)
            .filter(ApprovalRequest.harmonization_request_id == h.id)
            .order_by(ApprovalRequest.created_at.desc())
            .first()
        )
        results.append(
            HarmonizationRequestOut(
                id=h.id,
                material=h.material,
                candidate=h.candidate,
                request_type=h.request_type,
                status=h.status,
                ai_score=approval.ai_score if approval else None,
                common_code=h.common_code,
                notes=h.notes,
                created_at=h.created_at,
                updated_at=h.updated_at,
            )
        )
    return results


@router.get("/{harmonization_id}", response_model=HarmonizationRequestOut)
def get_harmonization_request(
    harmonization_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    h = db.query(HarmonizationRequest).filter(HarmonizationRequest.id == harmonization_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Harmonization request not found")
    approval = (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.harmonization_request_id == h.id)
        .order_by(ApprovalRequest.created_at.desc())
        .first()
    )
    return HarmonizationRequestOut(
        id=h.id,
        material=h.material,
        candidate=h.candidate,
        request_type=h.request_type,
        status=h.status,
        ai_score=approval.ai_score if approval else None,
        common_code=h.common_code,
        notes=h.notes,
        created_at=h.created_at,
        updated_at=h.updated_at,
    )


@router.post("/{harmonization_id}/approve", response_model=HarmonizationRequestOut)
def approve(
    harmonization_id: uuid.UUID,
    payload: HarmonizationActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value)),
):
    h = db.query(HarmonizationRequest).filter(HarmonizationRequest.id == harmonization_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Harmonization request not found")
    if h.status in (HarmonizationStatus.APPROVED.value, HarmonizationStatus.AUTO_APPROVED.value):
        raise HTTPException(status_code=400, detail="This request has already been approved")

    approve_harmonization(db, h, current_user, payload.remarks)
    db.refresh(h)
    return HarmonizationRequestOut(
        id=h.id, material=h.material, candidate=h.candidate, request_type=h.request_type,
        status=h.status, ai_score=None, common_code=h.common_code, notes=h.notes,
        created_at=h.created_at, updated_at=h.updated_at,
    )


@router.post("/{harmonization_id}/reject", response_model=HarmonizationRequestOut)
def reject(
    harmonization_id: uuid.UUID,
    payload: HarmonizationActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value)),
):
    h = db.query(HarmonizationRequest).filter(HarmonizationRequest.id == harmonization_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Harmonization request not found")

    reject_harmonization(db, h, current_user, payload.remarks)
    db.refresh(h)
    return HarmonizationRequestOut(
        id=h.id, material=h.material, candidate=h.candidate, request_type=h.request_type,
        status=h.status, ai_score=None, common_code=h.common_code, notes=h.notes,
        created_at=h.created_at, updated_at=h.updated_at,
    )
