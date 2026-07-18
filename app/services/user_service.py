from typing import Optional
from app.repositories.user_repository import UserRepository
from app.utils.security import verify_password, hash_password


class UserService:
    def __init__(self):
        self.user_repo = UserRepository()

    async def get_profile(self, user_id: str) -> Optional[dict]:
        user = await self.user_repo.find_by_id(user_id)
        if user:
            user.pop("password_hash", None)
            user.pop("reset_token", None)
            user.pop("reset_token_expires", None)
            user.pop("verification_token", None)
        return user

    async def update_profile(self, user_id: str, update_data: dict) -> Optional[dict]:
        allowed_fields = {"full_name", "phone", "company", "bio", "avatar", "social_links"}
        filtered = {k: v for k, v in update_data.items() if k in allowed_fields and v is not None}
        if not filtered:
            return await self.get_profile(user_id)
        await self.user_repo.update_by_id(user_id, filtered)
        return await self.get_profile(user_id)

    async def update_settings(self, user_id: str, update_data: dict) -> Optional[dict]:
        allowed_fields = {"theme_preference", "timezone", "language", "notification_settings"}
        filtered = {k: v for k, v in update_data.items() if k in allowed_fields and v is not None}
        if not filtered:
            return await self.get_profile(user_id)
        await self.user_repo.update_by_id(user_id, filtered)
        return await self.get_profile(user_id)

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        if not verify_password(current_password, user["password_hash"]):
            raise ValueError("Current password is incorrect")
        await self.user_repo.update_by_id(user_id, {"password_hash": hash_password(new_password)})
        return True
