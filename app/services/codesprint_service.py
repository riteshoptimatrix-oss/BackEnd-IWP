from datetime import datetime, timedelta
from typing import Optional
from app.database import get_db
from app.services.gamification_service import gamification_service


class CodesprintService:

    async def finish_session(self, user_id: str, data: dict) -> dict:
        db = get_db()

        session = {
            "user_id": user_id,
            "language": data["language"],
            "difficulty": data["difficulty"],
            "category": data["category"],
            "snippet_id": data["snippet_id"],
            "snippet_title": data.get("snippet_title"),
            "duration_seconds": data.get("duration_seconds"),
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "completion_time": data["completion_time"],
            "characters_typed": data["characters_typed"],
            "correct_characters": data["correct_characters"],
            "incorrect_characters": data["incorrect_characters"],
            "total_mistakes": data.get("total_mistakes", 0),
            "backspaces": data.get("backspaces", 0),
            "accuracy": data["accuracy"],
            "cpm": data.get("cpm", 0),
            "wpm": data["wpm"],
            "completion_pct": data.get("completion_pct", 0),
            "finished": data.get("finished", False),
            "created_at": datetime.utcnow(),
        }

        result = await db.codesprint_sessions.insert_one(session)
        session_id = str(result.inserted_id)

        await self._update_user_stats(user_id, session)

        stats = await db.codesprint_user_stats.find_one({"user_id": user_id})
        is_new_best_wpm = stats and data["wpm"] >= stats.get("best_wpm", 0) and data["wpm"] > 0
        is_new_best_accuracy = stats and data["accuracy"] >= stats.get("best_accuracy", 0) and data["accuracy"] > 0

        xp_earned = 10
        if data.get("finished"):
            xp_earned += 5
        if data["accuracy"] > 95:
            xp_earned += 10
        elif data["accuracy"] > 90:
            xp_earned += 5
        if data.get("difficulty") == "hard":
            xp_earned += 15
        elif data.get("difficulty") == "medium":
            xp_earned += 5
        if is_new_best_wpm:
            xp_earned += 25
        if is_new_best_accuracy:
            xp_earned += 20

        xp_result = await gamification_service.award_xp(user_id, xp_earned, "session", f"Completed {data.get('language', '')} {data.get('difficulty', '')} test", session_id)
        new_achievements = await gamification_service.check_and_award_achievements(user_id)

        updated_stats = await db.codesprint_user_stats.find_one({"user_id": user_id})
        streak = updated_stats.get("current_streak", 0) if updated_stats else 0

        return {
            "session_id": session_id,
            "wpm": data["wpm"],
            "accuracy": data["accuracy"],
            "is_new_best_wpm": bool(is_new_best_wpm),
            "is_new_best_accuracy": bool(is_new_best_accuracy),
            "created_at": session["created_at"].isoformat(),
            "xp_earned": xp_result.get("xp_earned", 0),
            "level": xp_result.get("level", 1),
            "level_up": xp_result.get("level_up", False),
            "new_level": xp_result.get("level", 1) if xp_result.get("level_up") else None,
            "total_xp": xp_result.get("total_xp", 0),
            "streak": streak,
            "achievements_unlocked": new_achievements,
        }

    async def _update_user_stats(self, user_id: str, session: dict):
        db = get_db()
        stats = await db.codesprint_user_stats.find_one({"user_id": user_id})

        today = datetime.utcnow().strftime("%Y-%m-%d")
        last_date = stats.get("last_practice_date") if stats else None
        current_streak = stats.get("current_streak", 0) if stats else 0
        longest_streak = stats.get("longest_streak", 0) if stats else 0

        if last_date:
            last_dt = datetime.strptime(last_date, "%Y-%m-%d")
            today_dt = datetime.strptime(today, "%Y-%m-%d")
            diff = (today_dt - last_dt).days
            if diff == 1:
                current_streak += 1
            elif diff > 1:
                current_streak = 1
        else:
            current_streak = 1

        longest_streak = max(longest_streak, current_streak)

        total_tests = (stats.get("total_tests", 0) if stats else 0) + 1
        total_seconds = (stats.get("total_practice_seconds", 0) if stats else 0) + session["completion_time"]

        agg_cursor = db.codesprint_sessions.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": None,
                "avg_wpm": {"$avg": "$wpm"},
                "avg_accuracy": {"$avg": "$accuracy"},
                "best_wpm": {"$max": "$wpm"},
                "best_accuracy": {"$max": "$accuracy"},
            }},
        ])
        agg = None
        async for doc in agg_cursor:
            agg = doc

        if agg:
            avg_wpm = agg.get("avg_wpm", 0)
            avg_accuracy = agg.get("avg_accuracy", 0)
            best_wpm = agg.get("best_wpm", 0)
            best_accuracy = agg.get("best_accuracy", 0)
        else:
            avg_wpm = session["wpm"]
            avg_accuracy = session["accuracy"]
            best_wpm = session["wpm"]
            best_accuracy = session["accuracy"]

        best_cpm = max(stats.get("best_cpm", 0) if stats else 0, session.get("cpm", 0))
        longest_session = max(stats.get("longest_session_seconds", 0) if stats else 0, session["completion_time"])

        lang_cursor = db.codesprint_sessions.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$language", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1},
        ])
        favorite_lang = None
        async for doc in lang_cursor:
            favorite_lang = doc["_id"]

        cat_cursor = db.codesprint_sessions.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1},
        ])
        fav_category = None
        async for doc in cat_cursor:
            fav_category = doc["_id"]

        langs_cursor = db.codesprint_sessions.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$language"}},
        ])
        lang_set = []
        async for doc in langs_cursor:
            lang_set.append(doc["_id"])

        cat_cursor2 = db.codesprint_sessions.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$category"}},
        ])
        cat_set = []
        async for doc in cat_cursor2:
            cat_set.append(doc["_id"])

        update_data = {
            "total_tests": total_tests,
            "total_practice_seconds": total_seconds,
            "avg_wpm": round(avg_wpm, 1),
            "avg_accuracy": round(avg_accuracy, 1),
            "best_wpm": round(best_wpm, 1),
            "best_accuracy": round(best_accuracy, 1),
            "best_cpm": round(best_cpm, 1),
            "longest_session_seconds": round(longest_session, 1),
            "favorite_language": favorite_lang,
            "most_practiced_category": fav_category,
            "languages_practiced": lang_set,
            "categories_practiced": cat_set,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "last_practice_date": today,
            "updated_at": datetime.utcnow(),
        }

        if stats:
            await db.codesprint_user_stats.update_one(
                {"user_id": user_id}, {"$set": update_data}
            )
        else:
            update_data["user_id"] = user_id
            await db.codesprint_user_stats.insert_one(update_data)

    async def get_history(
        self, user_id: str, page: int = 1, limit: int = 20,
        language: Optional[str] = None, difficulty: Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict:
        db = get_db()
        query = {"user_id": user_id}
        if language:
            query["language"] = language
        if difficulty:
            query["difficulty"] = difficulty
        if category:
            query["category"] = category

        total = await db.codesprint_sessions.count_documents(query)
        skip = (page - 1) * limit

        cursor = db.codesprint_sessions.find(query).sort("created_at", -1).skip(skip).limit(limit)
        sessions = []
        async for doc in cursor:
            sessions.append({
                "id": str(doc["_id"]),
                "language": doc.get("language", ""),
                "difficulty": doc.get("difficulty", ""),
                "category": doc.get("category", ""),
                "snippet_title": doc.get("snippet_title"),
                "wpm": doc.get("wpm", 0),
                "accuracy": doc.get("accuracy", 0),
                "cpm": doc.get("cpm", 0),
                "characters_typed": doc.get("characters_typed", 0),
                "correct_characters": doc.get("correct_characters", 0),
                "incorrect_characters": doc.get("incorrect_characters", 0),
                "total_mistakes": doc.get("total_mistakes", 0),
                "completion_time": doc.get("completion_time", 0),
                "completion_pct": doc.get("completion_pct", 0),
                "finished": doc.get("finished", False),
                "duration_seconds": doc.get("duration_seconds"),
                "created_at": doc.get("created_at", datetime.utcnow()).isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at", "")),
            })

        return {
            "sessions": sessions,
            "total": total,
            "page": page,
            "limit": limit,
            "has_more": skip + limit < total,
        }

    async def get_statistics(self, user_id: str) -> dict:
        db = get_db()
        stats = await db.codesprint_user_stats.find_one({"user_id": user_id})

        if not stats:
            return {
                "overall": {
                    "total_tests": 0, "total_practice_hours": 0, "avg_wpm": 0,
                    "avg_accuracy": 0, "best_wpm": 0, "best_accuracy": 0,
                    "favorite_language": None, "most_practiced_category": None,
                    "languages_practiced": [], "current_streak": 0, "longest_streak": 0,
                    "personal_records": {"best_wpm": 0, "best_accuracy": 0, "best_cpm": 0, "longest_session_seconds": 0, "best_language": None, "best_difficulty": None},
                },
                "by_language": [],
                "by_difficulty": [],
            }

        lang_cursor = db.codesprint_sessions.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$language",
                "tests": {"$sum": 1},
                "avg_wpm": {"$avg": "$wpm"},
                "avg_accuracy": {"$avg": "$accuracy"},
                "best_wpm": {"$max": "$wpm"},
                "best_accuracy": {"$max": "$accuracy"},
            }},
            {"$sort": {"tests": -1}},
        ])
        by_lang = []
        async for doc in lang_cursor:
            by_lang.append({
                "language": doc["_id"],
                "tests": doc["tests"],
                "avg_wpm": round(doc["avg_wpm"], 1),
                "avg_accuracy": round(doc["avg_accuracy"], 1),
                "best_wpm": round(doc["best_wpm"], 1),
                "best_accuracy": round(doc["best_accuracy"], 1),
            })

        diff_cursor = db.codesprint_sessions.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$difficulty",
                "tests": {"$sum": 1},
                "avg_wpm": {"$avg": "$wpm"},
                "avg_accuracy": {"$avg": "$accuracy"},
            }},
            {"$sort": {"tests": -1}},
        ])
        by_diff = []
        async for doc in diff_cursor:
            by_diff.append({
                "difficulty": doc["_id"],
                "tests": doc["tests"],
                "avg_wpm": round(doc["avg_wpm"], 1),
                "avg_accuracy": round(doc["avg_accuracy"], 1),
            })

        best_lang = by_lang[0]["language"] if by_lang else None
        best_diff = by_diff[0]["difficulty"] if by_diff else None

        return {
            "overall": {
                "total_tests": stats.get("total_tests", 0),
                "total_practice_hours": round(stats.get("total_practice_seconds", 0) / 3600, 2),
                "avg_wpm": stats.get("avg_wpm", 0),
                "avg_accuracy": stats.get("avg_accuracy", 0),
                "best_wpm": stats.get("best_wpm", 0),
                "best_accuracy": stats.get("best_accuracy", 0),
                "favorite_language": stats.get("favorite_language"),
                "most_practiced_category": stats.get("most_practiced_category"),
                "languages_practiced": stats.get("languages_practiced", []),
                "current_streak": stats.get("current_streak", 0),
                "longest_streak": stats.get("longest_streak", 0),
                "personal_records": {
                    "best_wpm": stats.get("best_wpm", 0),
                    "best_accuracy": stats.get("best_accuracy", 0),
                    "best_cpm": stats.get("best_cpm", 0),
                    "longest_session_seconds": stats.get("longest_session_seconds", 0),
                    "best_language": best_lang,
                    "best_difficulty": best_diff,
                },
            },
            "by_language": by_lang,
            "by_difficulty": by_diff,
        }

    async def get_profile(self, user_id: str, user_data: dict) -> dict:
        stats = await self.get_statistics(user_id)
        return {
            "user_id": user_id,
            "display_name": user_data.get("full_name", "User"),
            "email": user_data.get("email", ""),
            "avatar": user_data.get("avatar"),
            "joined_at": user_data.get("created_at", datetime.utcnow()).isoformat() if isinstance(user_data.get("created_at"), datetime) else str(user_data.get("created_at", "")),
            "stats": stats["overall"],
        }


codesprint_service = CodesprintService()
