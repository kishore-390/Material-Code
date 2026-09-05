import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.harmonization import CommonMaterialCode
from app.models.material import Material
from app.models.user import User
from app.schemas.common_code import CommonMaterialCodeDetail, CommonMaterialCodeOut

router = APIRouter(prefix="/common-codes", tags=["Common Material Master"])
# Spec asks for GET /api/common-materials/{code} specifically; rather than a
# parallel implementation, this second router mounts the same handler body
# (see _get_common_code_detail) under that alternate path.
common_materials_router = APIRouter(prefix="/common-materials", tags=["Common Material Master"])


@router.get("", response_model=list[CommonMaterialCodeOut])
def list_common_codes(
    cpse_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(CommonMaterialCode)
    if cpse_id:
        query = query.filter(
            CommonMaterialCode.id.in_(
                db.query(Material.common_code_id).filter(
                    Material.cpse_id == cpse_id, Material.common_code_id.isnot(None)
                )
            )
        )
    return query.order_by(CommonMaterialCode.created_at.desc()).all()


def _get_common_code_detail(code: str, db: Session) -> CommonMaterialCodeDetail:
    common_code = db.query(CommonMaterialCode).filter(CommonMaterialCode.code == code).first()
    if not common_code:
        raise HTTPException(status_code=404, detail="Common material code not found")

    linked_materials = db.query(Material).filter(Material.common_code_id == common_code.id).all()
    linked_cpses = sorted({m.cpse.code for m in linked_materials if m.cpse})

    out = CommonMaterialCodeDetail.model_validate(common_code)
    out.linked_materials = linked_materials
    out.linked_cpses = linked_cpses
    return out


@router.get("/{code}", response_model=CommonMaterialCodeDetail)
def get_common_code(code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get_common_code_detail(code, db)


@common_materials_router.get("/{code}", response_model=CommonMaterialCodeDetail)
def get_common_material(code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get_common_code_detail(code, db)
