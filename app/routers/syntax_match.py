from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import Optional
from app.middleware.auth import get_current_user, get_optional_user
from app.schemas.syntax_match import (
    FinishGameRequest,
    FinishGameResponse,
    GameHistoryResponse,
    GameHistoryItem,
    StatisticsResponse,
    ProfileResponse,
    DashboardResponse,
    SaveSettingsRequest,
    SettingsResponse,
    AnalyticsResponse,
    ExportResponse,
    PlayerProfileResponse,
)
from app.services.syntax_match_service import syntax_match_service
from app.database import get_db

router = APIRouter(prefix="/v1/syntax-match", tags=["Syntax Match"])


@router.post("/games", response_model=FinishGameResponse)
async def finish_game(
    body: FinishGameRequest,
    current_user: dict = Depends(get_current_user),
):
    """Save a completed game for the authenticated user."""
    data = body.model_dump()
    result = await syntax_match_service.save_game(current_user["_id"], data)
    return FinishGameResponse(**result)


@router.get("/history", response_model=GameHistoryResponse)
async def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    language: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None, pattern="^(easy|medium|hard)$"),
    sort_by: str = Query("created_at", pattern="^(created_at|accuracy|moves|stars|completion_time_seconds)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: dict = Depends(get_current_user),
):
    """Get paginated game history with optional filters."""
    result = await syntax_match_service.get_history(
        current_user["_id"],
        page=page,
        limit=limit,
        language=language,
        difficulty=difficulty,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return GameHistoryResponse(**result)


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    current_user: dict = Depends(get_current_user),
):
    """Get aggregated player statistics."""
    stats = await syntax_match_service.get_statistics(current_user["_id"])
    return StatisticsResponse(**stats)


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: dict = Depends(get_current_user),
):
    """Get full player dashboard with recent games."""
    dashboard = await syntax_match_service.get_dashboard(current_user["_id"])
    return DashboardResponse(**dashboard)


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: dict = Depends(get_current_user),
):
    """Get player profile with aggregate stats."""
    profile = await syntax_match_service.get_profile(current_user["_id"], current_user)
    return ProfileResponse(**profile)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    current_user: dict = Depends(get_current_user),
):
    """Get player settings."""
    settings = await syntax_match_service.get_settings(current_user["_id"])
    return SettingsResponse(**settings)


@router.put("/settings", response_model=SettingsResponse)
async def save_settings(
    body: SaveSettingsRequest,
    current_user: dict = Depends(get_current_user),
):
    """Save player settings."""
    data = body.model_dump(exclude_none=True)
    settings = await syntax_match_service.save_settings(current_user["_id"], data)
    return SettingsResponse(**settings)


@router.get("/health")
async def health_check():
    collections = [
        "syntax_match_games",
        "syntax_match_statistics",
        "syntax_match_settings",
    ]
    return {
        "status": "ok",
        "module": "Syntax Match API v1",
        "collections": collections,
    }


# ══════════════════════════════════════════════
# Phase 21: Analytics Endpoints
# ══════════════════════════════════════════════


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    current_user: dict = Depends(get_current_user),
):
    """Comprehensive analytics for the player."""
    result = await syntax_match_service.get_analytics(current_user["_id"])
    return AnalyticsResponse(**result)


@router.get("/analytics/export")
async def export_analytics(
    format: str = Query("csv", pattern="^(csv|json)$"),
    current_user: dict = Depends(get_current_user),
):
    """Export analytics data as CSV or JSON."""
    content = await syntax_match_service.export_analytics(current_user["_id"], format)
    media_type = "text/csv" if format == "csv" else "application/json"
    filename = f"syntax-match-analytics.{format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ══════════════════════════════════════════════
# Phase 22: Gamification Endpoints
# ══════════════════════════════════════════════


