from datetime import datetime, timedelta
from typing import Optional, List
from app.database import get_db


LEVEL_TABLE = {
    1: 0, 2: 250, 3: 600, 4: 1200, 5: 2000,
    6: 3500, 7: 5500, 8: 8000, 9: 12000, 10: 18000,
}

LEVEL_TITLES = {
    1: "Beginner", 2: "Typist", 3: "Coder", 4: "Fast Fingers", 5: "Speed Demon",
    6: "Code Warrior", 7: "Keyboard Master", 8: "Elite Typist", 9: "Code Ninja", 10: "Legendary",
}

ACHIEVEMENTS = [
    {"key": "first_test", "name": "First Steps", "description": "Complete your first typing test", "icon": "🎯", "category": "milestone", "xp_reward": 10, "tier": "bronze", "condition_type": "total_tests", "condition_value": 1},
    {"key": "tests_10", "name": "Getting Started", "description": "Complete 10 typing tests", "icon": "📝", "category": "milestone", "xp_reward": 25, "tier": "bronze", "condition_type": "total_tests", "condition_value": 10},
    {"key": "tests_100", "name": "Dedicated", "description": "Complete 100 typing tests", "icon": "🔥", "category": "milestone", "xp_reward": 100, "tier": "silver", "condition_type": "total_tests", "condition_value": 100},
    {"key": "tests_1000", "name": "Legend", "description": "Complete 1000 typing tests", "icon": "👑", "category": "milestone", "xp_reward": 500, "tier": "gold", "condition_type": "total_tests", "condition_value": 1000},
    {"key": "perfect_accuracy", "name": "Perfection", "description": "Achieve 100% accuracy on a test", "icon": "💎", "category": "accuracy", "xp_reward": 50, "tier": "silver", "condition_type": "best_accuracy", "condition_value": 100},
    {"key": "wpm_100", "name": "Speed Demon", "description": "Reach 100 WPM", "icon": "⚡", "category": "speed", "xp_reward": 75, "tier": "silver", "condition_type": "best_wpm", "condition_value": 100},
    {"key": "wpm_150", "name": "Lightning Fingers", "description": "Reach 150 WPM", "icon": "🌩️", "category": "speed", "xp_reward": 150, "tier": "gold", "condition_type": "best_wpm", "condition_value": 150},
    {"key": "streak_7", "name": "Week Warrior", "description": "Maintain a 7-day streak", "icon": "📅", "category": "streak", "xp_reward": 100, "tier": "bronze", "condition_type": "current_streak", "condition_value": 7},
    {"key": "streak_30", "name": "Monthly Master", "description": "Maintain a 30-day streak", "icon": "🏆", "category": "streak", "xp_reward": 300, "tier": "silver", "condition_type": "current_streak", "condition_value": 30},
    {"key": "streak_100", "name": "Unstoppable", "description": "Maintain a 100-day streak", "icon": "🌟", "category": "streak", "xp_reward": 1000, "tier": "gold", "condition_type": "longest_streak", "condition_value": 100},
    {"key": "html_master", "name": "HTML Master", "description": "Complete 50 HTML tests", "icon": "🏷️", "category": "language", "xp_reward": 75, "tier": "bronze", "condition_type": "language_tests", "condition_value": 50, "condition_language": "html"},
    {"key": "react_master", "name": "React Master", "description": "Complete 50 React tests", "icon": "⚛️", "category": "language", "xp_reward": 75, "tier": "bronze", "condition_type": "language_tests", "condition_value": 50, "condition_language": "react"},
    {"key": "js_master", "name": "JS Guru", "description": "Complete 50 JavaScript tests", "icon": "🟨", "category": "language", "xp_reward": 75, "tier": "bronze", "condition_type": "language_tests", "condition_value": 50, "condition_language": "javascript"},
    {"key": "hard_master", "name": "Hard Mode", "description": "Complete 50 hard difficulty tests", "icon": "💪", "category": "difficulty", "xp_reward": 100, "tier": "silver", "condition_type": "difficulty_tests", "condition_value": 50, "condition_language": "hard"},
    {"key": "level_5", "name": "Rising Star", "description": "Reach Level 5", "icon": "⭐", "category": "level", "xp_reward": 50, "tier": "bronze", "condition_type": "level", "condition_value": 5},
    {"key": "level_10", "name": "Elite", "description": "Reach Level 10", "icon": "🏅", "category": "level", "xp_reward": 200, "tier": "gold", "condition_type": "level", "condition_value": 10},
]


def get_level_for_xp(xp: int) -> int:
    level = 1
    for lvl, required in sorted(LEVEL_TABLE.items()):
        if xp >= required:
            level = lvl
        else:
            break
    return level


def get_xp_for_level(level: int) -> int:
    return LEVEL_TABLE.get(level, 18000)


