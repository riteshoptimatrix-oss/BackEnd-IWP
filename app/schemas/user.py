from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = None
    company: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None
    social_links: Optional[dict] = None


class UserSettingsUpdate(BaseModel):
    theme_preference: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    notification_settings: Optional[dict] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    avatar: Optional[str] = None
    phone: Optional[str] = None
    role: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    email_verified: bool
    two_factor_enabled: bool
    account_status: str
    theme_preference: str
    notification_settings: dict
    timezone: str
    language: str
    company: Optional[str] = None
    bio: Optional[str] = None
    social_links: dict
