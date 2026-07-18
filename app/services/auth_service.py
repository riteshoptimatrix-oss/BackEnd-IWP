from datetime import datetime
from typing import Optional
from app.repositories.user_repository import UserRepository
from app.utils.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_refresh_token, generate_reset_token,
)


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()

    async def register(self, full_name: str, email: str, password: str, company: Optional[str] = None) -> dict:
        existing = await self.user_repo.find_by_email(email)
        if existing:
            raise ValueError("An account with this email already exists")

        user_data = {
            "full_name": full_name.strip(),
            "email": email.lower().strip(),
            "password_hash": hash_password(password),
            "company": company,
            "role": "user",
            "email_verified": False,
            "two_factor_enabled": False,
            "account_status": "active",
            "theme_preference": "system",
            "notification_settings": {
                "email_notifications": True,
                "project_updates": True,
                "ai_reports": True,
                "security_alerts": True,
                "marketing": False,
            },
            "timezone": "UTC",
            "language": "en",
            "social_links": {"twitter": "", "linkedin": "", "github": "", "website": ""},
        }
        user_id = await self.user_repo.create(user_data)
        tokens = self._create_tokens(user_id, email)
        return {"user_id": user_id, "email": email, **tokens}

    async def login(self, email: str, password: str, remember_me: bool = False) -> dict:
        user = await self.user_repo.find_by_email(email)
        if not user:
            raise ValueError("Invalid email or password")

        if not verify_password(password, user["password_hash"]):
            raise ValueError("Invalid email or password")

        if user.get("account_status") != "active":
            raise ValueError("Account is not active")

        await self.user_repo.update_last_login(user["_id"])

        access_expires = 60 * 24 * 7 if remember_me else 30
        tokens = self._create_tokens(user["_id"], email, access_minutes=access_expires)
        return {
            "user_id": user["_id"],
            "email": email,
            "full_name": user["full_name"],
            "avatar": user.get("avatar"),
            **tokens,
        }

    async def refresh_token(self, refresh_token: str) -> dict:
        payload = decode_refresh_token(refresh_token)
        if not payload:
            raise ValueError("Invalid or expired refresh token")

        user = await self.user_repo.find_by_id(payload.get("sub"))
        if not user:
            raise ValueError("User not found")

        tokens = self._create_tokens(user["_id"], user["email"])
        return {"user_id": user["_id"], "email": user["email"], **tokens}

    async def forgot_password(self, email: str) -> str:
        user = await self.user_repo.find_by_email(email)
        if not user:
            return "If an account with this email exists, a reset link has been sent"

        token = generate_reset_token()
        await self.user_repo.update_by_id(user["_id"], {
            "reset_token": token,
            "reset_token_expires": datetime.utcnow(),
        })
        return token

    async def reset_password(self, token: str, new_password: str) -> bool:
        user = await self.user_repo.find_by_reset_token(token)
        if not user:
            raise ValueError("Invalid or expired reset token")

        await self.user_repo.update_by_id(user["_id"], {
            "password_hash": hash_password(new_password),
            "reset_token": None,
            "reset_token_expires": None,
        })
        return True

    async def get_current_user(self, user_id: str) -> Optional[dict]:
        return await self.user_repo.find_by_id(user_id)

    def _create_tokens(self, user_id: str, email: str, access_minutes: int = 30) -> dict:
        from datetime import timedelta
        access_token = create_access_token(
            {"sub": user_id, "email": email},
            expires_delta=timedelta(minutes=access_minutes),
        )
        refresh_token = create_refresh_token(
            {"sub": user_id, "email": email},
            expires_delta=timedelta(days=7),
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": access_minutes * 60,
        }
