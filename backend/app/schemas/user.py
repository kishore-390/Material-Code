import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RoleOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class CPSEBrief(BaseModel):
    id: uuid.UUID
    code: str
    name: str

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    full_name: str
    password: str = Field(min_length=6)
    role_name: str
    cpse_code: Optional[str] = None


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    full_name: str
    is_active: bool
    role: RoleOut
    cpse: Optional[CPSEBrief] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
