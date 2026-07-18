from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    CONTENT_MANAGER = "content_manager"
    SUPPORT = "support"


class AdminAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SUSPEND = "suspend"
    REACTIVATE = "reactivate"
    ASSIGN_ROLE = "assign_role"
    RESET_STATS = "reset_stats"
    BROADCAST = "broadcast"
    EXPORT = "export"
    IMPORT = "import"
    LOGIN = "login"
    SETTINGS_CHANGE = "settings_change"
    CERTIFICATE_ISSUE = "certificate_issue"
    CERTIFICATE_REVOKE = "certificate_revoke"
    LEADERBOARD_REFRESH = "leaderboard_refresh"
    CHALLENGE_CREATE = "challenge_create"
    CHALLENGE_ARCHIVE = "challenge_archive"


class AdminLog(BaseModel):
    id: Optional[str] = None
    admin_id: str
    admin_email: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SystemSettings(BaseModel):
    id: Optional[str] = None
    key: str
    value: dict
    category: str
    updated_by: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SnippetCategory(BaseModel):
    id: Optional[str] = None
    name: str
    slug: str
    description: Optional[str] = None
    language: str
    difficulty: str = "beginner"
    icon: Optional[str] = None
    sort_order: int = 0
    snippet_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChallengeTemplate(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    type: str  # daily, weekly
    language: str
    category: str
    difficulty: str
    duration_seconds: int = 180
    xp_reward: int = 50
    bonus_xp: int = 25
    target_value: Optional[int] = None
    snippet_id: Optional[str] = None
    scheduled_date: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Certificate(BaseModel):
    id: Optional[str] = None
    user_id: str
    user_name: str
    user_email: str
    template_name: str
    title: str
    description: Optional[str] = None
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None
    verification_code: str
    metrics: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CertificateTemplate(BaseModel):
    id: Optional[str] = None
    name: str
    title: str
    description: str
    criteria: dict = Field(default_factory=dict)
    design: dict = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AdminNotification(BaseModel):
    id: Optional[str] = None
    title: str
    message: str
    type: str  # announcement, maintenance, challenge
    target: str = "all"  # all, users, premium
    sent_by: Optional[str] = None
    sent_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GlobalSearch(BaseModel):
    query: str
    types: List[str] = ["users", "snippets", "certificates", "challenges"]
    page: int = 1
    limit: int = 20


class PaginatedResponse(BaseModel):
    items: List[dict] = []
    total: int = 0
    page: int = 1
    limit: int = 20
    total_pages: int = 0
