from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.middleware.auth import get_current_user
from app.middleware.rate_limit import rate_limiter
from app.schemas.gamification import (
    LeaderboardResponse, UserRankResponse, DailyChallengesResponse,
    WeeklyChallengesResponse, ChallengeCompleteRequest, ChallengeCompleteResponse,
    AchievementsListResponse, XPInfoResponse, StreakResponse, GamificationProfileResponse,
)
from app.services.gamification_service import gamification_service
from app.services.leaderboard_service import leaderboard_service
from app.services.challenge_service import challenge_service

router = APIRouter(prefix="/codesprint", tags=["CodeSprint Gamification"])


@router.get("/leaderboard")
async def get_leaderboard(
    current_user: dict = Depends(get_current_user),
    period: str = Query("all_time"),
    language: Optional[str] = Query(None),
    metric: str = Query("xp"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    result = await leaderboard_service.get_leaderboard(
        period=period, language=language, metric=metric, page=page, limit=limit,
    )
    return result


@router.get("/leaderboard/me")
async def get_my_rank(
    current_user: dict = Depends(get_current_user),
    metric: str = Query("xp"),
):
    result = await leaderboard_service.get_user_rank(current_user["_id"], metric=metric)
    return result


@router.get("/challenges/daily")
async def get_daily_challenges(
    current_user: dict = Depends(get_current_user),
):
    result = await challenge_service.get_daily_challenges(current_user["_id"])
    return result


@router.get("/challenges/weekly")
async def get_weekly_challenges(
    current_user: dict = Depends(get_current_user),
):
    result = await challenge_service.get_weekly_challenges(current_user["_id"])
    return result


@router.post("/challenges/complete")
async def complete_challenge(
    body: ChallengeCompleteRequest,
    current_user: dict = Depends(get_current_user),
):
    result = await challenge_service.complete_challenge(
        current_user["_id"], body.challenge_id, body.challenge_type,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/achievements")
async def get_achievements(
    current_user: dict = Depends(get_current_user),
):
    result = await gamification_service.get_achievements(current_user["_id"])
    return result


@router.get("/gamification/xp")
async def get_xp_info(
    current_user: dict = Depends(get_current_user),
):
    result = await gamification_service.get_user_xp(current_user["_id"])
    return result


@router.get("/gamification/streak")
async def get_streak(
    current_user: dict = Depends(get_current_user),
):
    result = await gamification_service.get_streak(current_user["_id"])
    return result


@router.get("/gamification/profile")
async def get_gamification_profile(
    current_user: dict = Depends(get_current_user),
):
    result = await gamification_service.get_gamification_profile(current_user["_id"], current_user)
    rank_info = await leaderboard_service.get_user_rank(current_user["_id"], metric="xp")
    result["rank"] = rank_info.get("current_rank")
    result["top_percentage"] = rank_info.get("top_percentage")
    return result


@router.post("/gamification/daily-login")
async def claim_daily_login_xp(
    current_user: dict = Depends(get_current_user),
):
    result = await gamification_service.award_daily_login_xp(current_user["_id"])
    if not result.get("success", True):
        return result
    new_achievements = await gamification_service.check_and_award_achievements(current_user["_id"])
    result["achievements_unlocked"] = new_achievements
    return result
