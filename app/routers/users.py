from fastapi import APIRouter, HTTPException, Request, Depends
from app.schemas.user import UserProfileUpdate, UserSettingsUpdate, ChangePasswordRequest
from app.services.user_service import UserService
from app.middleware.auth import get_current_user
from app.middleware.rate_limit import rate_limiter

router = APIRouter(prefix="/users", tags=["Users"])
user_service = UserService()


def _sanitize_user(user: dict) -> dict:
    user.pop("password_hash", None)
    user.pop("reset_token", None)
    user.pop("reset_token_expires", None)
    user.pop("verification_token", None)
    user["id"] = user.pop("_id", "")
    return user


@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    return {"user": _sanitize_user(current_user)}


@router.put("/profile")
async def update_profile(body: UserProfileUpdate, current_user: dict = Depends(get_current_user)):
    update_data = body.model_dump(exclude_unset=True)
    user = await user_service.update_profile(current_user["_id"], update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": _sanitize_user(user)}


@router.patch("/update-profile")
async def update_profile_partial(body: UserProfileUpdate, current_user: dict = Depends(get_current_user)):
    update_data = body.model_dump(exclude_unset=True)
    user = await user_service.update_profile(current_user["_id"], update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": _sanitize_user(user)}


@router.put("/settings")
async def update_settings(body: UserSettingsUpdate, current_user: dict = Depends(get_current_user)):
    update_data = body.model_dump(exclude_unset=True)
    user = await user_service.update_settings(current_user["_id"], update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": _sanitize_user(user)}


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, request: Request, current_user: dict = Depends(get_current_user)):
    rate_limiter.check(request)
    try:
        await user_service.change_password(
            user_id=current_user["_id"],
            current_password=body.current_password,
            new_password=body.new_password,
        )
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
