from datetime import datetime
from typing import Optional
from bson import ObjectId
from app.database import get_db
from app.models.user import UserDocument


class UserRepository:
    @property
    def collection(self):
        return get_db().users

    async def create(self, user_data: dict) -> str:
        user_data["created_at"] = datetime.utcnow()
        user_data["updated_at"] = datetime.utcnow()
        result = await self.collection.insert_one(user_data)
        return str(result.inserted_id)

    async def find_by_email(self, email: str) -> Optional[dict]:
        user = await self.collection.find_one({"email": email.lower()})
        if user:
            user["_id"] = str(user["_id"])
        return user

    async def find_by_id(self, user_id: str) -> Optional[dict]:
        try:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
            return user
        except Exception:
            return None

    async def find_by_reset_token(self, token: str) -> Optional[dict]:
        user = await self.collection.find_one({"reset_token": token})
        if user:
            user["_id"] = str(user["_id"])
        return user

    async def update_by_id(self, user_id: str, update_data: dict) -> bool:
        update_data["updated_at"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def update_last_login(self, user_id: str) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_login": datetime.utcnow(), "updated_at": datetime.utcnow()}}
        )

    async def count_users(self) -> int:
        return await self.collection.count_documents({})
