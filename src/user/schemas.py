import uuid
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from enum import Enum

from utils import CamelModelMixin


class Roles(str, Enum):
    """
    User roles
    """
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    USER = "user"


class UserBase(CamelModelMixin):
    """
    Base user model
    """
    email: EmailStr
    is_active: Optional[bool] = False
    full_name: Optional[str] = None
    roles: List[str] = []
    avatar: Optional[str] = None

    class Config:
        from_attributes = True


class UserBaseInDB(UserBase):
    """
    Base user model in DB
    """
    id: Optional[int] = None
    company_id: Optional[int] = None


class UserCreate(UserBase):
    """
    User create model
    """
    password: str


class UserCreateByEmail(UserBase):
    """
    User create model by email
    """
    email: str
    company_id: Optional[int] = None


class UserUpdate(UserBase):
    """
    User update model
    """
    old_password: Optional[str] = None
    new_password: Optional[str] = None
    company_id: Optional[int] = None


class UpdateUserProfile(CamelModelMixin):
    """
    Update user profile model schema
    """

    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    old_password: Optional[str] = None
    new_password: Optional[str] = None
    hashed_password: Optional[str] = None
    roles: List[str] = []
    company_id: Optional[int] = None
    avatar: Optional[str] = None


class User(UserBaseInDB):
    """
    User model
    """
    pass


class UserInDB(UserBaseInDB):
    """
    User model in DB
    """
    hashed_password: str


class TokenData(CamelModelMixin):
    """
    Token data model
    """
    token: str


class RegistrationCompletion(CamelModelMixin):
    """
    Registration completion model
    """
    token: str
    password: str
    company_id: Optional[int] = None
    full_name: Optional[str] = None


