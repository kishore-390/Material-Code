import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import RoleName
from app.models.upload_batch import UploadBatch
from app.models.user import User
from app.schemas.upload import UploadBatchListResponse, UploadBatchOut

router = APIRouter(prefix="/uploads", tags=["Upload History"])


@router.get("", response_model=UploadBatchListResponse)
def list_uploads(
    cpse_id: uuid.UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(UploadBatch)

    if current_user.role.name == RoleName.CPSE_USER.value and current_user.cpse_id:
        query = query.filter(UploadBatch.cpse_id == current_user.cpse_id)
    elif cpse_id:
        query = query.filter(UploadBatch.cpse_id == cpse_id)

    if status_filter:
        query = query.filter(UploadBatch.status == status_filter)

    total = query.count()
    items = (
        query.order_by(UploadBatch.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return UploadBatchListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{upload_id}", response_model=UploadBatchOut)
def get_upload(
    upload_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    batch = db.query(UploadBatch).filter(UploadBatch.id == upload_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Upload batch not found")
    if (
        current_user.role.name == RoleName.CPSE_USER.value
        and current_user.cpse_id
        and batch.cpse_id != current_user.cpse_id
    ):
        raise HTTPException(status_code=403, detail="You may only view your own CPSE's uploads")
    return batch
