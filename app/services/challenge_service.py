import random
from datetime import datetime, timedelta, time
from bson import ObjectId
from app.database import get_db


DAILY_CHALLENGE_TEMPLATES = [
    {"language": "html", "category": "Basic HTML", "difficulty": "easy", "title": "HTML Warm-Up", "description": "Complete an easy HTML challenge", "xp_reward": 30, "bonus_xp": 15},
    {"language": "html", "category": "Forms", "difficulty": "medium", "title": "Form Builder", "description": "Build a medium HTML form", "xp_reward": 40, "bonus_xp": 20},
    {"language": "css", "category": "Flexbox", "difficulty": "medium", "title": "Flex Master", "description": "Master CSS Flexbox layout", "xp_reward": 40, "bonus_xp": 20},
    {"language": "css", "category": "Grid", "difficulty": "hard", "title": "Grid Guru", "description": "Tackle a hard CSS Grid challenge", "xp_reward": 60, "bonus_xp": 30},
    {"language": "javascript", "category": "Functions", "difficulty": "medium", "title": "Function Factory", "description": "Write JavaScript functions", "xp_reward": 45, "bonus_xp": 25},
    {"language": "javascript", "category": "Async/Await", "difficulty": "hard", "title": "Async Ace", "description": "Master async/await patterns", "xp_reward": 60, "bonus_xp": 30},
    {"language": "react", "category": "Components", "difficulty": "medium", "title": "Component Crafter", "description": "Build React components", "xp_reward": 45, "bonus_xp": 25},
    {"language": "react", "category": "Hooks", "difficulty": "hard", "title": "Hook Hero", "description": "Master React hooks", "xp_reward": 60, "bonus_xp": 30},
    {"language": "typescript", "category": "Interfaces", "difficulty": "medium", "title": "Type Titan", "description": "Define TypeScript interfaces", "xp_reward": 45, "bonus_xp": 25},
    {"language": "nextjs", "category": "App Router", "difficulty": "hard", "title": "Router Ranger", "description": "Navigate Next.js App Router", "xp_reward": 65, "bonus_xp": 35},
    {"language": "dart", "category": "Classes", "difficulty": "medium", "title": "Dart Duel", "description": "Write Dart classes", "xp_reward": 40, "bonus_xp": 20},
    {"language": "angular", "category": "Components", "difficulty": "hard", "title": "Angular Assault", "description": "Build Angular components", "xp_reward": 60, "bonus_xp": 30},
    {"language": "vue", "category": "Composition API", "difficulty": "medium", "title": "Vue Venture", "description": "Use Vue Composition API", "xp_reward": 45, "bonus_xp": 25},
]

WEEKLY_MISSION_TEMPLATES = [
    {"type": "tests_count", "title": "Practice Marathon", "description": "Complete 10 typing tests this week", "target_value": 10, "xp_reward": 100},
    {"type": "accuracy_target", "title": "Precision Player", "description": "Achieve 95% average accuracy", "target_value": 95, "xp_reward": 150},
    {"type": "practice_time", "title": "Time Invested", "description": "Practice for 30 minutes total", "target_value": 1800, "xp_reward": 120},
    {"type": "language_diversity", "title": "Polyglot", "description": "Practice 3 different languages", "target_value": 3, "xp_reward": 80},
    {"type": "hard_tests", "title": "Hard Worker", "description": "Complete 5 hard difficulty tests", "target_value": 5, "xp_reward": 130},
    {"type": "wpm_target", "title": "Speed Runner", "description": "Achieve 60+ WPM on any test", "target_value": 60, "xp_reward": 100},
]


