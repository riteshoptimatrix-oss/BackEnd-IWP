from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.middleware.auth import get_current_user
from app.database import get_db
from app.schemas.codesprint import (
    FinishSessionRequest,
    FinishSessionResponse,
    HistoryResponse,
    StatisticsResponse,
    ProfileResponse,
    LanguagesResponse,
    LanguageResponse,
)
from app.services.codesprint_service import codesprint_service

router = APIRouter(prefix="/codesprint", tags=["CodeSprint"])

SUPPORTED_LANGUAGES = [
    {"id": "html", "name": "HTML", "color": "#E34F26", "description": "Semantic markup and accessibility."},
    {"id": "css", "name": "CSS", "color": "#1572B6", "description": "Flexbox, Grid, animations, and responsive design."},
    {"id": "javascript", "name": "JavaScript", "color": "#F7DF1E", "description": "ES2024+, async/await, and modern patterns."},
    {"id": "react", "name": "React", "color": "#61DAFB", "description": "Components, hooks, state management, and JSX."},
    {"id": "nextjs", "name": "Next.js", "color": "#000000", "description": "App Router, server components, full-stack."},
    {"id": "typescript", "name": "TypeScript", "color": "#3178C6", "description": "Type safety, generics, utility types."},
    {"id": "dart", "name": "Dart", "color": "#0175C2", "description": "Flutter-ready syntax, null safety."},
    {"id": "angular", "name": "Angular", "color": "#DD0031", "description": "Components, services, decorators, RxJS."},
    {"id": "vue", "name": "Vue", "color": "#4FC08D", "description": "Composition API, reactivity, SFC."},
]


@router.get("/languages", response_model=LanguagesResponse)
async def get_languages():
    return LanguagesResponse(
        languages=[LanguageResponse(**lang) for lang in SUPPORTED_LANGUAGES]
    )


@router.post("/finish", response_model=FinishSessionResponse)
async def finish_session(
    body: FinishSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    data = body.model_dump()
    result = await codesprint_service.finish_session(current_user["_id"], data)
    return FinishSessionResponse(**result)


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    language: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    result = await codesprint_service.get_history(
        current_user["_id"], page=page, limit=limit,
        language=language, difficulty=difficulty, category=category,
    )
    return HistoryResponse(**result)


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    current_user: dict = Depends(get_current_user),
):
    result = await codesprint_service.get_statistics(current_user["_id"])
    return StatisticsResponse(**result)


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: dict = Depends(get_current_user),
):
    result = await codesprint_service.get_profile(current_user["_id"], current_user)
    return ProfileResponse(**result)


@router.get("/recent")
async def get_recent(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(5, ge=1, le=20),
):
    result = await codesprint_service.get_history(
        current_user["_id"], page=1, limit=limit,
    )
    return {"sessions": result["sessions"]}
