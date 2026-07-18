from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class DashboardStatsResponse(BaseModel):
    total_users: int = 0
    active_users_today: int = 0
    new_registrations: int = 0
    completed_tests: int = 0
    daily_challenges_completed: int = 0
    average_accuracy: float = 0.0
    average_wpm: float = 0.0
    certificates_issued: int = 0
    leaderboard_entries: int = 0
    server_status: str = "operational"
    api_status: str = "operational"
    database_status: str = "connected"
    user_growth_data: List[dict] = []
    language_distribution: List[dict] = []
    activity_data: List[dict] = []


class UserListRequest(BaseModel):
    page: int = 1
    limit: int = 20
    search: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"


class UserListResponse(BaseModel):
    users: List[dict] = []
    total: int = 0
    page: int = 1
    limit: int = 20
    total_pages: int = 0


class UserActionRequest(BaseModel):
    action: str
    reason: Optional[str] = None


class UserRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(super_admin|admin|moderator|content_manager|support|user)$")


class SnippetCreateRequest(BaseModel):
    language: str
    title: str
    content: str
    difficulty: str = "beginner"
    category: str = "general"
    tags: List[str] = []
    explanation: Optional[str] = None
    is_active: bool = True


class SnippetUpdateRequest(BaseModel):
    language: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    difficulty: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    explanation: Optional[str] = None
    is_active: Optional[bool] = None


class SnippetBulkImportRequest(BaseModel):
    snippets: List[SnippetCreateRequest]
    language: Optional[str] = None


class CategoryCreateRequest(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    language: str
    difficulty: str = "beginner"
    icon: Optional[str] = None
    sort_order: int = 0


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None


class ChallengeCreateRequest(BaseModel):
    title: str
    description: str
    type: str = "daily"
    language: str
    category: str
    difficulty: str
    duration_seconds: int = 180
    xp_reward: int = 50
    bonus_xp: int = 25
    target_value: Optional[int] = None
    snippet_id: Optional[str] = None
    scheduled_date: Optional[str] = None


class ChallengeArchiveRequest(BaseModel):
    archived: bool = True
    reason: Optional[str] = None


class CertificateCreateRequest(BaseModel):
    user_id: str
    template_name: str
    title: str
    description: Optional[str] = None
    metrics: dict = {}


class CertificateRevokeRequest(BaseModel):
    reason: str


class LeaderboardRefreshRequest(BaseModel):
    metrics: List[str] = ["xp", "wpm", "accuracy", "streak", "tests"]
    recalculate: bool = True


class SuspiciousActivityRequest(BaseModel):
    user_id: Optional[str] = None
    threshold: float = 0.95


class ReportGenerateRequest(BaseModel):
    report_type: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    filters: dict = {}


class BroadcastNotificationRequest(BaseModel):
    title: str
    message: str
    type: str = "announcement"
    target: str = "all"


class SettingsUpdateRequest(BaseModel):
    key: str
    value: Any
    category: str


class AuditLogQuery(BaseModel):
    page: int = 1
    limit: int = 50
    admin_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class GlobalSearchRequest(BaseModel):
    query: str
    types: List[str] = ["users", "snippets", "certificates", "challenges"]
    page: int = 1
    limit: int = 20


class AdminResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: Any = None


class PaginatedResponseSchema(BaseModel):
    items: List[Any] = []
    total: int = 0
    page: int = 1
    limit: int = 20
    total_pages: int = 0