class ChallengeService:

    def _get_week_start(self, dt: datetime = None) -> str:
        if dt is None:
            dt = datetime.utcnow()
        monday = dt - timedelta(days=dt.weekday())
        return monday.strftime("%Y-%m-%d")

    async def get_daily_challenges(self, user_id: str) -> dict:
        db = get_db()
        today = datetime.utcnow().strftime("%Y-%m-%d")

        existing = await db.codesprint_daily_challenges.find_one({"date": today})
        if not existing:
            templates = random.sample(DAILY_CHALLENGE_TEMPLATES, min(3, len(DAILY_CHALLENGE_TEMPLATES)))
            challenges = []
            for tmpl in templates:
                challenge = {
                    "date": today,
                    "language": tmpl["language"],
                    "category": tmpl["category"],
                    "difficulty": tmpl["difficulty"],
                    "duration_seconds": 180,
                    "xp_reward": tmpl["xp_reward"],
                    "bonus_xp": tmpl["bonus_xp"],
                    "title": tmpl["title"],
                    "description": tmpl["description"],
                    "deadline": datetime.utcnow().replace(hour=23, minute=59, second=59).isoformat(),
                    "created_at": datetime.utcnow(),
                }
                result = await db.codesprint_daily_challenges.insert_one(challenge)
                challenge["id"] = str(result.inserted_id)
                challenges.append(challenge)
        else:
            cursor = db.codesprint_daily_challenges.find({"date": today})
            challenges = []
            async for doc in cursor:
                doc["id"] = str(doc.pop("_id"))
                challenges.append(doc)

        completed_cursor = db.codesprint_user_challenges.find({
            "user_id": user_id,
            "challenge_type": "daily",
            "completed": True,
        })
        completed_ids = set()
        async for doc in completed_cursor:
            completed_ids.add(doc.get("challenge_id", ""))

        stats = await db.codesprint_user_stats.find_one({"user_id": user_id})
        streak = stats.get("current_streak", 0) if stats else 0

        result = []
        for ch in challenges:
            result.append({
                "id": ch.get("id", ""),
                "language": ch.get("language", ""),
                "category": ch.get("category", ""),
                "difficulty": ch.get("difficulty", ""),
                "duration_seconds": ch.get("duration_seconds", 180),
                "xp_reward": ch.get("xp_reward", 50),
                "bonus_xp": ch.get("bonus_xp", 25),
                "title": ch.get("title", ""),
                "description": ch.get("description", ""),
                "deadline": ch.get("deadline"),
                "completed": ch.get("id", "") in completed_ids,
                "completed_at": None,
            })

        return {"challenges": result, "date": today, "streak_days": streak}

    async def get_weekly_challenges(self, user_id: str) -> dict:
        db = get_db()
        week_start = self._get_week_start()
        week_end_dt = datetime.strptime(week_start, "%Y-%m-%d") + timedelta(days=6)
        week_end = week_end_dt.strftime("%Y-%m-%d")

        existing = await db.codesprint_weekly_challenges.find_one({"week_start": week_start})
        if not existing:
            templates = random.sample(WEEKLY_MISSION_TEMPLATES, min(4, len(WEEKLY_MISSION_TEMPLATES)))
            for tmpl in templates:
                await db.codesprint_weekly_challenges.insert_one({
                    "week_start": week_start,
                    "type": tmpl["type"],
                    "title": tmpl["title"],
                    "description": tmpl["description"],
                    "target_value": tmpl["target_value"],
                    "current_value": 0,
                    "language": tmpl.get("language"),
                    "xp_reward": tmpl["xp_reward"],
                    "completed": False,
                    "created_at": datetime.utcnow(),
                })

        week_start_dt = datetime.strptime(week_start, "%Y-%m-%d")
        week_end_of_day = datetime.combine(week_end_dt.date(), time(23, 59, 59))
        week_sessions = await db.codesprint_sessions.count_documents({
            "user_id": user_id,
            "created_at": {"$gte": week_start_dt, "$lte": week_end_of_day},
        })

        week_seconds_cursor = db.codesprint_sessions.aggregate([
            {"$match": {"user_id": user_id, "created_at": {"$gte": week_start_dt, "$lte": week_end_of_day}}},
            {"$group": {"_id": None, "total_seconds": {"$sum": "$completion_time"}}},
        ])
        week_seconds = 0
        async for doc in week_seconds_cursor:
            week_seconds = doc.get("total_seconds", 0)

        week_langs_cursor = db.codesprint_sessions.aggregate([
            {"$match": {"user_id": user_id, "created_at": {"$gte": week_start_dt, "$lte": week_end_of_day}}},
            {"$group": {"_id": "$language"}},
        ])
        week_langs = []
        async for doc in week_langs_cursor:
            week_langs.append(doc["_id"])

        week_accuracy_cursor = db.codesprint_sessions.aggregate([
            {"$match": {"user_id": user_id, "created_at": {"$gte": week_start_dt, "$lte": week_end_of_day}}},
            {"$group": {"_id": None, "avg_accuracy": {"$avg": "$accuracy"}}},
        ])
        week_avg_accuracy = 0
        async for doc in week_accuracy_cursor:
            week_avg_accuracy = doc.get("avg_accuracy", 0)

        week_hard = await db.codesprint_sessions.count_documents({
            "user_id": user_id, "difficulty": "hard",
            "created_at": {"$gte": week_start_dt, "$lte": week_end_of_day},
        })

        week_best_wpm_cursor = db.codesprint_sessions.aggregate([
            {"$match": {"user_id": user_id, "created_at": {"$gte": week_start_dt, "$lte": week_end_of_day}}},
            {"$group": {"_id": None, "best_wpm": {"$max": "$wpm"}}},
        ])
        week_best_wpm = 0
        async for doc in week_best_wpm_cursor:
            week_best_wpm = doc.get("best_wpm", 0)

        cursor = db.codesprint_weekly_challenges.find({"week_start": week_start})
        missions = []
        completed_count = 0
        async for doc in cursor:
            current_value = 0
            mtype = doc.get("type", "")
            if mtype == "tests_count":
                current_value = week_sessions
            elif mtype == "accuracy_target":
                current_value = round(week_avg_accuracy, 1)
            elif mtype == "practice_time":
                current_value = int(week_seconds)
            elif mtype == "language_diversity":
                current_value = len(week_langs)
            elif mtype == "hard_tests":
                current_value = week_hard
            elif mtype == "wpm_target":
                current_value = round(week_best_wpm, 1)

            target = doc.get("target_value", 1)
            completed = current_value >= target
            progress = min(1.0, current_value / target) if target > 0 else 0

            if completed:
                completed_count += 1

            doc_id = str(doc.pop("_id"))
            weekly_completed = await db.codesprint_user_challenges.find_one({
                "user_id": user_id, "challenge_id": doc_id, "completed": True,
            })

            missions.append({
                "id": doc_id,
                "type": mtype,
                "title": doc.get("title", ""),
                "description": doc.get("description", ""),
                "target_value": target,
                "current_value": current_value,
                "progress_pct": round(progress * 100, 1),
                "language": doc.get("language"),
                "xp_reward": doc.get("xp_reward", 100),
                "completed": weekly_completed is not None or completed,
            })

        return {
            "missions": missions,
            "week_start": week_start,
            "week_end": week_end,
            "completed_count": completed_count,
            "total_count": len(missions),
        }

    async def complete_challenge(self, user_id: str, challenge_id: str, challenge_type: str) -> dict:
        db = get_db()

        existing = await db.codesprint_user_challenges.find_one({
            "user_id": user_id, "challenge_id": challenge_id, "completed": True,
        })
        if existing:
            return {"success": False, "xp_earned": 0, "message": "Challenge already completed"}

        try:
            obj_id = ObjectId(challenge_id)
        except Exception:
            return {"success": False, "xp_earned": 0, "message": "Invalid challenge ID"}

        if challenge_type == "daily":
            challenge = await db.codesprint_daily_challenges.find_one({"_id": obj_id})
        else:
            challenge = await db.codesprint_weekly_challenges.find_one({"_id": obj_id})

        if not challenge:
            return {"success": False, "xp_earned": 0, "message": "Challenge not found"}

        if challenge_type == "daily":
            deadline_str = challenge.get("deadline")
            if deadline_str:
                try:
                    if isinstance(deadline_str, str):
                        deadline = datetime.fromisoformat(deadline_str)
                    else:
                        deadline = deadline_str
                    if datetime.utcnow() > deadline:
                        return {"success": False, "xp_earned": 0, "message": "Challenge deadline has passed"}
                except Exception:
                    pass

        xp = challenge.get("xp_reward", 50)
        bonus = challenge.get("bonus_xp", 0)
        total_xp = xp + bonus

        await db.codesprint_user_challenges.insert_one({
            "user_id": user_id,
            "challenge_id": challenge_id,
            "challenge_type": challenge_type,
            "completed": True,
            "completed_at": datetime.utcnow(),
            "xp_awarded": total_xp,
        })

        from app.services.gamification_service import gamification_service
        await gamification_service.award_xp(user_id, total_xp, "challenge", f"Completed {challenge_type} challenge")
        new_achievements = await gamification_service.check_and_award_achievements(user_id)

        return {"success": True, "xp_earned": total_xp, "bonus_xp": bonus, "message": f"Challenge completed! +{total_xp} XP", "achievements_unlocked": new_achievements}


challenge_service = ChallengeService()
