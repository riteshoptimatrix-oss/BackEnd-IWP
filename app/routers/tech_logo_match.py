from fastapi import APIRouter, Depends, HTTPException, Query
from app.middleware.auth import get_current_user, get_optional_user
from app.schemas.tech_logo_match import (
    FinishGameRequest,
    FinishGameResponse,
    GameHistoryResponse,
    StatisticsResponse,
    ProfileResponse,
    SaveSettingsRequest,
    SettingsResponse,
    DashboardResponse,
    AnalyticsResponse,
    LevelInfo,
    LeaderboardResponse,
    PlayerRankResponse,
    DailyChallengeResponse,
    WeeklyChallengeResponse,
    ChallengeHistoryResponse,
    RewardsResponse,
    NotificationsResponse,
    PlayerProfileResponse,
)
from fastapi.responses import PlainTextResponse, Response
from app.services.tech_logo_match_service import tech_logo_match_service

router = APIRouter(prefix="/v1/tech-logo-match", tags=["Tech Logo Match"])


@router.get("/health")
async def health_check():
    return await tech_logo_match_service.health_check()


@router.post("/games", response_model=FinishGameResponse)
async def finish_game(
    body: FinishGameRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.save_game(user_id, body.model_dump())


@router.get("/games", response_model=GameHistoryResponse)
async def get_game_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    search: str = Query("", max_length=100),
    sort_by: str = Query("created_at", pattern="^(score|accuracy|stars|created_at|duration_seconds)$"),
    sort_order: int = Query(-1, ge=-1, le=1),
    difficulty: str = Query("", max_length=20),
    mode: str = Query("", max_length=50),
    category: str = Query("", max_length=50),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_game_history(
        user_id, page, limit, search, sort_by, sort_order,
        difficulty, mode, category,
    )


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_statistics(user_id)


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_dashboard(user_id)


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_profile(user_id, current_user)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_settings(user_id)


@router.put("/settings", response_model=SettingsResponse)
async def save_settings(
    body: SaveSettingsRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.save_settings(
        user_id, body.model_dump(exclude_none=True)
    )


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_analytics(user_id)


@router.get("/analytics/export")
async def export_analytics(
    format: str = Query("csv", pattern="^(csv|json)$"),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    content = await tech_logo_match_service.export_analytics(user_id, format)
    if format == "csv":
        return PlainTextResponse(
            content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=tech-logo-match-analytics.csv"},
        )
    return Response(
        content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=tech-logo-match-analytics.json"},
    )


# ══════════════════════════════════════════════════
# GAMIFICATION ENDPOINTS
# ══════════════════════════════════════════════════

@router.get("/xp/level", response_model=LevelInfo)
async def get_player_level(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_player_level(user_id)


@router.post("/xp/daily-login")
async def award_daily_login_xp(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.award_daily_login_xp(user_id)


@router.get("/achievements")
async def get_achievements(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_achievements(user_id)


@router.get("/badges")
async def get_badges(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_badges(user_id)


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    metric: str = Query("xp", pattern="^(xp|accuracy|streak|score|games)$"),
    scope: str = Query("overall", max_length=50),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_leaderboard(user_id, metric, scope, page, limit)


@router.get("/leaderboard/my-rank", response_model=PlayerRankResponse)
async def get_my_rank(
    metric: str = Query("xp", pattern="^(xp|accuracy|streak|score|games)$"),
    scope: str = Query("overall", max_length=50),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_player_rank(user_id, metric, scope)


@router.get("/daily-challenge", response_model=DailyChallengeResponse)
async def get_daily_challenge(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_daily_challenge(user_id)


@router.get("/weekly-challenge", response_model=WeeklyChallengeResponse)
async def get_weekly_challenge(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_weekly_challenge(user_id)


@router.get("/challenge-history", response_model=ChallengeHistoryResponse)
async def get_challenge_history(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    challenges = await tech_logo_match_service.get_challenge_history(user_id)
    return {"challenges": challenges, "total": len(challenges)}


@router.get("/rewards", response_model=RewardsResponse)
async def get_rewards(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_rewards(user_id)


@router.get("/notifications", response_model=NotificationsResponse)
async def get_notifications(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_notifications(user_id)


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
):
    result = await tech_logo_match_service.mark_notification_read(notification_id)
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "ok"}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    count = await tech_logo_match_service.mark_all_notifications_read(user_id)
    return {"status": "ok", "marked_read": count}


@router.get("/player-profile", response_model=PlayerProfileResponse)
async def get_player_profile(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return await tech_logo_match_service.get_player_profile(user_id, current_user)
