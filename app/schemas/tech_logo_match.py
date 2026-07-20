from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FinishGameRequest(BaseModel):
    category: str = Field(..., min_length=1, max_length=50)
    difficulty: str = Field(..., pattern="^(easy|medium|hard|expert)$")
    mode: str = Field(..., min_length=1, max_length=50)
    score: int = Field(..., ge=0)
    correct: int = Field(..., ge=0)
    wrong: int = Field(..., ge=0)
    accuracy: float = Field(..., ge=0, le=100)
    avg_time: float = Field(..., ge=0)
    best_streak: int = Field(..., ge=0)
    stars: int = Field(..., ge=1, le=3)
    total_questions: int = Field(..., ge=1)
    duration_seconds: int = Field(..., ge=1)


class FinishGameResponse(BaseModel):
    game_id: str
    saved: bool
    message: str = "Game saved successfully"
    total_games: int = 0
    current_streak: int = 0
    xp_awarded: int = 0
    total_xp: int = 0
    level: int = 1
    level_up: bool = False
    new_achievements: List[dict] = []
    new_badges: List[dict] = []


class GameHistoryItem(BaseModel):
    id: str
    category: str
    difficulty: str
    mode: str
    score: int
    correct: int
    wrong: int
    accuracy: float
    avg_time: float
    best_streak: int
    stars: int
    total_questions: int
    duration_seconds: int
    created_at: str


class GameHistoryResponse(BaseModel):
    games: List[GameHistoryItem]
    total: int
    page: int
    limit: int
    has_more: bool


class StatisticsResponse(BaseModel):
    total_games: int = 0
    total_correct: int = 0
    total_wrong: int = 0
    average_accuracy: float = 0
    average_score: float = 0
    highest_score: int = 0
    fastest_completion: Optional[int] = None
    favorite_category: Optional[str] = None
    favorite_difficulty: Optional[str] = None
    favorite_mode: Optional[str] = None
    current_streak: int = 0
    longest_streak: int = 0
    three_star_games: int = 0
    total_duration: int = 0


class ProfileResponse(BaseModel):
    full_name: str
    email: str
    username: str = ""
    games_played: int = 0
    games_won: int = 0
    overall_accuracy: float = 0
    best_score: int = 0
    best_response_time: Optional[float] = None
    favorite_technology: Optional[str] = None
    favorite_category: Optional[str] = None
    favorite_difficulty: Optional[str] = None
    current_streak: int = 0
    longest_streak: int = 0
    total_stars: int = 0
    registered: str = ""


class SaveSettingsRequest(BaseModel):
    sound_enabled: Optional[bool] = None
    animations_enabled: Optional[bool] = None
    timer_visible: Optional[bool] = None
    high_contrast: Optional[bool] = None
    reduced_motion: Optional[bool] = None
    preferred_difficulty: Optional[str] = Field(None, pattern="^(easy|medium|hard|expert)?$")
    preferred_category: Optional[str] = None
    preferred_mode: Optional[str] = None


class SettingsResponse(BaseModel):
    sound_enabled: bool = True
    animations_enabled: bool = True
    timer_visible: bool = True
    high_contrast: bool = False
    reduced_motion: bool = False
    preferred_difficulty: Optional[str] = None
    preferred_category: Optional[str] = None
    preferred_mode: Optional[str] = None


class DashboardResponse(BaseModel):
    total_games: int = 0
    total_stars: int = 0
    average_accuracy: float = 0
    current_streak: int = 0
    longest_streak: int = 0
    favorite_category: Optional[str] = None
    favorite_difficulty: Optional[str] = None
    favorite_mode: Optional[str] = None
    best_score: int = 0
    highest_accuracy: float = 0
    fastest_completion: Optional[int] = None
    recent_games: List[GameHistoryItem] = []


class CategoryMetric(BaseModel):
    category: str
    games_played: int = 0
    average_accuracy: float = 0
    average_score: float = 0
    completion_rate: float = 0
    total_stars: int = 0


class ModeMetric(BaseModel):
    mode: str
    games_played: int = 0
    average_accuracy: float = 0
    average_time: float = 0
    best_score: int = 0


class DifficultyMetric(BaseModel):
    difficulty: str
    games_played: int = 0
    average_accuracy: float = 0
    average_time: float = 0
    success_rate: float = 0
    average_score: float = 0


class HeatmapEntry(BaseModel):
    date: str
    count: int


