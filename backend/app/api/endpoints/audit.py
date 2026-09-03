from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.enums import RoleName
from app.models.user import User
from app.schemas.audit import AuditLogListResponse, AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["Audit Log"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    entity_type: str | None = None,
    action: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.VIEWER.value, RoleName.MATERIAL_EXPERT.value)),
):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if action:
        query = query.filter(AuditLog.action == action)

    total = query.count()
    items = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AuditLogListResponse(items=items, total=total, page=page, page_size=page_size)
