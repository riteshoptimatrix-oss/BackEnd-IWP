from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FinishSessionRequest(BaseModel):
    language: str = Field(..., min_length=1, max_length=50)
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    category: str = Field(..., min_length=1, max_length=100)
    snippet_id: str = Field(..., min_length=1, max_length=100)
    snippet_title: Optional[str] = None
    duration_seconds: Optional[int] = Field(None, ge=1, le=3600)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    completion_time: float = Field(..., ge=0)
    characters_typed: int = Field(..., ge=0)
    correct_characters: int = Field(..., ge=0)
    incorrect_characters: int = Field(..., ge=0)
    total_mistakes: int = Field(default=0, ge=0)
    backspaces: int = Field(default=0, ge=0)
    accuracy: float = Field(..., ge=0, le=100)
    cpm: float = Field(default=0, ge=0)
    wpm: float = Field(default=0, ge=0)
    completion_pct: float = Field(default=0, ge=0, le=100)
    finished: bool = False


class FinishSessionResponse(BaseModel):
    session_id: str
    wpm: float
    accuracy: float
    is_new_best_wpm: bool = False
    is_new_best_accuracy: bool = False
    created_at: str
    xp_earned: int = 0
    level: int = 1
    level_up: bool = False
    new_level: Optional[int] = None
    total_xp: int = 0
    streak: int = 0
    achievements_unlocked: List[str] = []


class TypingSessionResponse(BaseModel):
    id: str
    language: str
    difficulty: str
    category: str
    snippet_title: Optional[str] = None
    wpm: float
    accuracy: float
    cpm: float
    characters_typed: int
    correct_characters: int
    incorrect_characters: int
    total_mistakes: int
    completion_time: float
    completion_pct: float
    finished: bool
    duration_seconds: Optional[int] = None
    created_at: str


class HistoryResponse(BaseModel):
    sessions: List[TypingSessionResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class PersonalRecords(BaseModel):
    best_wpm: float = 0.0
    best_accuracy: float = 0.0
    best_cpm: float = 0.0
    longest_session_seconds: float = 0.0
    best_language: Optional[str] = None
    best_difficulty: Optional[str] = None


class ProfileStatsResponse(BaseModel):
    total_tests: int = 0
    total_practice_hours: float = 0.0
    avg_wpm: float = 0.0
    avg_accuracy: float = 0.0
    best_wpm: float = 0.0
    best_accuracy: float = 0.0
    favorite_language: Optional[str] = None
    most_practiced_category: Optional[str] = None
    languages_practiced: List[str] = []
    current_streak: int = 0
    longest_streak: int = 0
    personal_records: PersonalRecords


class LanguageStats(BaseModel):
    language: str
    tests: int = 0
    avg_wpm: float = 0.0
    avg_accuracy: float = 0.0
    best_wpm: float = 0.0
    best_accuracy: float = 0.0


class DifficultyStats(BaseModel):
    difficulty: str
    tests: int = 0
    avg_wpm: float = 0.0
    avg_accuracy: float = 0.0


class StatisticsResponse(BaseModel):
    overall: ProfileStatsResponse
    by_language: List[LanguageStats] = []
    by_difficulty: List[DifficultyStats] = []


class ProfileResponse(BaseModel):
    user_id: str
    display_name: str
    email: str
    avatar: Optional[str] = None
    joined_at: str
    stats: ProfileStatsResponse


class LanguageResponse(BaseModel):
    id: str
    name: str
    color: str
    description: str


class LanguagesResponse(BaseModel):
    languages: List[LanguageResponse]
