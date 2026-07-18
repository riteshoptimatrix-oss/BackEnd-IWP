from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AchievementResponse(BaseModel):
    key: str
    name: str
    description: str
    icon: str
    category: str
    tier: str
    xp_reward: int
    unlocked: bool = False
    unlocked_at: Optional[str] = None


class AchievementsListResponse(BaseModel):
    achievements: List[AchievementResponse]
    total_unlocked: int
    total_available: int


class LeaderboardQuery(BaseModel):
    period: str = "all_time"
    language: Optional[str] = None
    metric: str = "xp"
    page: int = 1
    limit: int = 50


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    display_name: str
    avatar: Optional[str] = None
    score: float
    level: int
    xp: int
    title: str
    best_wpm: float
    current_streak: int


class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]
    total: int
    page: int
    limit: int
    has_more: bool


class UserRankResponse(BaseModel):
    current_rank: int
    previous_rank: Optional[int] = None
    rank_change: Optional[int] = None
    top_percentage: float
    xp: int
    level: int
    title: str
    progress_to_next: float
    xp_for_next_level: int
    metric_score: float


class DailyChallengeResponse(BaseModel):
    id: str
    language: str
    category: str
    difficulty: str
    duration_seconds: int
    xp_reward: int
    bonus_xp: int
    title: str
    description: str
    completed: bool = False
    completed_at: Optional[str] = None


class DailyChallengesResponse(BaseModel):
    challenges: List[DailyChallengeResponse]
    date: str
    streak_days: int = 0


class WeeklyMissionResponse(BaseModel):
    id: str
    type: str
    title: str
    description: str
    target_value: int
    current_value: int
    progress_pct: float
    language: Optional[str] = None
    xp_reward: int
    completed: bool


class WeeklyChallengesResponse(BaseModel):
    missions: List[WeeklyMissionResponse]
    week_start: str
    week_end: str
    completed_count: int
    total_count: int


class ChallengeCompleteRequest(BaseModel):
    challenge_id: str
    challenge_type: str


class ChallengeCompleteResponse(BaseModel):
    success: bool
    xp_earned: int
    message: str


class XPInfoResponse(BaseModel):
    xp: int
    level: int
    title: str
    xp_for_current_level: int
    xp_for_next_level: int
    progress_to_next: float
    total_xp_earned: int
    recent_transactions: List[dict] = []


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    last_practice_date: Optional[str] = None
    streak_calendar: List[str] = []
    today_practiced: bool = False


class GamificationProfileResponse(BaseModel):
    user_id: str
    display_name: str
    avatar: Optional[str] = None
    xp: int
    level: int
    title: str
    total_xp_earned: int
    current_streak: int
    longest_streak: int
    achievements_count: int
    total_achievements: int
    rank: Optional[int] = None
    top_percentage: Optional[float] = None
