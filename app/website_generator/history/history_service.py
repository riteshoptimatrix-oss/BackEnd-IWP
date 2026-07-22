from typing import List, Dict, Any
from app.database import get_db

class HistoryService:
    """
    Manages audit trail logs in MongoDB generation_history collection.
    """
    @staticmethod
    async def get_user_history(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        db = get_db()
        cursor = db.generation_history.find({"user_id": str(user_id)}).sort("created_at", -1).limit(limit)
        items = []
        async for doc in cursor:
            items.append({
                "id": str(doc["_id"]),
                "job_id": doc.get("job_id", ""),
                "company_name": doc.get("company_name", ""),
                "website_type": doc.get("website_type", ""),
                "theme": doc.get("theme", ""),
                "selected_features": doc.get("selected_features", []),
                "status": doc.get("status", "COMPLETED"),
                "created_at": doc.get("created_at", "").isoformat() if hasattr(doc.get("created_at"), "isoformat") else str(doc.get("created_at", "")),
            })
        return items
