from fastapi import Depends, Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.security import decode_access_token
from app.repositories.user_repository import UserRepository

security = HTTPBearer(auto_error=False)
user_repo = UserRepository()


async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

    user = await user_repo.find_by_id(payload.get("sub"))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.get("account_status") != "active":
        raise HTTPException(status_code=403, detail="Account is not active")

    user.pop("password_hash", None)
    user.pop("reset_token", None)
    user.pop("reset_token_expires", None)
    user.pop("verification_token", None)
    return user


async def get_optional_user(request: Request) -> dict | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    try:
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        if not payload:
            return None
        user = await user_repo.find_by_id(payload.get("sub"))
        if user:
            user.pop("password_hash", None)
        return user
    except Exception:
        return None
