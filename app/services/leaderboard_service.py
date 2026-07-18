from datetime import datetime, timedelta
from typing import Optional
from app.database import get_db


class LeaderboardService:

    async def get_leaderboard(
        self, period: str = "all_time", language: Optional[str] = None,
        metric: str = "xp", page: int = 1, limit: int = 50,
    ) -> dict:
        db = get_db()

        date_filter = None
        if period == "today":
            date_filter = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            date_filter = datetime.utcnow() - timedelta(days=7)
        elif period == "month":
            date_filter = datetime.utcnow() - timedelta(days=30)

        if metric == "xp":
            return await self._leaderboard_by_xp(db, date_filter, page, limit)
        elif metric == "wpm":
            return await self._leaderboard_by_wpm(db, date_filter, language, page, limit)
        elif metric == "accuracy":
            return await self._leaderboard_by_accuracy(db, date_filter, language, page, limit)
        elif metric == "streak":
            return await self._leaderboard_by_streak(db, page, limit)
        elif metric == "tests":
            return await self._leaderboard_by_tests(db, date_filter, page, limit)
        return await self._leaderboard_by_xp(db, date_filter, page, limit)

    async def _leaderboard_by_xp(self, db, date_filter, page, limit):
        query = {}
        if date_filter:
            query["updated_at"] = {"$gte": date_filter}

        total = await db.codesprint_user_xp.count_documents(query)
        skip = (page - 1) * limit
        cursor = db.codesprint_user_xp.find(query).sort("xp", -1).skip(skip).limit(limit)

        entries = []
        rank = skip
        async for doc in cursor:
            rank += 1
            user = await self._get_user_info(db, doc.get("user_id", ""))
            stats = await db.codesprint_user_stats.find_one({"user_id": doc.get("user_id", "")})
            entries.append({
                "rank": rank,
                "user_id": doc.get("user_id", ""),
                "display_name": user.get("full_name", "User") if user else "User",
                "avatar": user.get("avatar") if user else None,
                "score": doc.get("xp", 0),
                "level": doc.get("level", 1),
                "xp": doc.get("xp", 0),
                "title": doc.get("title", "Beginner"),
                "best_wpm": stats.get("best_wpm", 0) if stats else 0,
                "current_streak": stats.get("current_streak", 0) if stats else 0,
            })

        return {"entries": entries, "total": total, "page": page, "limit": limit, "has_more": skip + limit < total}

    async def _leaderboard_by_wpm(self, db, date_filter, language, page, limit):
        match = {}
        if date_filter:
            match["created_at"] = {"$gte": date_filter}
        if language:
            match["language"] = language

        count_pipeline = [
            {"$match": match} if match else {"$match": {}},
            {"$group": {"_id": "$user_id"}},
            {"$count": "total"},
        ]
        if not match:
            count_pipeline = count_pipeline[1:]
        count_cursor = db.codesprint_sessions.aggregate(count_pipeline)
        total = 0
        async for doc in count_cursor:
            total = doc.get("total", 0)

        pipeline = [
            {"$match": match} if match else {"$match": {}},
            {"$group": {"_id": "$user_id", "best_wpm": {"$max": "$wpm"}, "avg_wpm": {"$avg": "$wpm"}, "tests": {"$sum": 1}}},
            {"$sort": {"best_wpm": -1}},
            {"$skip": (page - 1) * limit},
            {"$limit": limit},
        ]
        if not match:
            pipeline = pipeline[1:]

        cursor = db.codesprint_sessions.aggregate(pipeline)

        entries = []
        rank = (page - 1) * limit
        async for doc in cursor:
            rank += 1
            user = await self._get_user_info(db, doc["_id"])
            xp_doc = await db.codesprint_user_xp.find_one({"user_id": doc["_id"]})
            entries.append({
                "rank": rank,
                "user_id": doc["_id"],
                "display_name": user.get("full_name", "User") if user else "User",
                "avatar": user.get("avatar") if user else None,
                "score": round(doc.get("best_wpm", 0), 1),
                "level": xp_doc.get("level", 1) if xp_doc else 1,
                "xp": xp_doc.get("xp", 0) if xp_doc else 0,
                "title": xp_doc.get("title", "Beginner") if xp_doc else "Beginner",
                "best_wpm": round(doc.get("best_wpm", 0), 1),
                "current_streak": 0,
            })

        return {"entries": entries, "total": total, "page": page, "limit": limit, "has_more": len(entries) == limit}

    async def _leaderboard_by_accuracy(self, db, date_filter, language, page, limit):
        match = {}
        if date_filter:
            match["created_at"] = {"$gte": date_filter}
        if language:
            match["language"] = language

        count_pipeline = [
            {"$match": match} if match else {"$match": {}},
            {"$group": {"_id": "$user_id", "tests": {"$sum": 1}}},
            {"$match": {"tests": {"$gte": 3}}},
            {"$count": "total"},
        ]
        if not match:
            count_pipeline = count_pipeline[1:]
        count_cursor = db.codesprint_sessions.aggregate(count_pipeline)
        total = 0
        async for doc in count_cursor:
            total = doc.get("total", 0)

        pipeline = [
            {"$match": match} if match else {"$match": {}},
            {"$group": {"_id": "$user_id", "avg_accuracy": {"$avg": "$accuracy"}, "tests": {"$sum": 1}}},
            {"$match": {"tests": {"$gte": 3}}},
            {"$sort": {"avg_accuracy": -1}},
            {"$skip": (page - 1) * limit},
            {"$limit": limit},
        ]
        if not match:
            pipeline = pipeline[1:]

        cursor = db.codesprint_sessions.aggregate(pipeline)

        entries = []
        rank = (page - 1) * limit
        async for doc in cursor:
            rank += 1
            user = await self._get_user_info(db, doc["_id"])
            xp_doc = await db.codesprint_user_xp.find_one({"user_id": doc["_id"]})
            entries.append({
                "rank": rank,
                "user_id": doc["_id"],
                "display_name": user.get("full_name", "User") if user else "User",
                "avatar": user.get("avatar") if user else None,
                "score": round(doc.get("avg_accuracy", 0), 1),
                "level": xp_doc.get("level", 1) if xp_doc else 1,
                "xp": xp_doc.get("xp", 0) if xp_doc else 0,
                "title": xp_doc.get("title", "Beginner") if xp_doc else "Beginner",
                "best_wpm": 0,
                "current_streak": 0,
            })

        return {"entries": entries, "total": total, "page": page, "limit": limit, "has_more": len(entries) == limit}

    async def _leaderboard_by_streak(self, db, page, limit):
        total = await db.codesprint_user_stats.count_documents({"current_streak": {"$gt": 0}})
        skip = (page - 1) * limit
        cursor = db.codesprint_user_stats.find({"current_streak": {"$gt": 0}}).sort("current_streak", -1).skip(skip).limit(limit)

        entries = []
        rank = skip
        async for doc in cursor:
            rank += 1
            user = await self._get_user_info(db, doc.get("user_id", ""))
            xp_doc = await db.codesprint_user_xp.find_one({"user_id": doc.get("user_id", "")})
            entries.append({
                "rank": rank,
                "user_id": doc.get("user_id", ""),
                "display_name": user.get("full_name", "User") if user else "User",
                "avatar": user.get("avatar") if user else None,
                "score": doc.get("current_streak", 0),
                "level": xp_doc.get("level", 1) if xp_doc else 1,
                "xp": xp_doc.get("xp", 0) if xp_doc else 0,
                "title": xp_doc.get("title", "Beginner") if xp_doc else "Beginner",
                "best_wpm": 0,
                "current_streak": doc.get("current_streak", 0),
            })

        return {"entries": entries, "total": total, "page": page, "limit": limit, "has_more": skip + limit < total}

    async def _leaderboard_by_tests(self, db, date_filter, page, limit):
        match = {}
        if date_filter:
            match["created_at"] = {"$gte": date_filter}

        count_pipeline = [
            {"$match": match} if match else {"$match": {}},
            {"$group": {"_id": "$user_id"}},
            {"$count": "total"},
        ]
        if not match:
            count_pipeline = count_pipeline[1:]
        count_cursor = db.codesprint_sessions.aggregate(count_pipeline)
        total = 0
        async for doc in count_cursor:
            total = doc.get("total", 0)

        pipeline = [
            {"$match": match} if match else {"$match": {}},
            {"$group": {"_id": "$user_id", "tests": {"$sum": 1}}},
            {"$sort": {"tests": -1}},
            {"$skip": (page - 1) * limit},
            {"$limit": limit},
        ]
        if not match:
            pipeline = pipeline[1:]

        cursor = db.codesprint_sessions.aggregate(pipeline)

        entries = []
        rank = (page - 1) * limit
        async for doc in cursor:
            rank += 1
            user = await self._get_user_info(db, doc["_id"])
            xp_doc = await db.codesprint_user_xp.find_one({"user_id": doc["_id"]})
            entries.append({
                "rank": rank,
                "user_id": doc["_id"],
                "display_name": user.get("full_name", "User") if user else "User",
                "avatar": user.get("avatar") if user else None,
                "score": doc.get("tests", 0),
                "level": xp_doc.get("level", 1) if xp_doc else 1,
                "xp": xp_doc.get("xp", 0) if xp_doc else 0,
                "title": xp_doc.get("title", "Beginner") if xp_doc else "Beginner",
                "best_wpm": 0,
                "current_streak": 0,
            })

        return {"entries": entries, "total": total, "page": page, "limit": limit, "has_more": len(entries) == limit}

    async def get_user_rank(self, user_id: str, metric: str = "xp") -> dict:
        db = get_db()

        if metric == "xp":
            user_xp = await db.codesprint_user_xp.find_one({"user_id": user_id})
            if not user_xp:
                return {"current_rank": 0, "previous_rank": None, "rank_change": None, "top_percentage": 100, "xp": 0, "level": 1, "title": "Beginner", "progress_to_next": 0, "xp_for_next_level": 250, "metric_score": 0}
            score = user_xp.get("xp", 0)
            total = await db.codesprint_user_xp.count_documents({})
            above = await db.codesprint_user_xp.count_documents({"xp": {"$gt": score}})
            rank = above + 1
        elif metric == "wpm":
            stats = await db.codesprint_user_stats.find_one({"user_id": user_id})
            if not stats:
                return {"current_rank": 0, "previous_rank": None, "rank_change": None, "top_percentage": 100, "xp": 0, "level": 1, "title": "Beginner", "progress_to_next": 0, "xp_for_next_level": 250, "metric_score": 0}
            score = stats.get("best_wpm", 0)
            pipeline = [
                {"$group": {"_id": "$user_id", "best_wpm": {"$max": "$wpm"}}},
                {"$match": {"best_wpm": {"$gt": score}}},
            ]
            above_cursor = db.codesprint_sessions.aggregate(pipeline)
            above_count = 0
            async for _ in above_cursor:
                above_count += 1
            rank = above_count + 1
            total = await db.codesprint_user_stats.count_documents({})
        else:
            return {"current_rank": 0, "previous_rank": None, "rank_change": None, "top_percentage": 100, "xp": 0, "level": 1, "title": "Beginner", "progress_to_next": 0, "xp_for_next_level": 250, "metric_score": 0}

        previous_rank = None
        rank_change = None
        rank_history = await db.codesprint_rank_history.find_one({"user_id": user_id, "metric": metric})
        if rank_history:
            previous_rank = rank_history.get("rank")
            if previous_rank and rank:
                rank_change = previous_rank - rank

        await db.codesprint_rank_history.update_one(
            {"user_id": user_id, "metric": metric},
            {"$set": {"rank": rank, "updated_at": datetime.utcnow()}},
            upsert=True,
        )

        from app.services.gamification_service import gamification_service, get_progress_to_next
        xp_info = await gamification_service.get_user_xp(user_id)
        progress = get_progress_to_next(xp_info["xp"])
        top_pct = round((rank / max(total, 1)) * 100, 1)

        return {
            "current_rank": rank,
            "previous_rank": previous_rank,
            "rank_change": rank_change,
            "top_percentage": top_pct,
            "xp": xp_info["xp"],
            "level": xp_info["level"],
            "title": xp_info["title"],
            "progress_to_next": progress["progress"],
            "xp_for_next_level": progress["xp_for_next"],
            "metric_score": score,
        }

    async def _get_user_info(self, db, user_id: str) -> Optional[dict]:
        from bson import ObjectId
        try:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                return {"full_name": user.get("full_name", "User"), "avatar": user.get("avatar")}
        except Exception:
            pass
        return None


leaderboard_service = LeaderboardService()
