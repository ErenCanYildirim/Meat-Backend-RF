from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    pass


class RoleRead(RoleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    email: EmailStr
    company_name: Optional[str] = None
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserCreateWithRoles(UserCreate):
    role_ids: Optional[List[UUID]] = []


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    roles: List[RoleRead] = []

    class Config:
        orm_mode = True


class UserUpdate(UserBase):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    company_name: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[str]] = None


class UserResponse(UserBase):
    id: str
    created_at: datetime

    class Config:
        orm_mode = True


class UserInDBBase(UserBase):
    id: str

    class Config:
        from_attributes = True


# Auth
class TokenData(BaseModel):
    company_name: Optional[str] = None
