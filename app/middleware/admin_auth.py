from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.security import decode_access_token
from app.repositories.user_repository import UserRepository

security = HTTPBearer()
user_repo = UserRepository()

ADMIN_ROLES = {"super_admin", "admin", "moderator", "content_manager", "support"}
WRITE_ROLES = {"super_admin", "admin", "moderator", "content_manager"}
SUPER_ADMIN_ROLES = {"super_admin"}
MODERATOR_ROLES = {"super_admin", "admin", "moderator"}


async def get_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

    user = await user_repo.find_by_id(payload.get("sub"))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.get("account_status") != "active":
        raise HTTPException(status_code=403, detail="Account is not active")

    role = user.get("role", "user")
    if role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")

    user.pop("password_hash", None)
    user.pop("reset_token", None)
    user.pop("reset_token_expires", None)
    user.pop("verification_token", None)
    return user


async def get_write_admin(
    current_user: dict = Depends(get_admin_user),
) -> dict:
    role = current_user.get("role", "user")
    if role not in WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Write admin access required")
    return current_user


async def get_super_admin(
    current_user: dict = Depends(get_admin_user),
) -> dict:
    role = current_user.get("role", "user")
    if role not in SUPER_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user


async def get_moderator_plus(
    current_user: dict = Depends(get_admin_user),
) -> dict:
    role = current_user.get("role", "user")
    if role not in MODERATOR_ROLES:
        raise HTTPException(status_code=403, detail="Moderator access or higher required")
    return current_user


def require_roles(*allowed_roles):
    async def role_checker(
        current_user: dict = Depends(get_admin_user),
    ) -> dict:
        role = current_user.get("role", "user")
        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Required roles: {', '.join(allowed_roles)}",
            )
        return current_user
    return role_checker
