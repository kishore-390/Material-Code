import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.approval import ApprovalRequest
from app.models.enums import ApprovalStatus, HarmonizationStatus, NotificationType, RoleName
from app.models.harmonization import HarmonizationRequest
from app.models.material import Material
from app.models.user import User
from app.schemas.harmonization import (
    HarmonizationActionRequest,
    HarmonizationRequestCreate,
    HarmonizationRequestOut,
)
from app.services.audit_service import log_action
from app.services.harmonization_service import approve_harmonization, reject_harmonization
from app.services.notification_service import notify_role

router = APIRouter(prefix="/harmonization", tags=["Harmonization"])


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
