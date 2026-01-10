from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field
from pydantic import AliasChoices
from pydantic import ConfigDict


class UserLogin(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    identifier: str = Field(validation_alias=AliasChoices("identifier", "username", "email"))
    password: str


class UserRegister(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    username: str
    password: str
    invite_token: str = Field(validation_alias=AliasChoices("invite_token", "invite_code"))


class AuthSessionResponse(BaseModel):
    authenticated: bool
    username: Optional[str] = None
    is_admin: Optional[bool] = None
    account_expires_at: Optional[datetime] = None
    session_expires_at: Optional[datetime] = None
    csrf_token: Optional[str] = None


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None


class InviteCreate(BaseModel):
    email: EmailStr
    never_expires: bool = False
    send_email: bool = False


class InviteRequestCreate(BaseModel):
    email: EmailStr
    turnstile_token: str


class InviteRequestDecision(BaseModel):
    send_email: bool = False
    never_expires: bool = False
    notes: Optional[str] = None


class InviteRequestResponse(BaseModel):
    id: str
    email: str
    status: str
    requested_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    invite_id: Optional[str] = None
    notes: Optional[str] = None


class UserSuspend(BaseModel):
    reason: Optional[str] = None


class UserExtend(BaseModel):
    expires_at: Optional[datetime] = None


class InviteExtend(BaseModel):
    expires_at: Optional[datetime] = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    suspended_reason: Optional[str] = None
    deleted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
