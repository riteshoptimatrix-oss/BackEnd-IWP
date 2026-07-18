from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Achievement(BaseModel):
    id: Optional[str] = None
    key: str
    name: str
    description: str
    icon: str
    category: str
    xp_reward: int = 0
    tier: str = "bronze"
    condition_type: str
    condition_value: int = 0
    condition_language: Optional[str] = None


class UserAchievement(BaseModel):
    id: Optional[str] = None
    user_id: str
    achievement_key: str
    unlocked_at: datetime = Field(default_factory=datetime.utcnow)


class DailyChallenge(BaseModel):
    id: Optional[str] = None
    date: str
    language: str
    category: str
    difficulty: str
    duration_seconds: int = 180
    xp_reward: int = 50
    bonus_xp: int = 25
    title: str
    description: str
    snippet_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WeeklyChallenge(BaseModel):
    id: Optional[str] = None
    week_start: str
    type: str
    title: str
    description: str
    target_value: int
    current_value: int = 0
    language: Optional[str] = None
    xp_reward: int = 200
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserChallenge(BaseModel):
    id: Optional[str] = None
    user_id: str
    challenge_id: str
    challenge_type: str
    completed: bool = False
    completed_at: Optional[datetime] = None
    xp_awarded: int = 0


class LeaderboardEntry(BaseModel):
    user_id: str
    display_name: str
    avatar: Optional[str] = None
    score: float = 0
    rank: int = 0
    previous_rank: Optional[int] = None
    level: int = 1
    xp: int = 0
    best_wpm: float = 0
    avg_accuracy: float = 0
    current_streak: int = 0
    total_tests: int = 0


class XPTransaction(BaseModel):
    id: Optional[str] = None
    user_id: str
    amount: int
    type: str
    description: str
    session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserGamification(BaseModel):
    id: Optional[str] = None
    user_id: str
    xp: int = 0
    level: int = 1
    title: str = "Beginner"
    total_xp_earned: int = 0
    coins: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StreakData(BaseModel):
    current_streak: int = 0
    longest_streak: int = 0
    last_practice_date: Optional[str] = None
    streak_calendar: List[str] = []
