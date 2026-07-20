import secrets
from datetime import datetime
from fastapi import APIRouter, HTTPException, Response, Request, Depends
from app.config import settings
from app.schemas.auth import (
    RegisterRequest, LoginRequest, ForgotPasswordRequest,
    ResetPasswordRequest, RefreshTokenRequest, MessageResponse,
)
from app.services.auth_service import AuthService
from app.middleware.auth import get_current_user
from app.middleware.rate_limit import auth_rate_limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()


def _sanitize_user(user: dict) -> dict:
    user.pop("password_hash", None)
    user.pop("reset_token", None)
    user.pop("reset_token_expires", None)
    user.pop("verification_token", None)
    user["id"] = user.pop("_id", "")
    return user


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, request: Request):
    auth_rate_limiter.check(request)
    try:
        result = await auth_service.register(
            full_name=body.full_name,
            email=body.email,
            password=body.password,
            company=body.company,
        )
        user = await auth_service.get_current_user(result["user_id"])
        return {**result, "user": _sanitize_user(user) if user else None}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(body: LoginRequest, response: Response, request: Request):
    auth_rate_limiter.check(request)
    try:
        result = await auth_service.login(
            email=body.email,
            password=body.password,
            remember_me=body.remember_me,
        )
        user = await auth_service.get_current_user(result["user_id"])
        response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax",
            max_age=7 * 24 * 60 * 60,
            path="/",
        )
        result.pop("refresh_token", None)
        return {**result, "user": _sanitize_user(user) if user else None}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    response.delete_cookie("refresh_token", path="/")
    return MessageResponse(message="Logged out successfully")


@router.post("/refresh")
async def refresh(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except Exception:
            pass
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token required")
    try:
        result = await auth_service.refresh_token(refresh_token)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"user": _sanitize_user(current_user)}


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    auth_rate_limiter.check(request)
    token = await auth_service.forgot_password(body.email)
    if token:
        return MessageResponse(message=f"Reset token generated (dev mode): {token}")
    return MessageResponse(message="If an account with this email exists, a reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, request: Request):
    auth_rate_limiter.check(request)
    try:
        await auth_service.reset_password(token=body.token, new_password=body.password)
        return MessageResponse(message="Password reset successfully")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/send-verification", response_model=MessageResponse)
async def send_verification(current_user: dict = Depends(get_current_user)):
    if current_user.get("email_verified"):
        return MessageResponse(message="Email already verified")
    token = secrets.token_urlsafe(48)
    from app.repositories.user_repository import UserRepository
    repo = UserRepository()
    await repo.update_by_id(current_user["_id"], {"verification_token": token})
    return MessageResponse(message=f"Verification token generated (dev mode): {token}")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(body: dict):
    token = body.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Verification token required")
    from app.repositories.user_repository import UserRepository
    repo = UserRepository()
    user = await repo.find_by_id(body.get("user_id", ""))
    if not user or user.get("verification_token") != token:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    await repo.update_by_id(user["_id"], {
        "email_verified": True,
        "verification_token": None,
    })
    return MessageResponse(message="Email verified successfully")
