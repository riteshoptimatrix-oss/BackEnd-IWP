from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class DifficultyLevel(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class TypingSession(BaseModel):
    id: Optional[str] = None
    user_id: str
    language: str
    difficulty: str
    category: str
    snippet_id: str
    snippet_title: Optional[str] = None
    duration_seconds: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    completion_time: float = 0.0
    characters_typed: int = 0
    correct_characters: int = 0
    incorrect_characters: int = 0
    total_mistakes: int = 0
    backspaces: int = 0
    accuracy: float = 0.0
    cpm: float = 0.0
    wpm: float = 0.0
    completion_pct: float = 0.0
    finished: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserTypingStats(BaseModel):
    id: Optional[str] = None
    user_id: str
    total_tests: int = 0
    total_practice_seconds: float = 0.0
    avg_wpm: float = 0.0
    avg_accuracy: float = 0.0
    best_wpm: float = 0.0
    best_accuracy: float = 0.0
    best_cpm: float = 0.0
    longest_session_seconds: float = 0.0
    favorite_language: Optional[str] = None
    most_practiced_category: Optional[str] = None
    languages_practiced: list = []
    categories_practiced: list = []
    current_streak: int = 0
    longest_streak: int = 0
    last_practice_date: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
