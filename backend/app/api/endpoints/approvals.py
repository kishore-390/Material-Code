import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.approval import ApprovalAction, ApprovalRequest
from app.models.enums import (
    ApprovalActionType,
    ApprovalStatus,
    HarmonizationStatus,
    NotificationType,
    RoleName,
)
from app.models.harmonization import HarmonizationRequest
from app.models.material import Material
from app.models.user import User
from app.schemas.approval import ApprovalActionRequest, ApprovalDetailOut, ApprovalRequestOut, FieldComparison
from app.services.harmonization_service import approve_harmonization, reject_harmonization
from app.services.notification_service import notify_user
from app.services.scoring import text_ratio

router = APIRouter(prefix="/approvals", tags=["Approvals"])


def _compare_field(name: str, a: str | None, b: str | None) -> FieldComparison:
    a, b = (a or "").strip(), (b or "").strip()
    if not a and not b:
        match = "SAME"
    elif a.upper() == b.upper():
        match = "SAME"
    elif text_ratio(a.upper(), b.upper()) >= 70:
        match = "SIMILAR"
    else:
        match = "DIFFERENT"
    return FieldComparison(field=name, original_value=a or None, candidate_value=b or None, match=match)


def _build_comparison(material: Material, candidate: Material | None) -> list[FieldComparison]:
    if candidate is None:
        return []
    return [
        _compare_field("Description", material.description, candidate.description),
        _compare_field("Specification", material.specification, candidate.specification),
        _compare_field("Category", material.category, candidate.category),
        _compare_field("UOM", material.uom, candidate.uom),
        _compare_field("Manufacturer", material.manufacturer, candidate.manufacturer),
        _compare_field("Brand", material.brand, candidate.brand),
        _compare_field(
            "Image",
            "Provided" if material.image_url else "Not provided",
            "Provided" if candidate.image_url else "Not provided",
        ),
    ]


def _to_detail(approval: ApprovalRequest) -> ApprovalDetailOut:
    out = ApprovalDetailOut.model_validate(approval)
    out.comparison = _build_comparison(approval.material, approval.candidate)
    return out


@router.get("", response_model=list[ApprovalRequestOut])
def list_approvals(
    status_filter: str | None = Query(None, alias="status"),
    cpse_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value, RoleName.VIEWER.value)),
):
    query = db.query(ApprovalRequest)
    if status_filter:
        query = query.filter(ApprovalRequest.status == status_filter)
    else:
        query = query.filter(ApprovalRequest.status == ApprovalStatus.PENDING.value)
    if cpse_id:
        query = query.join(Material, ApprovalRequest.material_id == Material.id).filter(
            Material.cpse_id == cpse_id
        )
    return query.order_by(ApprovalRequest.created_at.desc()).all()


@router.get("/{approval_id}", response_model=ApprovalDetailOut)
def get_approval(
    approval_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value, RoleName.VIEWER.value)),
):
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return _to_detail(approval)


@router.post("/{approval_id}/action", response_model=ApprovalDetailOut)
def take_action(
    approval_id: uuid.UUID,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value)),
):
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.status not in (ApprovalStatus.PENDING.value, ApprovalStatus.MORE_INFO_REQUESTED.value):
        raise HTTPException(status_code=400, detail="This approval request has already been resolved")

    harmonization = (
        db.query(HarmonizationRequest)
        .filter(HarmonizationRequest.id == approval.harmonization_request_id)
        .first()
    )
    action = payload.action.upper()
    valid_actions = {a.value for a in ApprovalActionType}
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of {sorted(valid_actions)}")

    if action == ApprovalActionType.APPROVE.value:
        approve_harmonization(db, harmonization, current_user, payload.remarks)
        approval.status = ApprovalStatus.APPROVED.value
    elif action == ApprovalActionType.MERGE.value:
        approve_harmonization(db, harmonization, current_user, payload.remarks)
        approval.status = ApprovalStatus.MERGED.value
    elif action == ApprovalActionType.REJECT.value:
        reject_harmonization(db, harmonization, current_user, payload.remarks)
        approval.status = ApprovalStatus.REJECTED.value
    elif action == ApprovalActionType.NOT_SAME_MATERIAL.value:
        reject_harmonization(db, harmonization, current_user, payload.remarks)
        approval.status = ApprovalStatus.NOT_SAME_MATERIAL.value
    elif action == ApprovalActionType.REQUEST_MORE_INFO.value:
        approval.status = ApprovalStatus.MORE_INFO_REQUESTED.value
        harmonization.status = HarmonizationStatus.MORE_INFO_REQUESTED.value
        db.commit()
        target = harmonization.requested_by or harmonization.material.created_by
        if target:
            notify_user(
                db,
                target,
                NotificationType.HUMAN_APPROVAL_REQUIRED.value,
                "More information requested",
                f"Material expert requested more information about "
                f"{harmonization.material.material_code}: {payload.remarks or 'See approval center for details.'}",
                "approval_request",
                approval.id,
            )

    db.add(
        ApprovalAction(
            approval_request_id=approval.id,
            action=action,
            actor_id=current_user.id,
            remarks=payload.remarks,
        )
    )
    db.commit()
    db.refresh(approval)
    return _to_detail(approval)