class ActivityEntry(BaseModel):
    date: str
    games: int = 0
    accuracy: float = 0


class InsightEntry(BaseModel):
    type: str
    message: str
    direction: str = "neutral"


class PersonalBest(BaseModel):
    label: str
    value: str
    icon: str = "star"


class AnalyticsResponse(BaseModel):
    total_games: int = 0
    total_stars: int = 0
    overall_accuracy: float = 0
    average_accuracy: float = 0
    highest_score: int = 0
    average_score: float = 0
    fastest_completion: Optional[int] = None
    average_response_time: float = 0
    current_streak: int = 0
    longest_streak: int = 0
    favorite_category: Optional[str] = None
    favorite_difficulty: Optional[str] = None
    favorite_mode: Optional[str] = None
    categories: List[CategoryMetric] = []
    modes: List[ModeMetric] = []
    difficulties: List[DifficultyMetric] = []
    heatmap: List[HeatmapEntry] = []
    daily_activity: List[ActivityEntry] = []
    weekly_activity: List[ActivityEntry] = []
    monthly_activity: List[ActivityEntry] = []
    personal_bests: List[PersonalBest] = []
    insights: List[InsightEntry] = []
    recent_games: List[GameHistoryItem] = []


class XpAward(BaseModel):
    xp: int = 0
    reason: str = ""
    icon: str = "zap"


class LevelInfo(BaseModel):
    level: int = 1
    current_xp: int = 0
    xp_for_next: int = 250
    progress: float = 0
    rank: str = "Beginner"
    rank_icon: str = "🌱"


class AchievementDefinition(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    xp_reward: int = 0
    progress_current: float = 0
    progress_target: float = 1
    unlocked: bool = False
    unlocked_at: Optional[str] = None


class BadgeItem(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    tier: str = "bronze"
    unlocked: bool = False
    unlocked_at: Optional[str] = None


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: str
    avatar: Optional[str] = None
    value: float = 0
    level: int = 1
    rank_title: str = "Beginner"


class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry] = []
    total: int = 0
    page: int = 1
    limit: int = 20
    has_more: bool = False
    my_rank: Optional[LeaderboardEntry] = None
    metric: str = "xp"
    scope: str = "overall"


class PlayerRankResponse(BaseModel):
    rank: int = 0
    total: int = 0
    value: float = 0
    metric: str = "xp"


class ChallengeBase(BaseModel):
    id: str
    title: str
    description: str
    type: str
    target: int = 1
    progress: int = 0
    completed: bool = False
    xp_reward: int = 0
    expires_at: str = ""


class DailyChallengeResponse(BaseModel):
    challenge: Optional[ChallengeBase] = None
    completed: bool = False


class WeeklyChallengeResponse(BaseModel):
    challenge: Optional[ChallengeBase] = None
    completed: bool = False


class ChallengeHistoryItem(BaseModel):
    id: str
    title: str
    type: str
    challenge_type: str = "daily"
    completed: bool
    xp_reward: int = 0
    completed_at: str = ""


class ChallengeHistoryResponse(BaseModel):
    challenges: List[ChallengeHistoryItem] = []
    total: int = 0


class RewardItem(BaseModel):
    id: str
    xp: int = 0
    reason: str = ""
    icon: str = "zap"
    created_at: str = ""


class RewardsResponse(BaseModel):
    total_xp: int = 0
    level: int = 1
    rank: str = "Beginner"
    recent_rewards: List[RewardItem] = []


class NotificationItem(BaseModel):
    id: str
    type: str = ""
    title: str = ""
    message: str = ""
    read: bool = False
    created_at: str = ""


class NotificationsResponse(BaseModel):
    notifications: List[NotificationItem] = []
    unread_count: int = 0


class PlayerProfileResponse(BaseModel):
    username: str = ""
    full_name: str = ""
    level: int = 1
    current_xp: int = 0
    xp_for_next: int = 250
    progress: float = 0
    rank: str = "Beginner"
    rank_icon: str = "🌱"
    games_played: int = 0
    average_accuracy: float = 0
    current_streak: int = 0
    longest_streak: int = 0
    achievements_unlocked: int = 0
    total_achievements: int = 0
    badges_unlocked: int = 0
    total_badges: int = 0
    favorite_category: Optional[str] = None
    favorite_difficulty: Optional[str] = None
    favorite_mode: Optional[str] = None