def get_title_for_level(level: int) -> str:
    return LEVEL_TITLES.get(level, "Legendary")


def get_progress_to_next(xp: int) -> dict:
    level = get_level_for_xp(xp)
    current_level_xp = get_xp_for_level(level)
    next_level_xp = get_xp_for_level(level + 1) if level < 10 else get_xp_for_level(10)
    if next_level_xp <= current_level_xp:
        return {"progress": 1.0, "xp_for_next": 0, "xp_in_level": 0, "xp_needed": 0}
    xp_in_level = xp - current_level_xp
    xp_needed = next_level_xp - current_level_xp
    progress = min(1.0, xp_in_level / xp_needed) if xp_needed > 0 else 1.0
    return {"progress": progress, "xp_for_next": next_level_xp, "xp_in_level": xp_in_level, "xp_needed": xp_needed}


class GamificationService:

    async def award_xp(self, user_id: str, amount: int, xp_type: str, description: str, session_id: str = None) -> dict:
        db = get_db()

        if session_id:
            existing_txn = await db.codesprint_xp_history.find_one({"user_id": user_id, "session_id": session_id})
            if existing_txn:
                return {"xp_earned": 0, "total_xp": 0, "level": 1, "title": "Beginner", "level_up": False}

        txn = {
            "user_id": user_id,
            "amount": amount,
            "type": xp_type,
            "description": description,
            "session_id": session_id,
            "created_at": datetime.utcnow(),
        }
        await db.codesprint_xp_history.insert_one(txn)

        user_xp = await db.codesprint_user_xp.find_one({"user_id": user_id})
        old_level = 1
        if user_xp:
            old_level = user_xp.get("level", 1)
            new_total = user_xp.get("xp", 0) + amount
            new_level = get_level_for_xp(new_total)
            new_title = get_title_for_level(new_level)
            await db.codesprint_user_xp.update_one(
                {"user_id": user_id},
                {"$set": {"xp": new_total, "level": new_level, "title": new_title, "total_xp_earned": user_xp.get("total_xp_earned", 0) + amount, "updated_at": datetime.utcnow()}}
            )
        else:
            new_total = amount
            new_level = get_level_for_xp(new_total)
            new_title = get_title_for_level(new_level)
            await db.codesprint_user_xp.insert_one({
                "user_id": user_id, "xp": new_total, "level": new_level, "title": new_title,
                "total_xp_earned": new_total, "coins": 0, "updated_at": datetime.utcnow(),
            })
            old_level = 0

        level_up = new_level > old_level
        return {"xp_earned": amount, "total_xp": new_total, "level": new_level, "title": new_title, "level_up": level_up}

    async def award_daily_login_xp(self, user_id: str) -> dict:
        db = get_db()
        today = datetime.utcnow().strftime("%Y-%m-%d")

        existing = await db.codesprint_xp_history.find_one({
            "user_id": user_id, "type": "daily_login",
            "created_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)},
        })
        if existing:
            return {"success": False, "xp_earned": 0, "message": "Daily login XP already claimed today"}

        return await self.award_xp(user_id, 5, "daily_login", "Daily login bonus")

    async def get_user_xp(self, user_id: str) -> dict:
        db = get_db()
        user_xp = await db.codesprint_user_xp.find_one({"user_id": user_id})
        if not user_xp:
            return {
                "xp": 0, "level": 1, "title": "Beginner",
                "xp_for_current_level": 0, "xp_for_next_level": 250,
                "progress_to_next": 0.0, "total_xp_earned": 0,
                "recent_transactions": [],
            }

        xp = user_xp.get("xp", 0)
        level = user_xp.get("level", 1)
        progress = get_progress_to_next(xp)

        cursor = db.codesprint_xp_history.find({"user_id": user_id}).sort("created_at", -1).limit(10)
        transactions = []
        async for txn in cursor:
            transactions.append({
                "amount": txn.get("amount", 0),
                "type": txn.get("type", ""),
                "description": txn.get("description", ""),
                "created_at": txn.get("created_at", datetime.utcnow()).isoformat() if isinstance(txn.get("created_at"), datetime) else str(txn.get("created_at", "")),
            })

        return {
            "xp": xp, "level": level, "title": user_xp.get("title", "Beginner"),
            "xp_for_current_level": get_xp_for_level(level),
            "xp_for_next_level": progress["xp_for_next"],
            "progress_to_next": progress["progress"],
            "total_xp_earned": user_xp.get("total_xp_earned", 0),
            "recent_transactions": transactions,
        }

    async def get_streak(self, user_id: str) -> dict:
        db = get_db()
        stats = await db.codesprint_user_stats.find_one({"user_id": user_id})
        today = datetime.utcnow().strftime("%Y-%m-%d")

        if not stats:
            return {"current_streak": 0, "longest_streak": 0, "last_practice_date": None, "streak_calendar": [], "today_practiced": False}

        last_date = stats.get("last_practice_date")
        current = stats.get("current_streak", 0)
        longest = stats.get("longest_streak", 0)

        today_practiced = last_date == today

        calendar_cursor = db.codesprint_sessions.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}}},
            {"$sort": {"_id": -1}},
            {"$limit": 365},
        ])
        calendar = []
        async for doc in calendar_cursor:
            calendar.append(doc["_id"])

        return {
            "current_streak": current,
            "longest_streak": longest,
            "last_practice_date": last_date,
            "streak_calendar": calendar,
            "today_practiced": today_practiced,
        }

    async def check_and_award_achievements(self, user_id: str) -> List[str]:
        db = get_db()
        stats = await db.codesprint_user_stats.find_one({"user_id": user_id})
        user_xp = await db.codesprint_user_xp.find_one({"user_id": user_id})
        if not stats and not user_xp:
            return []

        unlocked_cursor = db.codesprint_user_achievements.find({"user_id": user_id})
        unlocked_keys = set()
        async for doc in unlocked_cursor:
            unlocked_keys.add(doc.get("achievement_key", ""))

        newly_unlocked = []

        for ach in ACHIEVEMENTS:
            if ach["key"] in unlocked_keys:
                continue

            met = False
            ctype = ach["condition_type"]
            cval = ach["condition_value"]

            if ctype == "total_tests" and stats:
                met = stats.get("total_tests", 0) >= cval
            elif ctype == "best_accuracy" and stats:
                met = stats.get("best_accuracy", 0) >= cval
            elif ctype == "best_wpm" and stats:
                met = stats.get("best_wpm", 0) >= cval
            elif ctype == "current_streak" and stats:
                met = stats.get("current_streak", 0) >= cval
            elif ctype == "longest_streak" and stats:
                met = stats.get("longest_streak", 0) >= cval
            elif ctype == "level" and user_xp:
                met = user_xp.get("level", 1) >= cval
            elif ctype == "language_tests" and stats:
                lang = ach.get("condition_language", "")
                langs = stats.get("languages_practiced", [])
                lang_count = await db.codesprint_sessions.count_documents({"user_id": user_id, "language": lang})
                met = lang_count >= cval
            elif ctype == "difficulty_tests" and stats:
                diff = ach.get("condition_language", "")
                diff_count = await db.codesprint_sessions.count_documents({"user_id": user_id, "difficulty": diff})
                met = diff_count >= cval

            if met:
                await db.codesprint_user_achievements.insert_one({
                    "user_id": user_id,
                    "achievement_key": ach["key"],
                    "unlocked_at": datetime.utcnow(),
                })
                if ach["xp_reward"] > 0:
                    await self.award_xp(user_id, ach["xp_reward"], "achievement", f"Achievement: {ach['name']}")
                newly_unlocked.append(ach["key"])

        return newly_unlocked

    async def get_achievements(self, user_id: str) -> dict:
        db = get_db()
        unlocked_cursor = db.codesprint_user_achievements.find({"user_id": user_id})
        unlocked_map = {}
        async for doc in unlocked_cursor:
            unlocked_map[doc.get("achievement_key", "")] = doc.get("unlocked_at")

        achievements = []
        for ach in ACHIEVEMENTS:
            unlocked_at = unlocked_map.get(ach["key"])
            achievements.append({
                "key": ach["key"],
                "name": ach["name"],
                "description": ach["description"],
                "icon": ach["icon"],
                "category": ach["category"],
                "tier": ach["tier"],
                "xp_reward": ach["xp_reward"],
                "unlocked": unlocked_at is not None,
                "unlocked_at": unlocked_at.isoformat() if isinstance(unlocked_at, datetime) else (str(unlocked_at) if unlocked_at else None),
            })

        return {
            "achievements": achievements,
            "total_unlocked": len(unlocked_map),
            "total_available": len(ACHIEVEMENTS),
        }

    async def get_gamification_profile(self, user_id: str, user_data: dict) -> dict:
        xp_info = await self.get_user_xp(user_id)
        streak_info = await self.get_streak(user_id)
        achievements_info = await self.get_achievements(user_id)

        return {
            "user_id": user_id,
            "display_name": user_data.get("full_name", "User"),
            "avatar": user_data.get("avatar"),
            "xp": xp_info["xp"],
            "level": xp_info["level"],
            "title": xp_info["title"],
            "total_xp_earned": xp_info["total_xp_earned"],
            "current_streak": streak_info["current_streak"],
            "longest_streak": streak_info["longest_streak"],
            "achievements_count": achievements_info["total_unlocked"],
            "total_achievements": achievements_info["total_available"],
            "rank": None,
            "top_percentage": None,
        }


gamification_service = GamificationService()
