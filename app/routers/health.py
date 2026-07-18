from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "India Web Programmers API"}


@router.get("/protected-test")
async def protected_test(current_user: dict = Depends(get_current_user)):
    return {"message": f"Hello {current_user['full_name']}, you are authenticated!", "user_id": current_user["_id"]}
