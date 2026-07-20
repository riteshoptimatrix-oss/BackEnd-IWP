from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FinishGameRequest(BaseModel):
    language: str = Field(..., min_length=1, max_length=50)
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    completion_time_seconds: int = Field(..., ge=1, le=3600)
    moves: int = Field(..., ge=1)
    correct_matches: int = Field(..., ge=0)
    wrong_matches: int = Field(..., ge=0)
    accuracy: float = Field(..., ge=0, le=100)
    stars: int = Field(..., ge=1, le=3)
    total_pairs: int = Field(..., ge=1)


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
    language: str
    difficulty: str
    completion_time_seconds: int
    moves: int
    correct_matches: int
    wrong_matches: int
    accuracy: float
    stars: int
    total_pairs: int
    created_at: str


class GameHistoryResponse(BaseModel):
    games: List[GameHistoryItem]
    total: int
    page: int
    limit: int
    has_more: bool


class StatisticsResponse(BaseModel):
    total_games: int
    total_matches: int
    total_moves: int
    total_correct: int
    total_wrong: int
    average_accuracy: float
    average_moves: float
    average_completion_time: float
    best_accuracy: float
    fastest_completion: Optional[int] = None
    best_moves: Optional[int] = None
    favorite_language: Optional[str] = None
    favorite_difficulty: Optional[str] = None
    current_streak: int = 0
    longest_streak: int = 0
    three_star_games: int = 0


class ProfileResponse(BaseModel):
    full_name: str
    email: str
    total_games: int
    total_stars: int
    average_accuracy: float
    current_streak: int
    best_accuracy: float
    best_time: Optional[int] = None
    best_moves: Optional[int] = None
    favorite_language: Optional[str] = None
    favorite_difficulty: Optional[str] = None


class SaveSettingsRequest(BaseModel):
    card_flip_speed: Optional[str] = Field(None, pattern="^(slow|normal|fast)$")
    animation_speed: Optional[str] = Field(None, pattern="^(slow|normal|fast)$")
    sound_enabled: Optional[bool] = None
    music_enabled: Optional[bool] = None
    preview_duration: Optional[int] = Field(None, ge=2, le=10)
    reduced_motion: Optional[bool] = None
    last_language: Optional[str] = None
    last_difficulty: Optional[str] = None


class SettingsResponse(BaseModel):
    card_flip_speed: str = "normal"
    animation_speed: str = "normal"
    sound_enabled: bool = True
    music_enabled: bool = False
    preview_duration: Optional[int] = None
    reduced_motion: bool = False
    last_language: Optional[str] = None
    last_difficulty: Optional[str] = None


class DashboardResponse(BaseModel):
    total_games: int
    total_stars: int
    average_accuracy: float
    current_streak: int
    longest_streak: int
    favorite_language: Optional[str] = None
    favorite_difficulty: Optional[str] = None
    best_accuracy: float
    fastest_completion: Optional[int] = None
    recent_games: List[GameHistoryItem]
    weekly_activity: list = []
    monthly_activity: list = []


# ── Phase 21: Analytics ──

class LanguagePerformanceItem(BaseModel):
    language: str
    games_played: int = 0
    average_accuracy: float = 0
    average_time: float = 0
    best_time: Optional[int] = None
    best_moves: Optional[int] = None
    completion_rate: float = 0
    total_stars: int = 0
    favorite_difficulty: Optional[str] = None


class DifficultyPerformanceItem(BaseModel):
    difficulty: str
    games_played: int = 0
    average_accuracy: float = 0
    average_time: float = 0
    success_rate: float = 0
    average_moves: float = 0


class HeatmapItem(BaseModel):
    date: str
    count: int = 0


class InsightItem(BaseModel):
    type: str
    message: str
    direction: str = "up"
    value: Optional[str] = None


class ActivityItem(BaseModel):
    date: str
    games: int = 0
    accuracy: float = 0
    completion_time: float = 0


class PersonalBestItem(BaseModel):
    label: str
    value: str
    icon: str = "star"


class AchievementProgressItem(BaseModel):
    label: str
    current: float
    target: float
    percent: float = 0


