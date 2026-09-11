import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_exception
    user = db.query(User).filter(User.id == uuid.UUID(payload["sub"])).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(*allowed_roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return dependency


def scoped_cpse_id(current_user: User, requested_cpse_id: uuid.UUID | None) -> uuid.UUID | None:
    """
    Company-level data isolation: a user registered under a specific CPSE
    (cpse_id set) can only ever see their own company's materials, no
    matter what cpse_id they pass - it is silently forced to their own
    rather than trusted from the request. A central/admin/approval user
    (cpse_id is None) is unrestricted and may filter by any cpse_id, or
    none, to compare across companies - that cross-company view is the
    entire point of the central approval workflow.
    """
    if current_user.cpse_id is not None:
        if requested_cpse_id is not None and requested_cpse_id != current_user.cpse_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own company's materials.",
            )
        return current_user.cpse_id
    return requested_cpse_id


def assert_cpse_access(current_user: User, target_cpse_id: uuid.UUID) -> None:
    """Same isolation rule as scoped_cpse_id, applied when a specific
    record (not a list filter) is being read - e.g. a single material's
    detail page."""
    if current_user.cpse_id is not None and current_user.cpse_id != target_cpse_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own company's materials.",
        )
