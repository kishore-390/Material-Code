from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.enums import RoleName
from app.models.user import User
from app.schemas.settings import SystemSettingsOut, SystemSettingsUpdate
from app.services.settings_service import get_all_settings, update_settings

router = APIRouter(prefix="/settings", tags=["Admin Settings"])


@router.get("", response_model=SystemSettingsOut)
def read_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value)),
):
    return get_all_settings()


@router.put("", response_model=SystemSettingsOut)
def write_settings(
    payload: SystemSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value)),
):
    return update_settings(payload.model_dump(exclude_unset=True), db)