class AnalyticsResponse(BaseModel):
    # Overview
    total_games: int = 0
    games_completed: int = 0
    total_matches: int = 0
    total_wrong_matches: int = 0
    overall_accuracy: float = 0
    average_accuracy: float = 0
    fastest_game: Optional[int] = None
    average_completion_time: float = 0
    average_moves: float = 0
    best_star_rating: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    favorite_language: Optional[str] = None
    favorite_difficulty: Optional[str] = None

    # Sections
    languages: List[LanguagePerformanceItem] = []
    difficulties: List[DifficultyPerformanceItem] = []
    heatmap: List[HeatmapItem] = []
    insights: List[InsightItem] = []

    # Activity
    daily_activity: List[ActivityItem] = []
    weekly_activity: List[ActivityItem] = []
    monthly_activity: List[ActivityItem] = []
    yearly_activity: List[ActivityItem] = []

    # Personal Bests
    personal_bests: List[PersonalBestItem] = []

    # Achievement Progress
    achievement_progress: List[AchievementProgressItem] = []


class ExportResponse(BaseModel):
    csv: str = ""
    excel: str = ""
    pdf: str = ""


# ══════════════════════════════════════════════
# Phase 22: Gamification
# ══════════════════════════════════════════════

# ── XP & Levels ──

class XpAward(BaseModel):
    amount: int
    reason: str
    game_id: Optional[str] = None


class LevelInfo(BaseModel):
    level: int
    current_xp: int
    xp_for_next: int
    rank: str
    progress_percent: float


class RankBadge(BaseModel):
    name: str
    level: int
    icon: str = "star"


# ── Achievements ──

class AchievementDefinition(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    xp_reward: int
    category: str
    requirement_type: str
    requirement_value: float


class AchievementProgress(BaseModel):
    achievement_id: str
    title: str
    description: str
    icon: str
    xp_reward: int
    category: str
    current: float
    target: float
    progress_percent: float
    unlocked: bool = False
    unlocked_at: Optional[str] = None


class AchievementUnlockResponse(BaseModel):
    achievement_id: str
    title: str
    description: str
    icon: str
    xp_reward: int
    xp_awarded: int
    newly_unlocked: bool


# ── Badges ──

class BadgeItem(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    tier: str
    category: str
    unlocked: bool = False
    unlocked_at: Optional[str] = None


# ── Leaderboards ──

class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: str
    avatar: Optional[str] = None
    level: int
    rank_name: str
    score: float
    games_played: int
    accuracy: float
    streak: int


class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]
    total: int
    page: int
    limit: int
    metric: str
    scope: str


class PlayerRankResponse(BaseModel):
    rank: int
    total_players: int
    score: float


# ── Challenges ──

class ChallengeBase(BaseModel):
    id: str
    title: str
    description: str
    type: str
    requirement_type: str
    requirement_value: float
    xp_reward: int
    badge_reward: Optional[str] = None
    starts_at: str
    expires_at: str
    status: str = "active"


class DailyChallengeResponse(BaseModel):
    challenge: Optional[ChallengeBase] = None
    progress: float = 0
    completed: bool = False


class WeeklyChallengeResponse(BaseModel):
    challenge: Optional[ChallengeBase] = None
    progress: float = 0
    completed: bool = False


class ChallengeHistoryItem(BaseModel):
    id: str
    title: str
    type: str
    status: str
    xp_reward: int
    progress: float
    completed_at: Optional[str] = None


class ChallengeHistoryResponse(BaseModel):
    challenges: List[ChallengeHistoryItem]
    total: int


# ── Rewards ──

class RewardItem(BaseModel):
    id: str
    type: str
    title: str
    description: str
    icon: str
    tier: str = "bronze"
    xp_awarded: int
    source: str
    unlocked_at: str
    claimed: bool = True


class RewardsResponse(BaseModel):
    recent: List[RewardItem]
    total_xp_earned: int
    total_rewards: int


# ── Notifications ──

class NotificationItem(BaseModel):
    id: str
    type: str
    title: str
    message: str
    icon: str
    read: bool = False
    created_at: str


class NotificationsResponse(BaseModel):
    notifications: List[NotificationItem]
    unread_count: int


# ── Player Profile (Expanded) ──

class PlayerProfileResponse(BaseModel):
    full_name: str
    email: str
    total_games: int
    total_stars: int
    average_accuracy: float
    current_streak: int
    longest_streak: int
    best_accuracy: float
    best_time: Optional[int] = None
    best_moves: Optional[int] = None
    favorite_language: Optional[str] = None
    favorite_difficulty: Optional[str] = None

    # Gamification fields
    level: int = 1
    current_xp: int = 0
    xp_for_next: int = 250
    rank_name: str = "Beginner"
    rank_icon: str = "star"
    total_achievements: int = 0
    unlocked_achievements: int = 0
    total_badges: int = 0
    unlocked_badges: int = 0
    xp_progress_percent: float = 0


# ══════════════════════════════════════════════
# Phase 24: Tech Logo Match (Placeholder)
# ══════════════════════════════════════════════