# ── Player Profile (Expanded) ──
@router.get("/profile", response_model=PlayerProfileResponse)
async def get_player_profile(
    current_user: dict = Depends(get_current_user),
):
    """Get expanded player profile with XP, level, rank, achievements."""
    profile = await syntax_match_service.get_player_profile(current_user["_id"], current_user)
    return PlayerProfileResponse(**profile)


# ── XP & Levels ──
@router.post("/xp/daily-login")
async def award_daily_login_xp(
    current_user: dict = Depends(get_current_user),
):
    """Award daily login XP bonus."""
    return await syntax_match_service.award_daily_login_xp(current_user["_id"])


@router.get("/xp/level")
async def get_player_level(
    current_user: dict = Depends(get_current_user),
):
    """Get current level and XP info."""
    db = get_db()
    level_data = await db.syntax_match_levels.find_one({"user_id": current_user["_id"]})
    if not level_data:
        return {"level": 1, "current_xp": 0, "xp_for_next": 250, "rank": "Beginner", "progress_percent": 0}
    return {
        "level": level_data["level"],
        "current_xp": level_data["current_xp"],
        "xp_for_next": level_data["xp_for_next"],
        "rank": level_data["rank"],
        "progress_percent": round(
            (level_data["current_xp"] / level_data["xp_for_next"]) * 100, 1
        ) if level_data["xp_for_next"] else 100,
    }


# ── Achievements ──
@router.get("/achievements")
async def get_achievements(
    current_user: dict = Depends(get_current_user),
):
    """Get all achievements with progress and unlock status."""
    return await syntax_match_service.get_achievements(current_user["_id"])


# ── Badges ──
@router.get("/badges")
async def get_badges(
    current_user: dict = Depends(get_current_user),
):
    """Get all badges with unlock status."""
    return await syntax_match_service.get_badges(current_user["_id"])


# ── Leaderboards ──
@router.get("/leaderboard")
async def get_leaderboard(
    metric: str = Query("xp", pattern="^(xp|games|accuracy|streak)$"),
    scope: str = Query("overall", pattern="^(overall|html|css|javascript|react|next\\.js|typescript|angular|vue|dart|easy|medium|hard)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """Get leaderboard entries by metric and scope."""
    return await syntax_match_service.get_leaderboard(
        metric=metric, scope=scope, page=page, limit=limit,
    )


@router.get("/leaderboard/my-rank")
async def get_my_rank(
    current_user: dict = Depends(get_current_user),
):
    """Get current player's rank."""
    return await syntax_match_service.get_player_rank(current_user["_id"])


# ── Daily Challenge ──
@router.get("/challenges/daily")
async def get_daily_challenge(
    current_user: dict = Depends(get_current_user),
):
    """Get today's daily challenge."""
    return await syntax_match_service.get_daily_challenge(current_user["_id"])


# ── Weekly Challenge ──
@router.get("/challenges/weekly")
async def get_weekly_challenge(
    current_user: dict = Depends(get_current_user),
):
    """Get this week's weekly challenge."""
    return await syntax_match_service.get_weekly_challenge(current_user["_id"])


# ── Challenge History ──
@router.get("/challenges/history")
async def get_challenge_history(
    current_user: dict = Depends(get_current_user),
):
    """Get challenge completion history."""
    return await syntax_match_service.get_challenge_history(current_user["_id"])


# ── Rewards ──
@router.get("/rewards")
async def get_rewards(
    current_user: dict = Depends(get_current_user),
):
    """Get recent rewards and total XP earned."""
    return await syntax_match_service.get_rewards(current_user["_id"])


# ── Notifications ──
@router.get("/notifications")
async def get_notifications(
    current_user: dict = Depends(get_current_user),
):
    """Get in-app notifications."""
    return await syntax_match_service.get_notifications(current_user["_id"])


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Mark a notification as read."""
    result = await syntax_match_service.mark_notification_read(current_user["_id"], notification_id)
    return {"success": result}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user),
):
    """Mark all notifications as read."""
    result = await syntax_match_service.mark_all_notifications_read(current_user["_id"])
    return {"success": result, "count": result}
