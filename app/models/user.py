from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class AccountStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"
    PENDING = "pending"


class UserDocument(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    full_name: str
    email: EmailStr
    password_hash: str
    avatar: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole = UserRole.USER
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    email_verified: bool = False
    two_factor_enabled: bool = False
    account_status: AccountStatus = AccountStatus.ACTIVE
    theme_preference: str = "system"
    notification_settings: dict = Field(default_factory=lambda: {
        "email_notifications": True,
        "project_updates": True,
        "ai_reports": True,
        "security_alerts": True,
        "marketing": False,
    })
    timezone: str = "UTC"
    language: str = "en"
    reset_token: Optional[str] = None
    reset_token_expires: Optional[datetime] = None
    verification_token: Optional[str] = None
    company: Optional[str] = None
    bio: Optional[str] = None
    social_links: dict = Field(default_factory=lambda: {
        "twitter": "",
        "linkedin": "",
        "github": "",
        "website": "",
    })

    model_config = {"populate_by_name": True}
