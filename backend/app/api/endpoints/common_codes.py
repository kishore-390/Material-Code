from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.harmonization import CommonMaterialCode
from app.models.material import Material
from app.models.user import User
from app.schemas.common_code import CommonMaterialCodeDetail, CommonMaterialCodeOut

router = APIRouter(prefix="/common-codes", tags=["Common Material Master"])


@router.get("", response_model=list[CommonMaterialCodeOut])
def list_common_codes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(CommonMaterialCode).order_by(CommonMaterialCode.created_at.desc()).all()


@router.get("/{code}", response_model=CommonMaterialCodeDetail)
def get_common_code(code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    common_code = db.query(CommonMaterialCode).filter(CommonMaterialCode.code == code).first()
    if not common_code:
        raise HTTPException(status_code=404, detail="Common material code not found")

    linked_materials = db.query(Material).filter(Material.common_code_id == common_code.id).all()
    linked_cpses = sorted({m.cpse.code for m in linked_materials if m.cpse})

    out = CommonMaterialCodeDetail.model_validate(common_code)
    out.linked_materials = linked_materials
    out.linked_cpses = linked_cpses
    return out
