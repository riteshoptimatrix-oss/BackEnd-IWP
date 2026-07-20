from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId
from app.database import get_db


class TechLogoMatchService:

    # ── Health ──
    async def health_check(self) -> dict:
        return {
            "status": "ok",
            "module": "Tech Logo Match API v1",
            "collections": [
                "tech_logo_match_games",
                "tech_logo_match_statistics",
                "tech_logo_match_profiles",
                "tech_logo_match_settings",
            ],
        }

    # ── Save completed game ──
    async def save_game(self, user_id: str, data: dict) -> dict:
        db = get_db()
        now = datetime.utcnow()

        game = {
            "user_id": user_id,
            "category": data["category"],
            "difficulty": data["difficulty"],
            "mode": data["mode"],
            "score": data["score"],
            "correct": data["correct"],
            "wrong": data["wrong"],
            "accuracy": data["accuracy"],
            "avg_time": data["avg_time"],
            "best_streak": data["best_streak"],
            "stars": data["stars"],
            "total_questions": data["total_questions"],
            "duration_seconds": data["duration_seconds"],
            "created_at": now,
        }

        result = await db.tech_logo_match_games.insert_one(game)
        game_id = str(result.inserted_id)

        await self._update_statistics(user_id)
        streak = await self._update_streak(user_id, now)
        total = await db.tech_logo_match_games.count_documents({"user_id": user_id})

        xp_result = await self._award_game_xp(user_id, data, game_id, streak, now)
        new_achievements = await self._check_achievements(user_id)
        new_badges = await self._check_badges(user_id)

        return {
            "game_id": game_id,
            "saved": True,
            "total_games": total,
            "current_streak": streak,
            "xp_awarded": xp_result["xp_awarded"],
            "total_xp": xp_result["total_xp"],
            "level": xp_result["level"],
            "level_up": xp_result["level_up"],
            "new_achievements": new_achievements,
            "new_badges": new_badges,
        }

    # ── Aggregate statistics ──
    async def _update_statistics(self, user_id: str) -> None:
        db = get_db()
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": None,
                    "total_games": {"$sum": 1},
                    "total_correct": {"$sum": "$correct"},
                    "total_wrong": {"$sum": "$wrong"},
                    "total_stars": {"$sum": "$stars"},
                    "total_duration": {"$sum": "$duration_seconds"},
                    "sum_accuracy": {"$sum": "$accuracy"},
                    "sum_score": {"$sum": "$score"},
                    "highest_score": {"$max": "$score"},
                    "highest_accuracy": {"$max": "$accuracy"},
                    "fastest_time": {"$min": "$duration_seconds"},
                    "three_star_count": {
                        "$sum": {"$cond": [{"$eq": ["$stars", 3]}, 1, 0]}
                    },
                }
            },
        ]
        results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
        if not results:
            return

        r = results[0]
        total = r["total_games"]

        fav_cat = await self._favorite(db, user_id, "category")
        fav_diff = await self._favorite(db, user_id, "difficulty")
        fav_mode = await self._favorite(db, user_id, "mode")

        await db.tech_logo_match_statistics.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "total_games": total,
                    "total_correct": r["total_correct"],
                    "total_wrong": r["total_wrong"],
                    "total_stars": r["total_stars"],
                    "total_duration": r["total_duration"],
                    "average_accuracy": round(r["sum_accuracy"] / total, 1) if total > 0 else 0,
                    "average_score": round(r["sum_score"] / total, 1) if total > 0 else 0,
                    "highest_score": r["highest_score"],
                    "highest_accuracy": r["highest_accuracy"],
                    "fastest_completion": r["fastest_time"],
                    "three_star_count": r["three_star_count"],
                    "favorite_category": fav_cat,
                    "favorite_difficulty": fav_diff,
                    "favorite_mode": fav_mode,
                    "updated_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )

    # ── Streak calculation ──
    async def _update_streak(self, user_id: str, now: datetime) -> int:
        db = get_db()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        yesterday = today - timedelta(days=1)

        last_game = await db.tech_logo_match_games.find_one(
            {"user_id": user_id},
            sort=[("created_at", -1)],
            projection={"created_at": 1},
        )

        if not last_game:
            return 1

        last_date = last_game["created_at"].replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        if last_date == today:
            stats = await db.tech_logo_match_statistics.find_one({"user_id": user_id})
            return stats.get("current_streak", 1) if stats else 1

        if last_date == yesterday:
            stats = await db.tech_logo_match_statistics.find_one({"user_id": user_id})
            prev_streak = stats.get("current_streak", 0) if stats else 0
            return prev_streak + 1

        return 1

    # ── Favorite helper ──
    async def _favorite(self, db, user_id: str, field: str) -> Optional[str]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1},
        ]
        results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
        if results:
            return results[0]["_id"]
        return None

    # ── Get statistics ──
    async def get_statistics(self, user_id: str) -> dict:
        db = get_db()
        stats = await db.tech_logo_match_statistics.find_one({"user_id": user_id})
        if not stats:
            return {
                "total_games": 0,
                "total_correct": 0,
                "total_wrong": 0,
                "average_accuracy": 0,
                "average_score": 0,
                "highest_score": 0,
                "fastest_completion": None,
                "favorite_category": None,
                "favorite_difficulty": None,
                "favorite_mode": None,
                "current_streak": 0,
                "longest_streak": 0,
                "three_star_games": 0,
                "total_duration": 0,
            }
        return self._format_stats(stats)

    def _format_stats(self, stats: dict) -> dict:
        return {
            "total_games": stats.get("total_games", 0),
            "total_correct": stats.get("total_correct", 0),
            "total_wrong": stats.get("total_wrong", 0),
            "average_accuracy": stats.get("average_accuracy", 0),
            "average_score": stats.get("average_score", 0),
            "highest_score": stats.get("highest_score", 0),
            "fastest_completion": stats.get("fastest_completion"),
            "favorite_category": stats.get("favorite_category"),
            "favorite_difficulty": stats.get("favorite_difficulty"),
            "favorite_mode": stats.get("favorite_mode"),
            "current_streak": stats.get("current_streak", 0),
            "longest_streak": stats.get("longest_streak", 0),
            "three_star_games": stats.get("three_star_count", 0),
            "total_duration": stats.get("total_duration", 0),
        }

    # ── Game history ──
    async def get_game_history(
        self, user_id: str, page: int = 1, limit: int = 10,
        search: str = "", sort_by: str = "created_at",
        sort_order: int = -1, difficulty: str = "", mode: str = "",
        category: str = "",
    ) -> dict:
        db = get_db()
        query: dict = {"user_id": user_id}

        if search:
            query["$or"] = [
                {"category": {"$regex": search, "$options": "i"}},
                {"mode": {"$regex": search, "$options": "i"}},
                {"difficulty": {"$regex": search, "$options": "i"}},
            ]
        if difficulty:
            query["difficulty"] = difficulty
        if mode:
            query["mode"] = mode
        if category:
            query["category"] = category

        total = await db.tech_logo_match_games.count_documents(query)

        sort_field = sort_by if sort_by in ["score", "accuracy", "stars", "created_at", "duration_seconds"] else "created_at"
        skip = (page - 1) * limit

        cursor = db.tech_logo_match_games.find(query)
        cursor = cursor.sort(sort_field, sort_order).skip(skip).limit(limit)
        games = await cursor.to_list(None)

        return {
            "games": [self._format_game(g) for g in games],
            "total": total,
            "page": page,
            "limit": limit,
            "has_more": (page * limit) < total,
        }

    def _format_game(self, g: dict) -> dict:
        return {
            "id": str(g["_id"]),
            "category": g.get("category", ""),
            "difficulty": g.get("difficulty", ""),
            "mode": g.get("mode", ""),
            "score": g.get("score", 0),
            "correct": g.get("correct", 0),
            "wrong": g.get("wrong", 0),
            "accuracy": g.get("accuracy", 0),
            "avg_time": g.get("avg_time", 0),
            "best_streak": g.get("best_streak", 0),
            "stars": g.get("stars", 0),
            "total_questions": g.get("total_questions", 0),
            "duration_seconds": g.get("duration_seconds", 0),
            "created_at": g.get("created_at", datetime.utcnow()).isoformat(),
        }

    # ── Dashboard ──
    async def get_dashboard(self, user_id: str) -> dict:
        db = get_db()
        stats = await db.tech_logo_match_statistics.find_one({"user_id": user_id})

        recent = (
            db.tech_logo_match_games.find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(5)
        )
        recent_games = [self._format_game(g) for g in await recent.to_list(None)]

        if not stats:
            return {
                "total_games": 0,
                "total_stars": 0,
                "average_accuracy": 0,
                "current_streak": 0,
                "longest_streak": 0,
                "favorite_category": None,
                "favorite_difficulty": None,
                "favorite_mode": None,
                "best_score": 0,
                "highest_accuracy": 0,
                "fastest_completion": None,
                "recent_games": [],
            }

        return {
            "total_games": stats.get("total_games", 0),
            "total_stars": stats.get("total_stars", 0),
            "average_accuracy": stats.get("average_accuracy", 0),
            "current_streak": stats.get("current_streak", 0),
            "longest_streak": stats.get("longest_streak", 0),
            "favorite_category": stats.get("favorite_category"),
            "favorite_difficulty": stats.get("favorite_difficulty"),
            "favorite_mode": stats.get("favorite_mode"),
            "best_score": stats.get("highest_score", 0),
            "highest_accuracy": stats.get("highest_accuracy", 0),
            "fastest_completion": stats.get("fastest_completion"),
            "recent_games": recent_games,
        }

    # ── Profile ──
    async def get_profile(self, user_id: str, user: dict) -> dict:
        db = get_db()
        stats = await db.tech_logo_match_statistics.find_one({"user_id": user_id})

        three_star = stats.get("three_star_count", 0) if stats else 0
        total = stats.get("total_games", 0) if stats else 0

        return {
            "full_name": user.get("full_name", ""),
            "email": user.get("email", ""),
            "username": user.get("username", user.get("full_name", "")),
            "games_played": total,
            "games_won": three_star,
            "overall_accuracy": stats.get("average_accuracy", 0) if stats else 0,
            "best_score": stats.get("highest_score", 0) if stats else 0,
            "best_response_time": stats.get("fastest_completion") if stats else None,
            "favorite_technology": None,
            "favorite_category": stats.get("favorite_category") if stats else None,
            "favorite_difficulty": stats.get("favorite_difficulty") if stats else None,
            "current_streak": stats.get("current_streak", 0) if stats else 0,
            "longest_streak": stats.get("longest_streak", 0) if stats else 0,
            "total_stars": stats.get("total_stars", 0) if stats else 0,
            "registered": user.get("created_at", "").isoformat() if isinstance(user.get("created_at"), datetime) else str(user.get("created_at", "")),
        }

    # ── Settings ──
    async def get_settings(self, user_id: str) -> dict:
        db = get_db()
        settings = await db.tech_logo_match_settings.find_one({"user_id": user_id})
        if not settings:
            return {
                "sound_enabled": True,
                "animations_enabled": True,
                "timer_visible": True,
                "high_contrast": False,
                "reduced_motion": False,
                "preferred_difficulty": None,
                "preferred_category": None,
                "preferred_mode": None,
            }
        return {
            "sound_enabled": settings.get("sound_enabled", True),
            "animations_enabled": settings.get("animations_enabled", True),
            "timer_visible": settings.get("timer_visible", True),
            "high_contrast": settings.get("high_contrast", False),
            "reduced_motion": settings.get("reduced_motion", False),
            "preferred_difficulty": settings.get("preferred_difficulty"),
            "preferred_category": settings.get("preferred_category"),
            "preferred_mode": settings.get("preferred_mode"),
        }

    async def save_settings(self, user_id: str, data: dict) -> dict:
        db = get_db()
        update = {k: v for k, v in data.items() if v is not None}
        if not update:
            return await self.get_settings(user_id)

        await db.tech_logo_match_settings.update_one(
            {"user_id": user_id},
            {"$set": update},
            upsert=True,
        )
        return await self.get_settings(user_id)

    # ── Analytics ──
    async def get_analytics(self, user_id: str) -> dict:
        db = get_db()
        stats = await db.tech_logo_match_statistics.find_one({"user_id": user_id})

        if not stats:
            return self._empty_analytics()

        categories = await self._get_category_performance(db, user_id)
        modes = await self._get_mode_performance(db, user_id)
        difficulties = await self._get_difficulty_performance(db, user_id)
        heatmap = await self._get_heatmap(db, user_id)
        daily = await self._get_activity(db, user_id, "day")
        weekly = await self._get_activity(db, user_id, "week")
        monthly = await self._get_activity(db, user_id, "month")
        personal_bests = self._get_personal_bests(stats)
        insights = await self._get_insights(db, user_id, stats, categories, difficulties)

        recent = (
            db.tech_logo_match_games.find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(10)
        )
        recent_games = [self._format_game(g) for g in await recent.to_list(None)]

        total = stats.get("total_games", 0)
        total_correct = stats.get("total_correct", 0)
        total_wrong = stats.get("total_wrong", 0)
        overall_acc = round(
            (total_correct / (total_correct + total_wrong)) * 100, 1
        ) if (total_correct + total_wrong) > 0 else 0

        total_duration = stats.get("total_duration", 0)
        avg_resp = round(total_duration / total, 1) if total > 0 else 0

        return {
            "total_games": total,
            "total_stars": stats.get("total_stars", 0),
            "overall_accuracy": overall_acc,
            "average_accuracy": stats.get("average_accuracy", 0),
            "highest_score": stats.get("highest_score", 0),
            "average_score": stats.get("average_score", 0),
            "fastest_completion": stats.get("fastest_completion"),
            "average_response_time": avg_resp,
            "current_streak": stats.get("current_streak", 0),
            "longest_streak": stats.get("longest_streak", 0),
            "favorite_category": stats.get("favorite_category"),
            "favorite_difficulty": stats.get("favorite_difficulty"),
            "favorite_mode": stats.get("favorite_mode"),
            "categories": categories,
            "modes": modes,
            "difficulties": difficulties,
            "heatmap": heatmap,
            "daily_activity": daily,
            "weekly_activity": weekly,
            "monthly_activity": monthly,
            "personal_bests": personal_bests,
            "insights": insights,
            "recent_games": recent_games,
        }

    def _empty_analytics(self) -> dict:
        return {
            "total_games": 0, "total_stars": 0, "overall_accuracy": 0,
            "average_accuracy": 0, "highest_score": 0, "average_score": 0,
            "fastest_completion": None, "average_response_time": 0,
            "current_streak": 0, "longest_streak": 0,
            "favorite_category": None, "favorite_difficulty": None, "favorite_mode": None,
            "categories": [], "modes": [], "difficulties": [],
            "heatmap": [], "daily_activity": [], "weekly_activity": [], "monthly_activity": [],
            "personal_bests": [], "insights": [], "recent_games": [],
        }

    async def _get_category_performance(self, db, user_id: str) -> list:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$category",
                "games_played": {"$sum": 1},
                "average_accuracy": {"$avg": "$accuracy"},
                "average_score": {"$avg": "$score"},
                "total_stars": {"$sum": "$stars"},
                "completed_count": {
                    "$sum": {"$cond": [{"$gte": ["$stars", 1]}, 1, 0]}
                },
            }},
            {"$sort": {"games_played": -1}},
        ]
        results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
        out = []
        for r in results:
            total = r["games_played"]
            completed = r.get("completed_count", total)
            out.append({
                "category": r["_id"],
                "games_played": total,
                "average_accuracy": round(r.get("average_accuracy", 0), 1),
                "average_score": round(r.get("average_score", 0), 1),
                "completion_rate": round((completed / total) * 100, 1) if total else 0,
                "total_stars": r.get("total_stars", 0),
            })
        return out

    async def _get_mode_performance(self, db, user_id: str) -> list:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$mode",
                "games_played": {"$sum": 1},
                "average_accuracy": {"$avg": "$accuracy"},
                "average_time": {"$avg": "$avg_time"},
                "best_score": {"$max": "$score"},
            }},
            {"$sort": {"games_played": -1}},
        ]
        results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
        return [{
            "mode": r["_id"],
            "games_played": r["games_played"],
            "average_accuracy": round(r.get("average_accuracy", 0), 1),
            "average_time": round(r.get("average_time", 0), 1),
            "best_score": r.get("best_score", 0),
        } for r in results]

    async def _get_difficulty_performance(self, db, user_id: str) -> list:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$difficulty",
                "games_played": {"$sum": 1},
                "average_accuracy": {"$avg": "$accuracy"},
                "average_time": {"$avg": "$duration_seconds"},
                "average_score": {"$avg": "$score"},
                "stars_3_count": {
                    "$sum": {"$cond": [{"$eq": ["$stars", 3]}, 1, 0]}
                },
            }},
            {"$sort": {"games_played": -1}},
        ]
        results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
        out = []
        for r in results:
            total = r["games_played"]
            succeeded = r.get("stars_3_count", 0)
            out.append({
                "difficulty": r["_id"],
                "games_played": total,
                "average_accuracy": round(r.get("average_accuracy", 0), 1),
                "average_time": round(r.get("average_time", 0), 1),
                "success_rate": round((succeeded / total) * 100, 1) if total else 0,
                "average_score": round(r.get("average_score", 0), 1),
            })
        return out

    async def _get_heatmap(self, db, user_id: str) -> list:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                },
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ]
        results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
        return [{"date": r["_id"], "count": r["count"]} for r in results]

    async def _get_activity(self, db, user_id: str, group_by: str) -> list:
        fmt = {"day": "%Y-%m-%d", "week": "%Y-W%V", "month": "%Y-%m"}
        format_str = fmt.get(group_by, "%Y-%m-%d")
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": {
                    "$dateToString": {"format": format_str, "date": "$created_at"}
                },
                "games": {"$sum": 1},
                "accuracy": {"$avg": "$accuracy"},
            }},
            {"$sort": {"_id": 1}},
        ]
        results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
        return [{
            "date": r["_id"],
            "games": r["games"],
            "accuracy": round(r.get("accuracy", 0), 1),
        } for r in results]

    def _get_personal_bests(self, stats: dict) -> list:
        bests = []
        if stats.get("highest_score"):
            bests.append({"label": "Highest Score", "value": str(stats["highest_score"]), "icon": "trophy"})
        if stats.get("highest_accuracy"):
            bests.append({"label": "Highest Accuracy", "value": f"{stats['highest_accuracy']}%", "icon": "target"})
        if stats.get("fastest_completion"):
            sec = stats["fastest_completion"]
            m, s = divmod(sec, 60)
            bests.append({"label": "Fastest Completion", "value": f"{m}:{s:02d}", "icon": "clock"})
        if stats.get("current_streak", 0) > 0:
            bests.append({"label": "Current Streak", "value": f"{stats['current_streak']} days", "icon": "flame"})
        if stats.get("longest_streak", 0) > 0:
            bests.append({"label": "Longest Streak", "value": f"{stats['longest_streak']} days", "icon": "award"})
        if stats.get("favorite_category"):
            bests.append({"label": "Most Played Category", "value": stats["favorite_category"], "icon": "folder"})
        if stats.get("favorite_mode"):
            mode_label = stats["favorite_mode"].replace("-", " → ").title()
            bests.append({"label": "Favorite Mode", "value": mode_label, "icon": "zap"})
        return bests

    async def _get_insights(self, db, user_id: str, stats: dict, categories: list, difficulties: list) -> list:
        insights = []
        total = stats.get("total_games", 0)
        if total == 0:
            insights.append({"type": "info", "message": "Play your first Tech Logo Match game to receive personalized insights.", "direction": "neutral"})
            return insights

        if categories:
            best_cat = categories[0]
            if best_cat["games_played"] >= 2:
                insights.append({"type": "strength", "message": f"{best_cat['category']} is your strongest category with {best_cat['average_accuracy']}% accuracy.", "direction": "up"})
            if len(categories) >= 2:
                worst_cat = categories[-1]
                if worst_cat["average_accuracy"] < 70 and worst_cat["games_played"] >= 2:
                    insights.append({"type": "improvement", "message": f"{worst_cat['category']} could use more practice ({worst_cat['average_accuracy']}% accuracy).", "direction": "down"})

        for d in difficulties:
            if d["games_played"] >= 2 and d["difficulty"] == "expert" and d["success_rate"] > 50:
                insights.append({"type": "achievement", "message": f"Expert difficulty mastery! {d['success_rate']}% success rate across {d['games_played']} games.", "direction": "up"})
            elif d["difficulty"] == "easy" and d["average_accuracy"] > 90 and d["games_played"] >= 2:
                insights.append({"type": "milestone", "message": f"Easy difficulty mastered at {d['average_accuracy']}% — try Medium or Hard!", "direction": "up"})

        if stats.get("current_streak", 0) >= 3:
            insights.append({"type": "streak", "message": f"You're on a {stats['current_streak']}-day streak! Keep it going.", "direction": "up"})

        if stats.get("average_accuracy", 0) > 0:
            acc = stats["average_accuracy"]
            if acc >= 90:
                insights.append({"type": "performance", "message": f"Outstanding overall accuracy of {acc}%! You really know your technologies.", "direction": "up"})
            elif acc >= 70:
                insights.append({"type": "performance", "message": f"Good overall accuracy of {acc}%. Focus on weaker categories to improve.", "direction": "up"})
            else:
                insights.append({"type": "improvement", "message": f"Overall accuracy is {acc}%. Try practicing with Easy mode to build confidence.", "direction": "down"})

        if not insights:
            insights.append({"type": "info", "message": "Keep playing to unlock more detailed performance insights.", "direction": "neutral"})

        return insights

    async def export_analytics(self, user_id: str, format_type: str) -> str:
        import csv, io, json
        db = get_db()
        games = await db.tech_logo_match_games.find(
            {"user_id": user_id}
        ).sort("created_at", -1).to_list(None)

        if format_type == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Date", "Category", "Difficulty", "Mode", "Score", "Correct", "Wrong", "Accuracy", "AvgTime", "BestStreak", "Stars", "TotalQuestions", "Duration"])
            for g in games:
                writer.writerow([
                    g["created_at"].isoformat(), g.get("category", ""),
                    g.get("difficulty", ""), g.get("mode", ""),
                    g.get("score", 0), g.get("correct", 0),
                    g.get("wrong", 0), g.get("accuracy", 0),
                    g.get("avg_time", 0), g.get("best_streak", 0),
                    g.get("stars", 0), g.get("total_questions", 0),
                    g.get("duration_seconds", 0),
                ])
            return output.getvalue()

        data = []
        for g in games:
            data.append({
                "date": g["created_at"].isoformat(),
                "category": g.get("category", ""),
                "difficulty": g.get("difficulty", ""),
                "mode": g.get("mode", ""),
                "score": g.get("score", 0),
                "correct": g.get("correct", 0),
                "wrong": g.get("wrong", 0),
                "accuracy": g.get("accuracy", 0),
                "avg_time": g.get("avg_time", 0),
                "best_streak": g.get("best_streak", 0),
                "stars": g.get("stars", 0),
                "total_questions": g.get("total_questions", 0),
                "duration_seconds": g.get("duration_seconds", 0),
            })
        return json.dumps(data, indent=2)

    # ═══════════════════════════════════════════
    # GAMIFICATION — XP, Levels, Achievements, Badges
    # ═══════════════════════════════════════════

    ACHIEVEMENTS = [
        {"id": "first-game", "title": "First Logo Identified", "description": "Complete your first Tech Logo Match game", "icon": "🎯", "xp_reward": 100, "check": lambda s, u, db, st: st.get("total_games", 0) >= 1},
        {"id": "games-10", "title": "Getting Started", "description": "Play 10 games", "icon": "🎮", "xp_reward": 200, "check": lambda s, u, db, st: st.get("total_games", 0) >= 10},
        {"id": "games-50", "title": "Dedicated Learner", "description": "Play 50 games", "icon": "🔥", "xp_reward": 500, "check": lambda s, u, db, st: st.get("total_games", 0) >= 50},
        {"id": "games-100", "title": "Tech Logo Master", "description": "Play 100 games", "icon": "👑", "xp_reward": 1000, "check": lambda s, u, db, st: st.get("total_games", 0) >= 100},
        {"id": "perfect-game", "title": "Perfect Recognition", "description": "Complete a game with 100% accuracy", "icon": "💎", "xp_reward": 300, "check": lambda s, u, db, st: st.get("highest_accuracy", 0) >= 100},
        {"id": "perfect-10", "title": "Perfectionist", "description": "Complete 10 perfect games", "icon": "🌟", "xp_reward": 1000, "check": lambda s, u, db, st: st.get("three_star_games", 0) >= 10},
        {"id": "streak-7", "title": "Week Warrior", "description": "Maintain a 7-day streak", "icon": "📅", "xp_reward": 500, "check": lambda s, u, db, st: st.get("longest_streak", 0) >= 7},
        {"id": "streak-30", "title": "Monthly Master", "description": "Maintain a 30-day streak", "icon": "🗓️", "xp_reward": 2000, "check": lambda s, u, db, st: st.get("longest_streak", 0) >= 30},
        {"id": "master-frameworks", "title": "Framework Expert", "description": "Master the Frameworks category", "icon": "⚛️", "xp_reward": 500, "check": lambda s, u, db, st: s._category_mastered(db, u, "Frameworks")},
        {"id": "master-languages", "title": "Language Expert", "description": "Master the Languages category", "icon": "🔤", "xp_reward": 500, "check": lambda s, u, db, st: s._category_mastered(db, u, "Languages")},
        {"id": "master-styling", "title": "Styling Expert", "description": "Master the Styling category", "icon": "🎨", "xp_reward": 500, "check": lambda s, u, db, st: s._category_mastered(db, u, "Styling")},
        {"id": "speed-demon", "title": "Speed Demon", "description": "Average response time under 10 seconds", "icon": "⚡", "xp_reward": 500, "check": lambda s, u, db, st: s._check_speed_demon(db, u)},
        {"id": "explorer", "title": "Frontend Explorer", "description": "Play every technology category", "icon": "🧭", "xp_reward": 300, "check": lambda s, u, db, st: s._check_explorer(db, u)},
        {"id": "collector", "title": "Mode Collector", "description": "Use every game mode", "icon": "🎯", "xp_reward": 300, "check": lambda s, u, db, st: s._check_mode_collector(db, u)},
        {"id": "three-star-50", "title": "Star Collector", "description": "Earn 50 three-star games", "icon": "⭐", "xp_reward": 1000, "check": lambda s, u, db, st: st.get("three_star_games", 0) >= 50},
    ]

    BADGES = [
        {"id": "games-bronze", "name": "Bronze Gamer", "description": "Play 10 games", "icon": "🥉", "tier": "bronze", "check": lambda s, u, db, st: st.get("total_games", 0) >= 10},
        {"id": "games-silver", "name": "Silver Gamer", "description": "Play 50 games", "icon": "🥈", "tier": "silver", "check": lambda s, u, db, st: st.get("total_games", 0) >= 50},
        {"id": "games-gold", "name": "Gold Gamer", "description": "Play 100 games", "icon": "🥇", "tier": "gold", "check": lambda s, u, db, st: st.get("total_games", 0) >= 100},
        {"id": "games-platinum", "name": "Platinum Gamer", "description": "Play 250 games", "icon": "💿", "tier": "platinum", "check": lambda s, u, db, st: st.get("total_games", 0) >= 250},
        {"id": "games-diamond", "name": "Diamond Gamer", "description": "Play 500 games", "icon": "💎", "tier": "diamond", "check": lambda s, u, db, st: st.get("total_games", 0) >= 500},
        {"id": "streak-bronze", "name": "Streak Starter", "description": "7-day streak", "icon": "🔥", "tier": "bronze", "check": lambda s, u, db, st: st.get("longest_streak", 0) >= 7},
        {"id": "streak-silver", "name": "Streak Builder", "description": "14-day streak", "icon": "🔥", "tier": "silver", "check": lambda s, u, db, st: st.get("longest_streak", 0) >= 14},
        {"id": "streak-gold", "name": "Streak Master", "description": "30-day streak", "icon": "🔥", "tier": "gold", "check": lambda s, u, db, st: st.get("longest_streak", 0) >= 30},
        {"id": "accuracy-gold", "name": "Accuracy King", "description": "90%+ average accuracy", "icon": "🎯", "tier": "gold", "check": lambda s, u, db, st: st.get("average_accuracy", 0) >= 90},
        {"id": "speed-silver", "name": "Quick Thinker", "description": "Average response time under 15s", "icon": "⚡", "tier": "silver", "check": lambda s, u, db, st: s._check_speed_badge(db, u)},
    ]

    RANKS = [
        (0, "Beginner", "🌱"), (500, "Explorer", "🔍"), (1500, "Frontend Learner", "📖"),
        (3000, "Frontend Developer", "💻"), (5000, "Frontend Engineer", "⚙️"),
        (8000, "Sr. Frontend Engineer", "🔧"), (12000, "Frontend Architect", "🏗️"),
        (20000, "Master", "👑"), (35000, "Legend", "🌟"),
    ]

    DAILY_CHALLENGES = [
        {"id": "play-any", "title": "Daily Practice", "description": "Complete any Tech Logo Match game", "type": "play_any", "target": 1, "xp_reward": 50},
        {"id": "perfect-accuracy", "title": "Perfect Round", "description": "Complete a game with 100% accuracy", "type": "perfect_accuracy", "target": 1, "xp_reward": 100},
        {"id": "fast-completion", "title": "Speed Round", "description": "Average under 20s per question", "type": "fast_completion", "target": 1, "xp_reward": 100},
        {"id": "high-score", "title": "High Scorer", "description": "Score over 1000 points in a game", "type": "high_score", "target": 1, "xp_reward": 150},
        {"id": "frameworks-focus", "title": "Framework Focus", "description": "Play a Frameworks category game", "type": "category_focus", "target": 1, "xp_reward": 75, "category": "Frameworks"},
        {"id": "languages-focus", "title": "Language Focus", "description": "Play a Languages category game", "type": "category_focus", "target": 1, "xp_reward": 75, "category": "Languages"},
        {"id": "styling-focus", "title": "Styling Focus", "description": "Play a Styling category game", "type": "category_focus", "target": 1, "xp_reward": 75, "category": "Styling"},
        {"id": "tools-focus", "title": "Tools Focus", "description": "Play a Build & Dev Tools game", "type": "category_focus", "target": 1, "xp_reward": 75, "category": "Build & Dev Tools"},
        {"id": "platforms-focus", "title": "Platform Focus", "description": "Play a Platforms & Services game", "type": "category_focus", "target": 1, "xp_reward": 75, "category": "Platforms & Services"},
        {"id": "logo-to-name-mode", "title": "Name That Logo", "description": "Play a Logo→Name mode game", "type": "mode_focus", "target": 1, "xp_reward": 75, "mode": "logo-to-name"},
        {"id": "name-to-logo-mode", "title": "Logo Picker", "description": "Play a Name→Logo mode game", "type": "mode_focus", "target": 1, "xp_reward": 75, "mode": "name-to-logo"},
        {"id": "mixed-mode", "title": "Mixed Master", "description": "Play a Mixed Challenge mode game", "type": "mode_focus", "target": 1, "xp_reward": 100, "mode": "mixed"},
    ]

    WEEKLY_CHALLENGES = [
        {"id": "weekly-games-5", "title": "Consistency", "description": "Complete 5 games this week", "type": "weekly_games", "target": 5, "xp_reward": 200},
        {"id": "weekly-games-10", "title": "Dedication", "description": "Complete 10 games this week", "type": "weekly_games", "target": 10, "xp_reward": 500},
        {"id": "weekly-all-categories", "title": "Category Explorer", "description": "Play every category this week", "type": "weekly_categories", "target": 6, "xp_reward": 300},
        {"id": "weekly-all-modes", "title": "Mode Master", "description": "Play every game mode this week", "type": "weekly_modes", "target": 4, "xp_reward": 300},
        {"id": "weekly-accuracy-90", "title": "Accuracy Champion", "description": "Maintain 90%+ average accuracy", "type": "weekly_accuracy", "target": 1, "xp_reward": 400},
        {"id": "weekly-xp-500", "title": "XP Hunter", "description": "Earn 500 XP this week", "type": "weekly_xp", "target": 500, "xp_reward": 600},
    ]

    # ── XP Awarding ──
    async def _award_game_xp(self, user_id: str, data: dict, game_id: str, streak: int, now: datetime) -> dict:
        db = get_db()
        xp = 100

        if data.get("accuracy", 0) >= 90: xp += 50
        elif data.get("accuracy", 0) >= 70: xp += 25

        avg = data.get("avg_time", 999)
        if avg <= 5: xp += 75
        elif avg <= 10: xp += 50
        elif avg <= 15: xp += 25

        if data.get("stars", 0) == 3: xp += 50
        elif data.get("stars", 0) == 2: xp += 20

        if streak >= 3: xp += streak * 5

        if data.get("wrong", 0) == 0 and data.get("total_questions", 0) > 0: xp += 100

        first_today = await self._check_first_game_today(user_id)
        if first_today: xp += 25

        dc_done = await self._check_daily_challenge_completion(user_id, data)
        if dc_done: xp += 50
        wc_done = await self._check_weekly_challenge_progress(user_id, data)
        if wc_done: xp += 100

        xp = min(xp, 1000)

        await db.tech_logo_match_xp.insert_one({
            "user_id": user_id, "xp": xp, "reason": "game_completed",
            "game_id": game_id, "created_at": now,
        })

        pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": None, "total": {"$sum": "$xp"}}}]
        total_result = await db.tech_logo_match_xp.aggregate(pipeline).to_list(None)
        total_xp = total_result[0]["total"] if total_result else xp

        level_info = self._calculate_level(total_xp)

        await self._create_notification(user_id, "xp", f"+{xp} XP", f"Earned {xp} XP from completing a game", now)

        return {"xp_awarded": xp, "total_xp": total_xp, "level": level_info["level"], "level_up": level_info["level_up"]}

    async def _check_first_game_today(self, user_id: str) -> bool:
        db = get_db()
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        count = await db.tech_logo_match_xp.count_documents({
            "user_id": user_id, "reason": "game_completed", "created_at": {"$gte": today_start},
        })
        return count <= 1

    def _calculate_level(self, total_xp: int) -> dict:
        level = 1
        while True:
            needed = 250 * (level ** 1.5)
            if total_xp < needed: break
            total_xp -= needed
            level += 1
        xp_for_next = int(250 * (level ** 1.5))
        progress = round((total_xp / xp_for_next) * 100, 1) if xp_for_next > 0 else 0

        rank = self.RANKS[0][0]
        rank_title = self.RANKS[0][1]
        rank_icon = self.RANKS[0][2]
        cumulative = 0
        for xp_req, title, icon in self.RANKS:
            if cumulative + xp_req <= total_xp:
                rank_title = title
                rank_icon = icon
            cumulative += xp_req

        return {"level": level, "current_xp": int(total_xp), "xp_for_next": xp_for_next, "progress": progress, "rank": rank_title, "rank_icon": rank_icon, "level_up": level > 1}

    async def get_player_level(self, user_id: str) -> dict:
        db = get_db()
        pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": None, "total": {"$sum": "$xp"}}}]
        result = await db.tech_logo_match_xp.aggregate(pipeline).to_list(None)
        total_xp = result[0]["total"] if result else 0
        return self._calculate_level(total_xp)

    # ── Achievements ──
    async def _check_achievements(self, user_id: str) -> list:
        db = get_db()
        stats = await db.tech_logo_match_statistics.find_one({"user_id": user_id}) or {}
        new_unlocks = []
        for ach in self.ACHIEVEMENTS:
            existing = await db.tech_logo_match_achievements.find_one({"user_id": user_id, "achievement_id": ach["id"]})
            if existing: continue
            if ach["check"](self, user_id, db, stats):
                now = datetime.utcnow()
                await db.tech_logo_match_achievements.insert_one({
                    "user_id": user_id, "achievement_id": ach["id"],
                    "title": ach["title"], "description": ach["description"],
                    "icon": ach["icon"], "xp_reward": ach["xp_reward"],
                    "unlocked_at": now,
                })
                await db.tech_logo_match_xp.insert_one({
                    "user_id": user_id, "xp": ach["xp_reward"], "reason": f"achievement_{ach['id']}",
                    "created_at": now,
                })
                await self._create_notification(user_id, "achievement", f"Achievement: {ach['title']}", ach["description"], now)
                new_unlocks.append({
                    "id": ach["id"], "title": ach["title"], "description": ach["description"],
                    "icon": ach["icon"], "xp_reward": ach["xp_reward"], "newly_unlocked": True,
                })
        return new_unlocks

    async def get_achievements(self, user_id: str) -> list:
        db = get_db()
        stats = await db.tech_logo_match_statistics.find_one({"user_id": user_id}) or {}
        out = []
        for ach in self.ACHIEVEMENTS:
            unlocked = await db.tech_logo_match_achievements.find_one({"user_id": user_id, "achievement_id": ach["id"]})
            out.append({
                "id": ach["id"], "title": ach["title"], "description": ach["description"],
                "icon": ach["icon"], "xp_reward": ach["xp_reward"],
                "progress_current": 1.0 if unlocked else 0.0,
                "progress_target": 1.0,
                "unlocked": bool(unlocked),
                "unlocked_at": unlocked["unlocked_at"].isoformat() if unlocked else None,
            })
        return out

    def _category_mastered(self, db, user_id: str, category: str) -> bool:
        import asyncio
        pipeline = [
            {"$match": {"user_id": user_id, "category": {"$regex": category, "$options": "i"}}},
            {"$group": {"_id": None, "avg_acc": {"$avg": "$accuracy"}, "count": {"$sum": 1}}},
        ]
        results = asyncio.get_event_loop().run_until_complete(
            db.tech_logo_match_games.aggregate(pipeline).to_list(None)
        ) if hasattr(asyncio, 'get_event_loop') else []
        # Use synchronous approach instead
        return False

    async def _check_speed_demon(self, db, user_id: str) -> bool:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": None, "avg_time": {"$avg": "$avg_time"}}},
        ]
        results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
        return results and results[0].get("avg_time", 999) < 10

    async def _check_explorer(self, db, user_id: str) -> bool:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$category"}},
        ]
        results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
        cats = {"Frameworks", "Languages", "Styling", "Build & Dev Tools", "Platforms & Services"}
        played = {r["_id"] for r in results}
        return cats.issubset(played)

    async def _check_mode_collector(self, db, user_id: str) -> bool:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$mode"}},
        ]
        results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
        modes = {"logo-to-name", "name-to-logo", "logo-to-category", "mixed"}
        played = {r["_id"] for r in results}
        return modes.issubset(played)

    # ── Badges ──
    async def _check_badges(self, user_id: str) -> list:
        db = get_db()
        stats = await db.tech_logo_match_statistics.find_one({"user_id": user_id}) or {}
        new_unlocks = []
        for badge in self.BADGES:
            existing = await db.tech_logo_match_badges.find_one({"user_id": user_id, "badge_id": badge["id"]})
            if existing: continue
            if badge["check"](self, user_id, db, stats):
                now = datetime.utcnow()
                await db.tech_logo_match_badges.insert_one({
                    "user_id": user_id, "badge_id": badge["id"],
                    "name": badge["name"], "description": badge["description"],
                    "icon": badge["icon"], "tier": badge["tier"],
                    "unlocked_at": now,
                })
                xp_reward = {"bronze": 50, "silver": 100, "gold": 200, "platinum": 300, "diamond": 500}.get(badge["tier"], 50)
                await db.tech_logo_match_xp.insert_one({
                    "user_id": user_id, "xp": xp_reward, "reason": f"badge_{badge['id']}",
                    "created_at": now,
                })
                await self._create_notification(user_id, "badge", f"Badge: {badge['name']}", badge["description"], now)
                new_unlocks.append({
                    "id": badge["id"], "name": badge["name"], "description": badge["description"],
                    "icon": badge["icon"], "tier": badge["tier"], "newly_unlocked": True,
                })
        return new_unlocks

    async def get_badges(self, user_id: str) -> list:
        db = get_db()
        stats = await db.tech_logo_match_statistics.find_one({"user_id": user_id}) or {}
        out = []
        for badge in self.BADGES:
            unlocked = await db.tech_logo_match_badges.find_one({"user_id": user_id, "badge_id": badge["id"]})
            out.append({
                "id": badge["id"], "name": badge["name"], "description": badge["description"],
                "icon": badge["icon"], "tier": badge["tier"],
                "unlocked": bool(unlocked),
                "unlocked_at": unlocked["unlocked_at"].isoformat() if unlocked else None,
            })
        return out

    async def _check_speed_badge(self, db, user_id: str) -> bool:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": None, "avg_time": {"$avg": "$avg_time"}}},
        ]
        results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
        return results and results[0].get("avg_time", 999) < 15

    # ── Leaderboards ──
    async def get_leaderboard(self, user_id: str, metric: str, scope: str, page: int, limit: int) -> dict:
        db = get_db()
        match: dict = {}
        if scope != "overall":
            match["category"] = {"$regex": scope, "$options": "i"}

        sort_field = {"xp": "xp", "accuracy": "accuracy", "streak": "streak", "score": "score", "games": "games"}
        group_field = sort_field.get(metric, "xp")

        group_stage = {"_id": "$user_id", "value": {"$sum": 1 if metric == "games" else ("$xp" if metric == "xp" else f"${metric}")}}
        if metric == "xp":
            group_stage = {"_id": "$user_id", "value": {"$sum": "$xp"}}
        elif metric == "accuracy":
            group_stage = {"_id": "$user_id", "value": {"$avg": "$accuracy"}}
        elif metric == "games":
            group_stage = {"_id": "$user_id", "value": {"$sum": 1}}
        else:
            group_stage = {"_id": "$user_id", "value": {"$max": f"${metric}"}}

        try:
            pipeline = [
                {"$match": {"user_id": {"$ne": None}}},
                {"$group": group_stage},
                {"$sort": {"value": -1}},
                {"$skip": (page - 1) * limit},
                {"$limit": limit},
            ]
            results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
        except Exception:
            results = []

        entries = []
        for i, r in enumerate(results):
            uid = r["_id"]
            uinfo = await db.users.find_one({"_id": uid}) if uid else None
            level_info = await self.get_player_level(uid) if uid else {}
            entries.append({
                "rank": (page - 1) * limit + i + 1,
                "user_id": str(uid) if uid else "",
                "username": uinfo.get("full_name", "Unknown") if uinfo else "Unknown",
                "avatar": None,
                "value": round(r.get("value", 0), 1) if isinstance(r.get("value"), (int, float)) else 0,
                "level": level_info.get("level", 1),
                "rank_title": level_info.get("rank", "Beginner"),
            })

        total_pipeline = [{"$match": {"user_id": {"$ne": None}}}, {"$group": {"_id": None, "total": {"$sum": 1}}}]
        total_result = await db.tech_logo_match_games.aggregate(total_pipeline).to_list(None)
        total = total_result[0]["total"] if total_result else 0

        my_rank_entry = None
        my_rank = await self.get_player_rank(user_id, metric, scope)
        if my_rank["rank"] > 0:
            my_rank_entry = {
                "rank": my_rank["rank"],
                "user_id": user_id,
                "username": "You",
                "avatar": None,
                "value": my_rank["value"],
                "level": (await self.get_player_level(user_id)).get("level", 1),
                "rank_title": (await self.get_player_level(user_id)).get("rank", "Beginner"),
            }

        return {
            "entries": entries,
            "total": total,
            "page": page,
            "limit": limit,
            "has_more": (page * limit) < total,
            "my_rank": my_rank_entry,
            "metric": metric,
            "scope": scope,
        }

    async def get_player_rank(self, user_id: str, metric: str, scope: str) -> dict:
        db = get_db()
        match: dict = {"user_id": user_id}
        if scope != "overall":
            match["category"] = {"$regex": scope, "$options": "i"}

        if metric == "xp":
            pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": None, "total": {"$sum": "$xp"}}}]
        elif metric == "accuracy":
            pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": None, "total": {"$avg": "$accuracy"}}}]
        elif metric == "games":
            pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": None, "total": {"$sum": 1}}}]
        else:
            pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": None, "total": {"$max": f"${metric}"}}}]

        result = await db.tech_logo_match_games.aggregate(pipeline).to_list(None) if metric != "xp" else []
        if metric == "xp":
            xp_result = await db.tech_logo_match_xp.aggregate([{"$match": {"user_id": user_id}}, {"$group": {"_id": None, "total": {"$sum": "$xp"}}}]).to_list(None)
            value = xp_result[0]["total"] if xp_result else 0
        else:
            value = result[0]["total"] if result else 0

        scope_match = {} if scope == "overall" else {"category": {"$regex": scope, "$options": "i"}}
        if metric == "xp":
            rank_pipeline = [
                {"$group": {"_id": "$user_id", "value": {"$sum": "$xp"}}},
                {"$sort": {"value": -1}},
            ]
            all_results = await db.tech_logo_match_xp.aggregate(rank_pipeline).to_list(None)
        else:
            sort_dir = -1
            val_field = f"${metric}"
            if metric == "accuracy":
                val_field = {"$avg": f"${metric}"}
            rank_pipeline = [
                {"$match": scope_match},
                {"$group": {"_id": "$user_id", "value": val_field}},
                {"$sort": {"value": sort_dir}},
            ]
            all_results = await db.tech_logo_match_games.aggregate(rank_pipeline).to_list(None)

        rank = 1
        for r in all_results:
            if str(r["_id"]) == user_id: break
            rank += 1
        else:
            rank = 0

        return {"rank": rank, "total": len(all_results), "value": round(value, 1) if isinstance(value, (int, float)) else 0, "metric": metric}

    # ── Daily Challenge ──
    async def get_daily_challenge(self, user_id: str) -> dict:
        db = get_db()
        today_key = datetime.utcnow().strftime("%Y-%m-%d")
        import hashlib
        idx = int(hashlib.md5(today_key.encode()).hexdigest(), 16) % len(self.DAILY_CHALLENGES)
        template = self.DAILY_CHALLENGES[idx]
        expires = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)

        existing = await db.tech_logo_match_daily_challenges.find_one({"user_id": user_id, "date": today_key})
        if existing:
            return {
                "challenge": {"id": existing["challenge_id"], "title": existing["title"], "description": existing["description"], "type": existing["type"], "target": existing["target"], "progress": existing.get("progress", 0), "completed": existing.get("completed", False), "xp_reward": existing.get("xp_reward", 0), "expires_at": expires.isoformat()},
                "completed": existing.get("completed", False),
            }

        await db.tech_logo_match_daily_challenges.insert_one({
            "user_id": user_id, "date": today_key, "challenge_id": template["id"],
            "title": template["title"], "description": template["description"],
            "type": template["type"], "target": template["target"],
            "xp_reward": template["xp_reward"], "progress": 0, "completed": False,
            "category": template.get("category"), "mode": template.get("mode"),
            "created_at": datetime.utcnow(),
        })

        return {
            "challenge": {"id": template["id"], "title": template["title"], "description": template["description"], "type": template["type"], "target": template["target"], "progress": 0, "completed": False, "xp_reward": template["xp_reward"], "expires_at": expires.isoformat()},
            "completed": False,
        }

    async def _check_daily_challenge_completion(self, user_id: str, data: dict) -> bool:
        db = get_db()
        today_key = datetime.utcnow().strftime("%Y-%m-%d")
        dc = await db.tech_logo_match_daily_challenges.find_one({"user_id": user_id, "date": today_key})
        if not dc or dc.get("completed"): return False

        progress = 0
        completed = False
        t = dc["type"]
        if t == "play_any":
            progress = 1
            completed = True
        elif t == "perfect_accuracy":
            if data.get("accuracy", 0) >= 100:
                progress = 1; completed = True
        elif t == "fast_completion":
            if data.get("avg_time", 999) <= 20:
                progress = 1; completed = True
        elif t == "high_score":
            if data.get("score", 0) >= 1000:
                progress = 1; completed = True
        elif t == "category_focus":
            cat = dc.get("category", "").lower()
            if cat and cat in data.get("category", "").lower():
                progress = 1; completed = True
        elif t == "mode_focus":
            mode = dc.get("mode", "")
            if mode and mode == data.get("mode", ""):
                progress = 1; completed = True

        if completed:
            await db.tech_logo_match_daily_challenges.update_one(
                {"_id": dc["_id"]}, {"$set": {"progress": progress, "completed": True}}
            )
            await db.tech_logo_match_xp.insert_one({
                "user_id": user_id, "xp": dc["xp_reward"], "reason": "daily_challenge",
                "created_at": datetime.utcnow(),
            })
            await self._create_notification(user_id, "challenge", "Daily Challenge Complete!", f"Earned {dc['xp_reward']} XP", datetime.utcnow())
            return True
        return False

    # ── Weekly Challenge ──
    async def get_weekly_challenge(self, user_id: str) -> dict:
        db = get_db()
        import datetime as dt
        today = datetime.utcnow()
        week_key = today.strftime("%Y-W%V")
        expires = today + dt.timedelta(days=(6 - today.weekday()))
        expires = expires.replace(hour=23, minute=59, second=59, microsecond=999999)

        import hashlib
        idx = int(hashlib.md5(week_key.encode()).hexdigest(), 16) % len(self.WEEKLY_CHALLENGES)
        template = self.WEEKLY_CHALLENGES[idx]

        existing = await db.tech_logo_match_weekly_challenges.find_one({"user_id": user_id, "week": week_key})
        if existing:
            return {
                "challenge": {"id": existing["challenge_id"], "title": existing["title"], "description": existing["description"], "type": existing["type"], "target": existing["target"], "progress": existing.get("progress", 0), "completed": existing.get("completed", False), "xp_reward": existing.get("xp_reward", 0), "expires_at": expires.isoformat()},
                "completed": existing.get("completed", False),
            }

        await db.tech_logo_match_weekly_challenges.insert_one({
            "user_id": user_id, "week": week_key, "challenge_id": template["id"],
            "title": template["title"], "description": template["description"],
            "type": template["type"], "target": template["target"],
            "xp_reward": template["xp_reward"], "progress": 0, "completed": False,
            "created_at": datetime.utcnow(),
        })

        return {
            "challenge": {"id": template["id"], "title": template["title"], "description": template["description"], "type": template["type"], "target": template["target"], "progress": 0, "completed": False, "xp_reward": template["xp_reward"], "expires_at": expires.isoformat()},
            "completed": False,
        }

    async def _check_weekly_challenge_progress(self, user_id: str, data: dict) -> bool:
        db = get_db()
        week_key = datetime.utcnow().strftime("%Y-W%V")
        wc = await db.tech_logo_match_weekly_challenges.find_one({"user_id": user_id, "week": week_key})
        if not wc or wc.get("completed"): return False

        t = wc["type"]
        progress = wc.get("progress", 0)
        completed = False

        if t == "weekly_games":
            count = await db.tech_logo_match_games.count_documents({"user_id": user_id})
            progress = count
            completed = progress >= wc["target"]
        elif t == "weekly_categories":
            pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": "$category"}}]
            results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
            progress = len(results)
            completed = progress >= wc["target"]
        elif t == "weekly_modes":
            pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": "$mode"}}]
            results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
            progress = len(results)
            completed = progress >= wc["target"]
        elif t == "weekly_accuracy":
            pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": None, "avg": {"$avg": "$accuracy"}}}]
            results = await db.tech_logo_match_games.aggregate(pipeline).to_list(None)
            avg = results[0]["avg"] if results else 0
            progress = 1 if avg >= 90 else 0
            completed = progress >= 1
        elif t == "weekly_xp":
            pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": None, "total": {"$sum": "$xp"}}}]
            results = await db.tech_logo_match_xp.aggregate(pipeline).to_list(None)
            progress = results[0]["total"] if results else 0
            completed = progress >= wc["target"]

        if completed or progress != wc.get("progress", 0):
            await db.tech_logo_match_weekly_challenges.update_one(
                {"_id": wc["_id"]}, {"$set": {"progress": min(progress, wc["target"]), "completed": completed}}
            )
            if completed:
                await db.tech_logo_match_xp.insert_one({
                    "user_id": user_id, "xp": wc["xp_reward"], "reason": "weekly_challenge",
                    "created_at": datetime.utcnow(),
                })
                await self._create_notification(user_id, "challenge", "Weekly Challenge Complete!", f"Earned {wc['xp_reward']} XP", datetime.utcnow())
                return True
        return False

    async def get_challenge_history(self, user_id: str) -> list:
        db = get_db()
        daily = await db.tech_logo_match_daily_challenges.find({"user_id": user_id, "completed": True}).sort("created_at", -1).to_list(50)
        weekly = await db.tech_logo_match_weekly_challenges.find({"user_id": user_id, "completed": True}).sort("created_at", -1).to_list(50)
        out = []
        for d in daily:
            out.append({"id": str(d["_id"]), "title": d.get("title", ""), "type": d.get("type", ""), "challenge_type": "daily", "completed": True, "xp_reward": d.get("xp_reward", 0), "completed_at": d.get("created_at", datetime.utcnow()).isoformat()})
        for w in weekly:
            out.append({"id": str(w["_id"]), "title": w.get("title", ""), "type": w.get("type", ""), "challenge_type": "weekly", "completed": True, "xp_reward": w.get("xp_reward", 0), "completed_at": w.get("created_at", datetime.utcnow()).isoformat()})
        out.sort(key=lambda x: x["completed_at"], reverse=True)
        return out[:50]

    # ── Rewards ──
    async def get_rewards(self, user_id: str) -> dict:
        db = get_db()
        pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": None, "total": {"$sum": "$xp"}}}]
        result = await db.tech_logo_match_xp.aggregate(pipeline).to_list(None)
        total_xp = result[0]["total"] if result else 0
        level_info = self._calculate_level(total_xp)

        recent = db.tech_logo_match_xp.find({"user_id": user_id}).sort("created_at", -1).limit(50)
        rewards = []
        icons = {"game_completed": "zap", "achievement": "trophy", "badge": "award", "daily_challenge": "calendar", "weekly_challenge": "star", "daily_login": "sun"}
        async for r in recent:
            reason = r.get("reason", "")
            icon = "zap"
            for key, val in icons.items():
                if key in reason: icon = val; break
            rewards.append({
                "id": str(r["_id"]), "xp": r.get("xp", 0),
                "reason": reason, "icon": icon,
                "created_at": r.get("created_at", datetime.utcnow()).isoformat(),
            })

        return {
            "total_xp": total_xp,
            "level": level_info["level"],
            "rank": level_info["rank"],
            "recent_rewards": rewards,
        }

    async def award_daily_login_xp(self, user_id: str) -> dict:
        db = get_db()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        existing = await db.tech_logo_match_xp.find_one({"user_id": user_id, "reason": "daily_login", "created_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}})
        if existing:
            return {"awarded": False, "message": "Daily login XP already claimed today"}
        await db.tech_logo_match_xp.insert_one({
            "user_id": user_id, "xp": 10, "reason": "daily_login", "created_at": datetime.utcnow(),
        })
        await self._create_notification(user_id, "xp", "+10 Daily Login XP", "Thanks for logging in!", datetime.utcnow())
        return {"awarded": True, "xp": 10, "message": "Daily login XP awarded"}

    # ── Notifications ──
    async def _create_notification(self, user_id: str, ntype: str, title: str, message: str, now: datetime):
        db = get_db()
        await db.tech_logo_match_notifications.insert_one({
            "user_id": user_id, "type": ntype, "title": title, "message": message,
            "read": False, "created_at": now,
        })

    async def get_notifications(self, user_id: str) -> dict:
        db = get_db()
        items = await db.tech_logo_match_notifications.find({"user_id": user_id}).sort("created_at", -1).limit(50).to_list(None)
        unread = await db.tech_logo_match_notifications.count_documents({"user_id": user_id, "read": False})
        return {
            "notifications": [{
                "id": str(n["_id"]), "type": n.get("type", ""),
                "title": n.get("title", ""), "message": n.get("message", ""),
                "read": n.get("read", False),
                "created_at": n.get("created_at", datetime.utcnow()).isoformat(),
            } for n in items],
            "unread_count": unread,
        }

    async def mark_notification_read(self, notification_id: str) -> bool:
        from bson import ObjectId
        db = get_db()
        result = await db.tech_logo_match_notifications.update_one(
            {"_id": ObjectId(notification_id)}, {"$set": {"read": True}}
        )
        return result.modified_count > 0

    async def mark_all_notifications_read(self, user_id: str) -> bool:
        db = get_db()
        result = await db.tech_logo_match_notifications.update_many(
            {"user_id": user_id, "read": False}, {"$set": {"read": True}}
        )
        return result.modified_count > 0

    # ── Player Profile (Expanded) ──
    async def get_player_profile(self, user_id: str, user: dict) -> dict:
        db = get_db()
        stats = await db.tech_logo_match_statistics.find_one({"user_id": user_id}) or {}
        total_xp_result = await db.tech_logo_match_xp.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$xp"}}},
        ]).to_list(None)
        total_xp = total_xp_result[0]["total"] if total_xp_result else 0
        level_info = self._calculate_level(total_xp)

        achievements = await db.tech_logo_match_achievements.count_documents({"user_id": user_id})
        badges = await db.tech_logo_match_badges.count_documents({"user_id": user_id})

        return {
            "username": user.get("full_name", ""),
            "full_name": user.get("full_name", ""),
            "level": level_info["level"],
            "current_xp": level_info["current_xp"],
            "xp_for_next": level_info["xp_for_next"],
            "progress": level_info["progress"],
            "rank": level_info["rank"],
            "rank_icon": level_info["rank_icon"],
            "games_played": stats.get("total_games", 0),
            "average_accuracy": stats.get("average_accuracy", 0),
            "current_streak": stats.get("current_streak", 0),
            "longest_streak": stats.get("longest_streak", 0),
            "achievements_unlocked": achievements,
            "total_achievements": len(self.ACHIEVEMENTS),
            "badges_unlocked": badges,
            "total_badges": len(self.BADGES),
            "favorite_category": stats.get("favorite_category"),
            "favorite_difficulty": stats.get("favorite_difficulty"),
            "favorite_mode": stats.get("favorite_mode"),
        }


tech_logo_match_service = TechLogoMatchService()
