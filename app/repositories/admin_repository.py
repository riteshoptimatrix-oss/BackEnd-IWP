from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId
from app.database import get_db


class AdminRepository:
    @property
    def db(self):
        return get_db()

    # ─── User Operations ──────────────────────────────────────────

    async def get_users(
        self, page: int = 1, limit: int = 20, search: Optional[str] = None,
        role: Optional[str] = None, status: Optional[str] = None,
        sort_by: str = "created_at", sort_order: str = "desc",
    ) -> dict:
        query: Dict[str, Any] = {}
        if search:
            query["$or"] = [
                {"full_name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
            ]
        if role:
            query["role"] = role
        if status:
            query["account_status"] = status

        total = await self.db.users.count_documents(query)
        skip = (page - 1) * limit
        sort_dir = -1 if sort_order == "desc" else 1

        cursor = self.db.users.find(query).sort(sort_by, sort_dir).skip(skip).limit(limit)
        users = []
        async for user in cursor:
            user["_id"] = str(user["_id"])
            user.pop("password_hash", None)
            user.pop("reset_token", None)
            user.pop("reset_token_expires", None)
            user.pop("verification_token", None)
            users.append(user)

        return {
            "users": users,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": max(1, (total + limit - 1) // limit),
        }

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        try:
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
                user.pop("password_hash", None)
                user.pop("reset_token", None)
                user.pop("reset_token_expires", None)
                user.pop("verification_token", None)
            return user
        except Exception:
            return None

    async def update_user(self, user_id: str, update_data: dict) -> bool:
        update_data["updated_at"] = datetime.utcnow()
        result = await self.db.users.update_one(
            {"_id": ObjectId(user_id)}, {"$set": update_data}
        )
        return result.modified_count > 0

    async def delete_user(self, user_id: str) -> bool:
        result = await self.db.users.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0

    async def count_users(self, query: dict = None) -> int:
        return await self.db.users.count_documents(query or {})

    async def count_active_users_today(self) -> int:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return await self.db.users.count_documents({"last_login": {"$gte": today}})

    async def count_new_registrations(self, days: int = 7) -> int:
        since = datetime.utcnow() - timedelta(days=days)
        return await self.db.users.count_documents({"created_at": {"$gte": since}})

    # ─── Session Statistics ────────────────────────────────────────

    async def count_sessions(self, query: dict = None) -> int:
        return await self.db.codesprint_sessions.count_documents(query or {})

    async def get_average_stats(self) -> dict:
        pipeline = [
            {"$match": {"finished": True}},
            {"$group": {
                "_id": None,
                "avg_accuracy": {"$avg": "$accuracy"},
                "avg_wpm": {"$avg": "$wpm"},
                "total_sessions": {"$sum": 1},
            }},
        ]
        result = await self.db.codesprint_sessions.aggregate(pipeline).to_list(1)
        if result:
            return {
                "average_accuracy": round(result[0].get("avg_accuracy", 0), 2),
                "average_wpm": round(result[0].get("avg_wpm", 0), 2),
                "total_sessions": result[0].get("total_sessions", 0),
            }
        return {"average_accuracy": 0, "average_wpm": 0, "total_sessions": 0}

    async def get_language_distribution(self) -> list:
        pipeline = [
            {"$group": {"_id": "$language", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 20},
        ]
        result = await self.db.codesprint_sessions.aggregate(pipeline).to_list(20)
        return [{"language": r["_id"], "count": r["count"]} for r in result]

    async def get_user_growth(self, days: int = 30) -> list:
        since = datetime.utcnow() - timedelta(days=days)
        pipeline = [
            {"$match": {"created_at": {"$gte": since}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ]
        result = await self.db.users.aggregate(pipeline).to_list(days + 1)
        return [{"date": r["_id"], "count": r["count"]} for r in result]

    async def get_activity_data(self, days: int = 30) -> list:
        since = datetime.utcnow() - timedelta(days=days)
        pipeline = [
            {"$match": {"created_at": {"$gte": since}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "sessions": {"$sum": 1},
                "unique_users": {"$addToSet": "$user_id"},
            }},
            {"$sort": {"_id": 1}},
            {"$project": {
                "date": "$_id",
                "sessions": 1,
                "unique_users": {"$size": "$unique_users"},
            }},
        ]
        result = await self.db.codesprint_sessions.aggregate(pipeline).to_list(days + 1)
        return result

    # ─── Snippet Operations ────────────────────────────────────────

    async def get_snippets(
        self, page: int = 1, limit: int = 20, language: Optional[str] = None,
        difficulty: Optional[str] = None, search: Optional[str] = None,
    ) -> dict:
        query: Dict[str, Any] = {}
        if language:
            query["language"] = language
        if difficulty:
            query["difficulty"] = difficulty
        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"content": {"$regex": search, "$options": "i"}},
            ]

        total = await self.db.codesprint_snippets.count_documents(query)
        skip = (page - 1) * limit
        cursor = self.db.codesprint_snippets.find(query).skip(skip).limit(limit)
        snippets = []
        async for s in cursor:
            s["_id"] = str(s["_id"])
            snippets.append(s)

        return {
            "snippets": snippets,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": max(1, (total + limit - 1) // limit),
        }

    async def create_snippet(self, data: dict) -> str:
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        result = await self.db.codesprint_snippets.insert_one(data)
        return str(result.inserted_id)

    async def update_snippet(self, snippet_id: str, update_data: dict) -> bool:
        update_data["updated_at"] = datetime.utcnow()
        result = await self.db.codesprint_snippets.update_one(
            {"_id": ObjectId(snippet_id)}, {"$set": update_data}
        )
        return result.modified_count > 0

    async def delete_snippet(self, snippet_id: str) -> bool:
        result = await self.db.codesprint_snippets.delete_one({"_id": ObjectId(snippet_id)})
        return result.deleted_count > 0

    async def bulk_create_snippets(self, snippets: list) -> int:
        for s in snippets:
            s["created_at"] = datetime.utcnow()
            s["updated_at"] = datetime.utcnow()
        result = await self.db.codesprint_snippets.insert_many(snippets)
        return len(result.inserted_ids)

    # ─── Category Operations ───────────────────────────────────────

    async def get_categories(self, language: Optional[str] = None) -> list:
        query = {}
        if language:
            query["language"] = language
        cursor = self.db.snippet_categories.find(query).sort("sort_order", 1)
        cats = []
        async for c in cursor:
            c["_id"] = str(c["_id"])
            cats.append(c)
        return cats

    async def create_category(self, data: dict) -> str:
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        result = await self.db.snippet_categories.insert_one(data)
        return str(result.inserted_id)

    async def update_category(self, cat_id: str, update_data: dict) -> bool:
        update_data["updated_at"] = datetime.utcnow()
        result = await self.db.snippet_categories.update_one(
            {"_id": ObjectId(cat_id)}, {"$set": update_data}
        )
        return result.modified_count > 0

    async def delete_category(self, cat_id: str) -> bool:
        result = await self.db.snippet_categories.delete_one({"_id": ObjectId(cat_id)})
        return result.deleted_count > 0

    # ─── Challenge Operations ──────────────────────────────────────

    async def get_challenges(
        self, challenge_type: Optional[str] = None,
        page: int = 1, limit: int = 20,
    ) -> dict:
        query: Dict[str, Any] = {}
        if challenge_type:
            query["type"] = challenge_type

        total = await self.db.codesprint_daily_challenges.count_documents(query)
        skip = (page - 1) * limit
        cursor = self.db.codesprint_daily_challenges.find(query).sort("created_at", -1).skip(skip).limit(limit)
        items = []
        async for c in cursor:
            c["_id"] = str(c["_id"])
            items.append(c)

        return {
            "challenges": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": max(1, (total + limit - 1) // limit),
        }

    async def create_challenge(self, data: dict) -> str:
        data["created_at"] = datetime.utcnow()
        result = await self.db.codesprint_daily_challenges.insert_one(data)
        return str(result.inserted_id)

    async def update_challenge(self, challenge_id: str, update_data: dict) -> bool:
        result = await self.db.codesprint_daily_challenges.update_one(
            {"_id": ObjectId(challenge_id)}, {"$set": update_data}
        )
        return result.modified_count > 0

    async def delete_challenge(self, challenge_id: str) -> bool:
        result = await self.db.codesprint_daily_challenges.delete_one({"_id": ObjectId(challenge_id)})
        return result.deleted_count > 0

    async def get_weekly_challenges(self, page: int = 1, limit: int = 20) -> dict:
        total = await self.db.codesprint_weekly_challenges.count_documents({})
        skip = (page - 1) * limit
        cursor = self.db.codesprint_weekly_challenges.find({}).sort("created_at", -1).skip(skip).limit(limit)
        items = []
        async for c in cursor:
            c["_id"] = str(c["_id"])
            items.append(c)
        return {
            "challenges": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": max(1, (total + limit - 1) // limit),
        }

    async def count_completed_challenges(self) -> int:
        return await self.db.codesprint_user_challenges.count_documents({"completed": True})

    # ─── Certificate Operations ────────────────────────────────────

    async def get_certificates(self, page: int = 1, limit: int = 20, user_id: Optional[str] = None) -> dict:
        query: Dict[str, Any] = {}
        if user_id:
            query["user_id"] = user_id

        total = await self.db.certificates.count_documents(query)
        skip = (page - 1) * limit
        cursor = self.db.certificates.find(query).sort("created_at", -1).skip(skip).limit(limit)
        items = []
        async for c in cursor:
            c["_id"] = str(c["_id"])
            items.append(c)

        return {
            "certificates": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": max(1, (total + limit - 1) // limit),
        }

    async def create_certificate(self, data: dict) -> str:
        data["created_at"] = datetime.utcnow()
        result = await self.db.certificates.insert_one(data)
        return str(result.inserted_id)

    async def revoke_certificate(self, cert_id: str, reason: str) -> bool:
        result = await self.db.certificates.update_one(
            {"_id": ObjectId(cert_id)},
            {"$set": {"revoked": True, "revoked_at": datetime.utcnow(), "revoked_reason": reason}},
        )
        return result.modified_count > 0

    async def verify_certificate(self, code: str) -> Optional[dict]:
        cert = await self.db.certificates.find_one({"verification_code": code})
        if cert:
            cert["_id"] = str(cert["_id"])
        return cert

    async def count_certificates(self) -> int:
        return await self.db.certificates.count_documents({})

    # ─── Certificate Templates ─────────────────────────────────────

    async def get_certificate_templates(self) -> list:
        cursor = self.db.certificate_templates.find({}).sort("created_at", -1)
        items = []
        async for t in cursor:
            t["_id"] = str(t["_id"])
            items.append(t)
        return items

    async def create_certificate_template(self, data: dict) -> str:
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        result = await self.db.certificate_templates.insert_one(data)
        return str(result.inserted_id)

    async def update_certificate_template(self, tmpl_id: str, update_data: dict) -> bool:
        update_data["updated_at"] = datetime.utcnow()
        result = await self.db.certificate_templates.update_one(
            {"_id": ObjectId(tmpl_id)}, {"$set": update_data}
        )
        return result.modified_count > 0

    async def delete_certificate_template(self, tmpl_id: str) -> bool:
        result = await self.db.certificate_templates.delete_one({"_id": ObjectId(tmpl_id)})
        return result.deleted_count > 0

    # ─── Leaderboard Operations ────────────────────────────────────

    async def get_leaderboard(self, metric: str = "xp", limit: int = 100) -> list:
        sort_field = f"{metric}" if metric in ["xp", "wpm", "accuracy"] else "xp"
        if metric == "wpm":
            pipeline = [
                {"$match": {"finished": True}},
                {"$group": {"_id": "$user_id", "best": {"$max": "$wpm"}}},
                {"$sort": {"best": -1}},
                {"$limit": limit},
            ]
            results = await self.db.codesprint_sessions.aggregate(pipeline).to_list(limit)
            return [{"user_id": r["_id"], "score": r["best"]} for r in results]

        if metric == "accuracy":
            pipeline = [
                {"$match": {"finished": True}},
                {"$group": {"_id": "$user_id", "avg": {"$avg": "$accuracy"}}},
                {"$sort": {"avg": -1}},
                {"$limit": limit},
            ]
            results = await self.db.codesprint_sessions.aggregate(pipeline).to_list(limit)
            return [{"user_id": r["_id"], "score": round(r["avg"], 2)} for r in results]

        if metric == "tests":
            pipeline = [
                {"$match": {"finished": True}},
                {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": limit},
            ]
            results = await self.db.codesprint_sessions.aggregate(pipeline).to_list(limit)
            return [{"user_id": r["_id"], "score": r["count"]} for r in results]

        cursor = self.db.codesprint_user_xp.find({}).sort("xp", -1).limit(limit)
        items = []
        async for entry in cursor:
            entry["_id"] = str(entry["_id"])
            items.append(entry)
        return items

    async def get_leaderboard_count(self) -> int:
        return await self.db.codesprint_user_xp.count_documents({})

    async def remove_invalid_scores(self, min_wpm: float = 0, max_wpm: float = 300) -> int:
        result = await self.db.codesprint_sessions.delete_many({
            "$or": [
                {"wpm": {"$lt": min_wpm}},
                {"wpm": {"$gt": max_wpm}},
                {"accuracy": {"$lt": 0}},
                {"accuracy": {"$gt": 100}},
            ]
        })
        return result.deleted_count

    async def detect_suspicious(self, threshold: float = 0.95) -> list:
        pipeline = [
            {"$match": {"finished": True}},
            {"$group": {
                "_id": "$user_id",
                "avg_accuracy": {"$avg": "$accuracy"},
                "avg_wpm": {"$avg": "$wpm"},
                "total_tests": {"$sum": 1},
            }},
            {"$match": {"avg_accuracy": {"$gte": threshold}, "total_tests": {"$gte": 5}}},
            {"$sort": {"avg_accuracy": -1}},
            {"$limit": 50},
        ]
        results = await self.db.codesprint_sessions.aggregate(pipeline).to_list(50)
        return [{"user_id": r["_id"], "avg_accuracy": round(r["avg_accuracy"], 2),
                 "avg_wpm": round(r["avg_wpm"], 2), "total_tests": r["total_tests"]} for r in results]

    # ─── Audit Log ─────────────────────────────────────────────────

    async def log_admin_action(self, log_data: dict) -> str:
        log_data["created_at"] = datetime.utcnow()
        result = await self.db.admin_logs.insert_one(log_data)
        return str(result.inserted_id)

    async def get_audit_logs(
        self, page: int = 1, limit: int = 50,
        admin_id: Optional[str] = None, action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[str] = None, end_date: Optional[str] = None,
    ) -> dict:
        query: Dict[str, Any] = {}
        if admin_id:
            query["admin_id"] = admin_id
        if action:
            query["action"] = action
        if resource_type:
            query["resource_type"] = resource_type
        if start_date:
            query.setdefault("created_at", {})["$gte"] = datetime.fromisoformat(start_date)
        if end_date:
            query.setdefault("created_at", {})["$lte"] = datetime.fromisoformat(end_date)

        total = await self.db.admin_logs.count_documents(query)
        skip = (page - 1) * limit
        cursor = self.db.admin_logs.find(query).sort("created_at", -1).skip(skip).limit(limit)
        items = []
        async for log in cursor:
            log["_id"] = str(log["_id"])
            items.append(log)

        return {
            "logs": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": max(1, (total + limit - 1) // limit),
        }

    # ─── System Settings ───────────────────────────────────────────

    async def get_settings(self, category: Optional[str] = None) -> list:
        query = {}
        if category:
            query["category"] = category
        cursor = self.db.system_settings.find(query).sort("key", 1)
        items = []
        async for s in cursor:
            s["_id"] = str(s["_id"])
            items.append(s)
        return items

    async def update_setting(self, key: str, value: Any, category: str, admin_id: str = None) -> bool:
        existing = await self.db.system_settings.find_one({"key": key})
        if existing:
            result = await self.db.system_settings.update_one(
                {"key": key},
                {"$set": {"value": value, "updated_by": admin_id, "updated_at": datetime.utcnow()}},
            )
            return result.modified_count > 0
        else:
            await self.db.system_settings.insert_one({
                "key": key, "value": value, "category": category,
                "updated_by": admin_id, "updated_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
            })
            return True

    # ─── Notifications ─────────────────────────────────────────────

    async def create_notification(self, data: dict) -> str:
        data["created_at"] = datetime.utcnow()
        result = await self.db.admin_notifications.insert_one(data)
        return str(result.inserted_id)

    async def get_notifications(self, page: int = 1, limit: int = 20) -> dict:
        total = await self.db.admin_notifications.count_documents({})
        skip = (page - 1) * limit
        cursor = self.db.admin_notifications.find({}).sort("created_at", -1).skip(skip).limit(limit)
        items = []
        async for n in cursor:
            n["_id"] = str(n["_id"])
            items.append(n)
        return {
            "notifications": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": max(1, (total + limit - 1) // limit),
        }

    async def delete_notification(self, notif_id: str) -> bool:
        result = await self.db.admin_notifications.delete_one({"_id": ObjectId(notif_id)})
        return result.deleted_count > 0

    # ─── Global Search ─────────────────────────────────────────────

    async def global_search(self, query_str: str, types: list, page: int = 1, limit: int = 20) -> dict:
        results: Dict[str, list] = {}
        regex = {"$regex": query_str, "$options": "i"}

        if "users" in types:
            cursor = self.db.users.find(
                {"$or": [{"full_name": regex}, {"email": regex}]}
            ).limit(limit)
            users = []
            async for u in cursor:
                u["_id"] = str(u["_id"])
                u.pop("password_hash", None)
                users.append(u)
            results["users"] = users

        if "snippets" in types:
            cursor = self.db.codesprint_snippets.find(
                {"$or": [{"title": regex}, {"content": regex}]}
            ).limit(limit)
            snippets = []
            async for s in cursor:
                s["_id"] = str(s["_id"])
                snippets.append(s)
            results["snippets"] = snippets

        if "certificates" in types:
            cursor = self.db.certificates.find(
                {"$or": [{"user_name": regex}, {"title": regex}, {"verification_code": regex}]}
            ).limit(limit)
            certs = []
            async for c in cursor:
                c["_id"] = str(c["_id"])
                certs.append(c)
            results["certificates"] = certs

        if "challenges" in types:
            cursor = self.db.codesprint_daily_challenges.find(
                {"$or": [{"title": regex}, {"description": regex}]}
            ).limit(limit)
            chals = []
            async for c in cursor:
                c["_id"] = str(c["_id"])
                chals.append(c)
            results["challenges"] = chals

        return results

    # ─── Reports ───────────────────────────────────────────────────

    async def generate_user_growth_report(self, days: int = 30) -> dict:
        growth = await self.get_user_growth(days)
        return {"type": "user_growth", "data": growth, "total_users": await self.count_users()}

    async def generate_practice_stats_report(self) -> dict:
        stats = await self.get_average_stats()
        lang_dist = await self.get_language_distribution()
        return {"type": "practice_stats", **stats, "language_distribution": lang_dist}

    async def generate_popular_languages_report(self) -> dict:
        langs = await self.get_language_distribution()
        return {"type": "popular_languages", "data": langs}

    async def generate_top_performers_report(self, limit: int = 10) -> dict:
        xp_top = await self.get_leaderboard("xp", limit)
        wpm_top = await self.get_leaderboard("wpm", limit)
        return {"type": "top_performers", "xp_leaders": xp_top, "wpm_leaders": wpm_top}

    async def generate_inactive_users_report(self, days: int = 30) -> dict:
        cutoff = datetime.utcnow() - timedelta(days=days)
        inactive = await self.db.users.count_documents({
            "$or": [
                {"last_login": {"$lt": cutoff}},
                {"last_login": None},
            ]
        })
        total = await self.db.users.count_documents({})
        return {"type": "inactive_users", "inactive_count": inactive, "total_users": total, "days": days}
