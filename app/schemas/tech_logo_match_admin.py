from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TechnologyStatus(str, Enum):
    active = "active"
    archived = "archived"


class QuestionType(str, Enum):
    logo_to_name = "logo_to_name"
    name_to_logo = "name_to_logo"
    logo_to_category = "logo_to_category"
    mixed = "mixed"


class AdminRole(str, Enum):
    super_admin = "super_admin"
    admin = "admin"
    content_manager = "content_manager"
    moderator = "moderator"
    viewer = "viewer"


class ExportFormat(str, Enum):
    csv = "csv"
    excel = "excel"
    json = "json"


# ── Technology ──

class TechnologyCreate(BaseModel):
    official_name: str = Field(..., min_length=1, max_length=200)
    short_name: str = Field(..., min_length=1, max_length=50)
    category: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    difficulty: str = Field(default="beginner", pattern="^(beginner|easy|medium|hard|expert)$")
    aliases: list[str] = Field(default_factory=list)
    official_url: str = Field(default="", max_length=500)
    display_order: int = Field(default=0, ge=0)
    status: TechnologyStatus = TechnologyStatus.active


class TechnologyUpdate(BaseModel):
    official_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    short_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=2000)
    difficulty: Optional[str] = Field(default=None, pattern="^(beginner|easy|medium|hard|expert)$")
    aliases: Optional[list[str]] = None
    official_url: Optional[str] = Field(default=None, max_length=500)
    display_order: Optional[int] = Field(default=None, ge=0)
    status: Optional[TechnologyStatus] = None


class TechnologyResponse(BaseModel):
    id: str
    official_name: str
    short_name: str
    category: str
    description: str
    difficulty: str
    aliases: list[str]
    official_url: str
    display_order: int
    status: TechnologyStatus
    logo_path: Optional[str] = None
    logo_url: Optional[str] = None
    logo_mime: Optional[str] = None
    logo_size: Optional[int] = None
    created_at: str
    updated_at: str
    created_by: Optional[str] = None
    version: int = 1


class TechnologyListResponse(BaseModel):
    technologies: list[TechnologyResponse]
    total: int
    page: int
    limit: int
    has_more: bool


# ── Category ──

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    icon: str = Field(default="", max_length=50)
    display_order: int = Field(default=0, ge=0)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    icon: Optional[str] = Field(default=None, max_length=50)
    display_order: Optional[int] = Field(default=None, ge=0)


class CategoryResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    display_order: int
    technology_count: int = 0
    created_at: str
    updated_at: str


# ── Pack ──

class PackCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    technologies: list[str] = Field(default_factory=list)
    difficulty: str = Field(default="beginner", pattern="^(beginner|easy|medium|hard|expert)$")
    estimated_minutes: int = Field(default=30, ge=1)


class PackUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    technologies: Optional[list[str]] = None
    difficulty: Optional[str] = Field(default=None, pattern="^(beginner|easy|medium|hard|expert)$")
    estimated_minutes: Optional[int] = Field(default=None, ge=1)


class PackResponse(BaseModel):
    id: str
    name: str
    description: str
    technologies: list[str]
    difficulty: str
    estimated_minutes: int
    technology_count: int = 0
    created_at: str
    updated_at: str


class PackListResponse(BaseModel):
    packs: list[PackResponse]
    total: int


# ── Question ──

class QuestionCreate(BaseModel):
    technology_id: str = Field(..., min_length=1)
    question_type: QuestionType
    prompt: str = Field(..., min_length=1, max_length=1000)
    correct_answer: str = Field(..., min_length=1, max_length=500)
    options: list[str] = Field(default_factory=list)
    difficulty: str = Field(default="beginner", pattern="^(beginner|easy|medium|hard|expert)$")
    category: str = Field(default="", max_length=100)
    tags: list[str] = Field(default_factory=list)


class QuestionUpdate(BaseModel):
    technology_id: Optional[str] = Field(default=None, min_length=1)
    question_type: Optional[QuestionType] = None
    prompt: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    correct_answer: Optional[str] = Field(default=None, min_length=1, max_length=500)
    options: Optional[list[str]] = None
    difficulty: Optional[str] = Field(default=None, pattern="^(beginner|easy|medium|hard|expert)$")
    category: Optional[str] = Field(default=None, max_length=100)
    tags: Optional[list[str]] = None


class QuestionResponse(BaseModel):
    id: str
    technology_id: str
    technology_name: str = ""
    question_type: QuestionType
    prompt: str
    correct_answer: str
    options: list[str]
    difficulty: str
    category: str
    tags: list[str]
    created_at: str
    updated_at: str


class QuestionListResponse(BaseModel):
    questions: list[QuestionResponse]
    total: int
    page: int
    limit: int
    has_more: bool


# ── Asset (Logo) ──

class AssetResponse(BaseModel):
    id: str
    filename: str
    original_name: str
    mime_type: str
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    url: str
    path: str
    version: int
    technology_id: Optional[str] = None
    is_alternative: bool = False
    label: str = ""
    created_at: str
    created_by: Optional[str] = None


class AssetListResponse(BaseModel):
    assets: list[AssetResponse]
    total: int
    page: int
    limit: int


# ── Version History ──

class VersionResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    action: str
    changes: dict
    changed_by: Optional[str] = None
    changed_at: str
    version: int


# ── Bulk Import ──

class BulkImportItem(BaseModel):
    row: int
    status: str
    message: str
    data: Optional[dict] = None


class BulkImportResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    items: list[BulkImportItem]


class BulkImportRequest(BaseModel):
    items: list[dict]
    format: str = "json"


# ── Validation ──

class ValidationIssue(BaseModel):
    type: str
    severity: str
    entity_type: str
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    message: str
    details: Optional[dict] = None


class ValidationResponse(BaseModel):
    total_issues: int
    errors: int
    warnings: int
    issues: list[ValidationIssue]
    passed: bool


# ── Dashboard ──

class AdminDashboardStats(BaseModel):
    total_technologies: int
    active_technologies: int
    archived_technologies: int
    total_categories: int
    total_packs: int
    total_questions: int
    total_assets: int
    assets_size_bytes: int = 0
    technologies_without_logo: int
    technologies_by_difficulty: dict[str, int] = {}
    technologies_by_category: dict[str, int] = {}
    recent_activity: list[VersionResponse] = []
