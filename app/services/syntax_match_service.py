from datetime import datetime, timedelta
from typing import Optional
from app.database import get_db


class SyntaxMatchService:

    # ── Save completed game ──
    async def save_game(self, user_id: str, data: dict) -> dict:
        db = get_db()
        now = datetime.utcnow()

        game = {
            "user_id": user_id,
            "language": data["language"],
            "difficulty": data["difficulty"],
            "completion_time_seconds": data["completion_time_seconds"],
            "moves": data["moves"],
            "correct_matches": data["correct_matches"],
            "wrong_matches": data["wrong_matches"],
            "accuracy": data["accuracy"],
            "stars": data["stars"],
            "total_pairs": data["total_pairs"],
            "created_at": now,
        }

        result = await db.syntax_match_games.insert_one(game)
        game_id = str(result.inserted_id)

        await self._update_statistics(user_id)
        streak = await self._update_streak(user_id, now)

        total = await db.syntax_match_games.count_documents({"user_id": user_id})

        # ── Gamification: award XP & check achievements ──
        xp_result = await self._award_game_xp(
            user_id, data, game_id, streak, now
        )
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
                    "total_matches": {"$sum": "$correct_matches"},
                    "total_moves": {"$sum": "$moves"},
                    "total_correct": {"$sum": "$correct_matches"},
                    "total_wrong": {"$sum": "$wrong_matches"},
                    "total_stars": {"$sum": "$stars"},
                    "sum_accuracy": {"$sum": "$accuracy"},
                    "sum_time": {"$sum": "$completion_time_seconds"},
                    "best_accuracy": {"$max": "$accuracy"},
                    "fastest_time": {"$min": "$completion_time_seconds"},
                    "best_moves": {"$min": "$moves"},
                    "three_star_count": {
                        "$sum": {"$cond": [{"$eq": ["$stars", 3]}, 1, 0]}
                    },
                }
            },
        ]
        results = await db.syntax_match_games.aggregate(pipeline).to_list(None)
        if not results:
            return

        r = results[0]
        total = r["total_games"]

        fav_lang = await self._favorite(db, user_id, "language")
        fav_diff = await self._favorite(db, user_id, "difficulty")

        await db.syntax_match_statistics.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "total_games": total,
                    "total_matches": r["total_matches"],
                    "total_moves": r["total_moves"],
                    "total_correct": r["total_correct"],
                    "total_wrong": r["total_wrong"],
                    "total_stars": r["total_stars"],
                    "average_accuracy": round(r["sum_accuracy"] / total, 1) if total else 0,
                    "average_moves": round(r["total_moves"] / total, 1) if total else 0,
                    "average_completion_time": round(r["sum_time"] / total, 1) if total else 0,
                    "best_accuracy": r["best_accuracy"],
                    "fastest_completion": r["fastest_time"],
                    "best_moves": r["best_moves"],
                    "favorite_language": fav_lang,
                    "favorite_difficulty": fav_diff,
                    "three_star_games": r["three_star_count"],
                    "updated_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )

    async def _favorite(self, db, user_id: str, field: str) -> Optional[str]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1},
        ]
        results = await db.syntax_match_games.aggregate(pipeline).to_list(None)
        return results[0]["_id"] if results else None

    # ── Streak tracking ──
    async def _update_streak(self, user_id: str, now: datetime) -> int:
        db = get_db()
        yesterday = now - timedelta(days=1)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        last = await db.syntax_match_games.find_one(
            {"user_id": user_id},
            sort=[("created_at", -1)],
        )

        if not last or last["created_at"].date() == now.date():
            streak = 1
        elif last["created_at"].date() == yesterday.date():
            existing = await db.syntax_match_statistics.find_one({"user_id": user_id})
            streak = (existing.get("current_streak", 0) or 0) + 1 if existing else 1
        else:
            streak = 1

        longest = streak
        existing_stats = await db.syntax_match_statistics.find_one({"user_id": user_id})
        if existing_stats:
            longest = max(streak, existing_stats.get("longest_streak", 0) or 0)

        if existing_stats:
            await db.syntax_match_statistics.update_one(
                {"user_id": user_id},
                {"$set": {"current_streak": streak, "longest_streak": longest}},
            )
        return streak

    # ── Get statistics ──
    async def get_statistics(self, user_id: str) -> dict:
        db = get_db()
        stats = await db.syntax_match_statistics.find_one({"user_id": user_id})
        if not stats:
            return {
                "total_games": 0,
                "total_matches": 0,
                "total_moves": 0,
                "total_correct": 0,
                "total_wrong": 0,
                "average_accuracy": 0,
                "average_moves": 0,
                "average_completion_time": 0,
                "best_accuracy": 0,
                "fastest_completion": None,
                "best_moves": None,
                "favorite_language": None,
                "favorite_difficulty": None,
                "current_streak": 0,
                "longest_streak": 0,
                "three_star_games": 0,
            }
        return {
            "total_games": stats.get("total_games", 0),
            "total_matches": stats.get("total_matches", 0),
            "total_moves": stats.get("total_moves", 0),
            "total_correct": stats.get("total_correct", 0),
            "total_wrong": stats.get("total_wrong", 0),
            "average_accuracy": stats.get("average_accuracy", 0),
            "average_moves": stats.get("average_moves", 0),
            "average_completion_time": stats.get("average_completion_time", 0),
            "best_accuracy": stats.get("best_accuracy", 0),
            "fastest_completion": stats.get("fastest_completion"),
            "best_moves": stats.get("best_moves"),
            "favorite_language": stats.get("favorite_language"),
            "favorite_difficulty": stats.get("favorite_difficulty"),
            "current_streak": stats.get("current_streak", 0),
            "longest_streak": stats.get("longest_streak", 0),
            "three_star_games": stats.get("three_star_games", 0),
        }

    # ── Get game history ──
    async def get_history(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        language: Optional[str] = None,
        difficulty: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> dict:
        db = get_db()
        query = {"user_id": user_id}
        if language:
            query["language"] = language
        if difficulty:
            query["difficulty"] = difficulty

        sort_dir = -1 if sort_order == "desc" else 1
        skip = (page - 1) * limit

        total = await db.syntax_match_games.count_documents(query)
        cursor = (
            db.syntax_match_games.find(query)
            .sort(sort_by, sort_dir)
            .skip(skip)
            .limit(limit)
        )
        games = await cursor.to_list(None)

        return {
            "games": [
                {
                    "id": str(g["_id"]),
                    "language": g["language"],
                    "difficulty": g["difficulty"],
                    "completion_time_seconds": g["completion_time_seconds"],
                    "moves": g["moves"],
                    "correct_matches": g["correct_matches"],
                    "wrong_matches": g["wrong_matches"],
                    "accuracy": g["accuracy"],
                    "stars": g["stars"],
                    "total_pairs": g["total_pairs"],
                    "created_at": g["created_at"].isoformat(),
                }
                for g in games
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "has_more": skip + limit < total,
        }

    # ── Get dashboard ──
    async def get_dashboard(self, user_id: str) -> dict:
        db = get_db()
        stats = await self.get_statistics(user_id)

        recent = (
            await db.syntax_match_games.find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(5)
            .to_list(None)
        )

        return {
            **stats,
            "total_stars": stats.get("total_games", 0) * 3,
            "recent_games": [
                {
                    "id": str(g["_id"]),
                    "language": g["language"],
                    "difficulty": g["difficulty"],
                    "completion_time_seconds": g["completion_time_seconds"],
                    "moves": g["moves"],
                    "accuracy": g["accuracy"],
                    "stars": g["stars"],
                    "created_at": g["created_at"].isoformat(),
                }
                for g in recent
            ],
            "weekly_activity": [],
            "monthly_activity": [],
        }

    # ── Get player profile ──
    async def get_profile(self, user_id: str, user: dict) -> dict:
        db = get_db()
        stats = await db.syntax_match_statistics.find_one({"user_id": user_id})
        total = await db.syntax_match_games.count_documents({"user_id": user_id})
        total_stars_result = await db.syntax_match_games.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$stars"}}},
        ]).to_list(None)
        total_stars = total_stars_result[0]["total"] if total_stars_result else 0

        return {
            "full_name": user.get("full_name", "Player"),
            "email": user.get("email", ""),
            "total_games": total,
            "total_stars": total_stars,
            "average_accuracy": stats.get("average_accuracy", 0) if stats else 0,
            "current_streak": stats.get("current_streak", 0) if stats else 0,
            "best_accuracy": stats.get("best_accuracy", 0) if stats else 0,
            "best_time": stats.get("fastest_completion") if stats else None,
            "best_moves": stats.get("best_moves") if stats else None,
            "favorite_language": stats.get("favorite_language") if stats else None,
            "favorite_difficulty": stats.get("favorite_difficulty") if stats else None,
        }

    # ── Settings ──
    async def get_settings(self, user_id: str) -> dict:
        db = get_db()
        settings = await db.syntax_match_settings.find_one({"user_id": user_id})
        if not settings:
            return {
                "card_flip_speed": "normal",
                "animation_speed": "normal",
                "sound_enabled": True,
                "music_enabled": False,
                "preview_duration": None,
                "reduced_motion": False,
                "last_language": None,
                "last_difficulty": None,
            }
        return {
            "card_flip_speed": settings.get("card_flip_speed", "normal"),
            "animation_speed": settings.get("animation_speed", "normal"),
            "sound_enabled": settings.get("sound_enabled", True),
            "music_enabled": settings.get("music_enabled", False),
            "preview_duration": settings.get("preview_duration"),
            "reduced_motion": settings.get("reduced_motion", False),
            "last_language": settings.get("last_language"),
            "last_difficulty": settings.get("last_difficulty"),
        }

    async def save_settings(self, user_id: str, data: dict) -> dict:
        db = get_db()
        update = {k: v for k, v in data.items() if v is not None}
        if update:
            await db.syntax_match_settings.update_one(
                {"user_id": user_id},
                {"$set": {**update, "updated_at": datetime.utcnow()}},
                upsert=True,
            )
        return await self.get_settings(user_id)

    # ══════════════════════════════════════════════
    # Phase 21: Analytics
    # ══════════════════════════════════════════════

    async def get_analytics(self, user_id: str) -> dict:
        db = get_db()
        stats = await self.get_statistics(user_id)
        languages = await self._get_language_performance(db, user_id)
        difficulties = await self._get_difficulty_performance(db, user_id)
        heatmap = await self._get_heatmap(db, user_id)
        insights = await self._get_insights(db, user_id, stats, languages, difficulties)
        daily = await self._get_activity(db, user_id, "day")
        weekly = await self._get_activity(db, user_id, "week")
        monthly = await self._get_activity(db, user_id, "month")
        yearly = await self._get_activity(db, user_id, "year")
        personal_bests = self._get_personal_bests(stats)
        achievement = self._get_achievement_progress(stats)

        total_matches = stats.get("total_matches", 0)
        total_wrong = stats.get("total_wrong", 0)
        overall_accuracy = round(
            (total_matches / (total_matches + total_wrong)) * 100, 1
        ) if (total_matches + total_wrong) > 0 else 0

        return {
            "total_games": stats.get("total_games", 0),
            "games_completed": stats.get("total_games", 0),
            "total_matches": total_matches,
            "total_wrong_matches": total_wrong,
            "overall_accuracy": overall_accuracy,
            "average_accuracy": stats.get("average_accuracy", 0),
            "fastest_game": stats.get("fastest_completion"),
            "average_completion_time": stats.get("average_completion_time", 0),
            "average_moves": stats.get("average_moves", 0),
            "best_star_rating": 3 if stats.get("three_star_games", 0) > 0 else 0,
            "current_streak": stats.get("current_streak", 0),
            "longest_streak": stats.get("longest_streak", 0),
            "favorite_language": stats.get("favorite_language"),
            "favorite_difficulty": stats.get("favorite_difficulty"),
            "languages": languages,
            "difficulties": difficulties,
            "heatmap": heatmap,
            "insights": insights,
            "daily_activity": daily,
            "weekly_activity": weekly,
            "monthly_activity": monthly,
            "yearly_activity": yearly,
            "personal_bests": personal_bests,
            "achievement_progress": achievement,
        }

    async def _get_language_performance(self, db, user_id: str) -> list:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": "$language",
                    "games_played": {"$sum": 1},
                    "average_accuracy": {"$avg": "$accuracy"},
                    "average_time": {"$avg": "$completion_time_seconds"},
                    "best_time": {"$min": "$completion_time_seconds"},
                    "best_moves": {"$min": "$moves"},
                    "total_stars": {"$sum": "$stars"},
                    "completed_count": {
                        "$sum": {"$cond": [{"$gte": ["$stars", 1]}, 1, 0]}
                    },
                }
            },
            {"$sort": {"games_played": -1}},
        ]
        results = await db.syntax_match_games.aggregate(pipeline).to_list(None)
        out = []
        for r in results:
            lang = r["_id"]
            total = r["games_played"]
            completed = r.get("completed_count", total)
            # favorite difficulty per language
            diff_pipe = [
                {"$match": {"user_id": user_id, "language": lang}},
                {"$group": {"_id": "$difficulty", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 1},
            ]
            diff_res = await db.syntax_match_games.aggregate(diff_pipe).to_list(None)
            fav_diff = diff_res[0]["_id"] if diff_res else None
            out.append({
                "language": lang,
                "games_played": total,
                "average_accuracy": round(r.get("average_accuracy", 0), 1),
                "average_time": round(r.get("average_time", 0), 1),
                "best_time": r.get("best_time"),
                "best_moves": r.get("best_moves"),
                "completion_rate": round((completed / total) * 100, 1),
                "total_stars": r.get("total_stars", 0),
                "favorite_difficulty": fav_diff,
            })
        return out

    async def _get_difficulty_performance(self, db, user_id: str) -> list:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": "$difficulty",
                    "games_played": {"$sum": 1},
                    "average_accuracy": {"$avg": "$accuracy"},
                    "average_time": {"$avg": "$completion_time_seconds"},
                    "average_moves": {"$avg": "$moves"},
                    "stars_3_count": {
                        "$sum": {"$cond": [{"$eq": ["$stars", 3]}, 1, 0]}
                    },
                    "stars_2_count": {
                        "$sum": {"$cond": [{"$eq": ["$stars", 2]}, 1, 0]}
                    },
                    "stars_1_count": {
                        "$sum": {"$cond": [{"$eq": ["$stars", 1]}, 1, 0]}
                    },
                }
            },
            {"$sort": {"games_played": -1}},
        ]
        results = await db.syntax_match_games.aggregate(pipeline).to_list(None)
        out = []
        for r in results:
            total = r["games_played"]
            succeeded = r.get("stars_3_count", 0) + r.get("stars_2_count", 0)
            success_rate = round((succeeded / total) * 100, 1) if total else 0
            out.append({
                "difficulty": r["_id"],
                "games_played": total,
                "average_accuracy": round(r.get("average_accuracy", 0), 1),
                "average_time": round(r.get("average_time", 0), 1),
                "success_rate": success_rate,
                "average_moves": round(r.get("average_moves", 0), 1),
            })
        return out

    async def _get_heatmap(self, db, user_id: str) -> list:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        results = await db.syntax_match_games.aggregate(pipeline).to_list(None)
        return [{"date": r["_id"], "count": r["count"]} for r in results]

    async def _get_activity(self, db, user_id: str, group_by: str) -> list:
        fmt = {"day": "%Y-%m-%d", "week": "%Y-W%V", "month": "%Y-%m", "year": "%Y"}
        format_str = fmt.get(group_by, "%Y-%m-%d")
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": format_str, "date": "$created_at"}
                    },
                    "games": {"$sum": 1},
                    "accuracy": {"$avg": "$accuracy"},
                    "completion_time": {"$avg": "$completion_time_seconds"},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        results = await db.syntax_match_games.aggregate(pipeline).to_list(None)
        return [
            {
                "date": r["_id"],
                "games": r["games"],
                "accuracy": round(r.get("accuracy", 0), 1),
                "completion_time": round(r.get("completion_time", 0), 1),
            }
            for r in results
        ]

    def _get_personal_bests(self, stats: dict) -> list:
        bests = []
        if stats.get("best_accuracy"):
            bests.append({
                "label": "Highest Accuracy",
                "value": f"{stats['best_accuracy']}%",
                "icon": "target",
            })
        if stats.get("fastest_completion"):
            sec = stats["fastest_completion"]
            m, s = divmod(sec, 60)
            bests.append({
                "label": "Fastest Completion",
                "value": f"{m}:{s:02d}",
                "icon": "clock",
            })
        if stats.get("best_moves"):
            bests.append({
                "label": "Lowest Moves",
                "value": str(stats["best_moves"]),
                "icon": "trending-up",
            })
        if stats.get("favorite_language"):
            bests.append({
                "label": "Most Played Language",
                "value": stats["favorite_language"].title(),
                "icon": "code",
            })
        if stats.get("current_streak", 0) > 0:
            bests.append({
                "label": "Current Streak",
                "value": f"{stats['current_streak']} days",
                "icon": "flame",
            })
        if stats.get("longest_streak", 0) > 0:
            bests.append({
                "label": "Longest Streak",
                "value": f"{stats['longest_streak']} days",
                "icon": "award",
            })
        return bests

    def _get_achievement_progress(self, stats: dict) -> list:
        total = stats.get("total_games", 0)
        three_star = stats.get("three_star_games", 0)
        avg_acc = stats.get("average_accuracy", 0)
        return [
            {
                "label": "Games Played",
                "current": float(total),
                "target": 100.0,
                "percent": min(round((total / 100) * 100, 1), 100),
            },
            {
                "label": "Accuracy Goal",
                "current": avg_acc,
                "target": 100.0,
                "percent": min(avg_acc, 100),
            },
            {
                "label": "Completion Goal",
                "current": float(three_star),
                "target": 50.0,
                "percent": min(round((three_star / 50) * 100, 1), 100),
            },
            {
                "label": "Winning Streak",
                "current": float(stats.get("current_streak", 0)),
                "target": 30.0,
                "percent": min(round((stats.get("current_streak", 0) / 30) * 100, 1), 100),
            },
            {
                "label": "Stars Collected",
                "current": float(stats.get("total_games", 0) * 3),
                "target": 300.0,
                "percent": min(round(((stats.get("total_games", 0) * 3) / 300) * 100, 1), 100),
            },
        ]

    async def _get_insights(self, db, user_id: str, stats: dict, languages: list, difficulties: list) -> list:
        insights = []
        total = stats.get("total_games", 0)
        if total == 0:
            insights.append({
                "type": "info",
                "message": "Play your first Syntax Match game to receive personalized insights.",
                "direction": "neutral",
            })
            return insights

        # Language insights
        if languages:
            best_lang = languages[0]
            if best_lang["games_played"] >= 2:
                insights.append({
                    "type": "strength",
                    "message": f"{best_lang['language']} is your strongest language with {best_lang['average_accuracy']}% accuracy.",
                    "direction": "up",
                })
            if len(languages) >= 2:
                worst_lang = languages[-1]
                if worst_lang["average_accuracy"] < 70 and worst_lang["games_played"] >= 2:
                    insights.append({
                        "type": "improvement",
                        "message": f"{worst_lang['language']} could use more practice ({worst_lang['average_accuracy']}% accuracy).",
                        "direction": "down",
                    })

        # Difficulty insights
        for d in difficulties:
            if d["games_played"] >= 3:
                if d["difficulty"] == "hard" and d["success_rate"] > 60:
                    insights.append({
                        "type": "achievement",
                        "message": f"Hard difficulty mastery! {d['success_rate']}% success rate across {d['games_played']} games.",
                        "direction": "up",
                    })
                elif d["difficulty"] == "easy" and d["average_accuracy"] > 90:
                    insights.append({
                        "type": "milestone",
                        "message": f"Easy difficulty mastered at {d['average_accuracy']}% — try Medium or Hard!",
                        "direction": "up",
                    })

        # Streak insight
        if stats.get("current_streak", 0) >= 3:
            insights.append({
                "type": "streak",
                "message": f"You're on a {stats['current_streak']}-day streak! Keep it going.",
                "direction": "up",
            })

        # Improvement insights
        if stats.get("average_moves", 0) > 0 and stats.get("total_games", 0) >= 3:
            insights.append({
                "type": "performance",
                "message": f"Average {stats['average_moves']} moves per game. Try to reduce moves for higher stars.",
                "direction": "neutral" if stats.get("average_moves", 0) > 15 else "up",
            })

        if stats.get("average_completion_time", 0) > 0:
            ct = stats["average_completion_time"]
            if ct < 60:
                insights.append({
                    "type": "speed",
                    "message": f"Lightning fast! Average completion time under a minute.",
                    "direction": "up",
                })

        if not insights:
            insights.append({
                "type": "info",
                "message": "Keep playing to unlock more detailed performance insights.",
                "direction": "neutral",
            })

        return insights

    async def export_analytics(self, user_id: str, format_type: str) -> str:
        import csv, io, json
        db = get_db()
        games = await db.syntax_match_games.find(
            {"user_id": user_id}
        ).sort("created_at", -1).to_list(None)

        if format_type == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Date", "Language", "Difficulty", "Time", "Moves", "Accuracy", "Stars", "Pairs"])
            for g in games:
                writer.writerow([
                    g["created_at"].isoformat(),
                    g["language"], g["difficulty"],
                    g["completion_time_seconds"], g["moves"],
                    g["accuracy"], g["stars"], g["total_pairs"],
                ])
            return output.getvalue()

        elif format_type == "json":
            data = []
            for g in games:
                data.append({
                    "date": g["created_at"].isoformat(),
                    "language": g["language"],
                    "difficulty": g["difficulty"],
                    "time_seconds": g["completion_time_seconds"],
                    "moves": g["moves"],
                    "accuracy": g["accuracy"],
                    "stars": g["stars"],
                    "total_pairs": g["total_pairs"],
                })
            return json.dumps(data, indent=2)

        return "Unsupported format"

    # ══════════════════════════════════════════════
    # Phase 22: Gamification
    # ══════════════════════════════════════════════

    # ── XP Calculation ──
    async def _award_game_xp(self, user_id: str, data: dict, game_id: str, streak: int, now: datetime) -> dict:
        db = get_db()
        xp = 0
        reasons = []

        # Base XP
        base = 100
        xp += base
        reasons.append(f"Game completed (+{base} XP)")

        # Accuracy bonus
        if data["accuracy"] >= 100:
            xp += 50
            reasons.append("Perfect accuracy (+50 XP)")
        elif data["accuracy"] >= 90:
            xp += 25
            reasons.append("High accuracy (+25 XP)")

        # Speed bonus
        time_limit = {"easy": 60, "medium": 90, "hard": 120}
        limit = time_limit.get(data["difficulty"], 90)
        if data["completion_time_seconds"] <= limit * 0.5:
            xp += 50
            reasons.append("Lightning fast (+50 XP)")
        elif data["completion_time_seconds"] <= limit * 0.75:
            xp += 25
            reasons.append("Fast completion (+25 XP)")

        # Low moves bonus
        optimal = data["total_pairs"] * 2
        if data["moves"] <= optimal:
            xp += 50
            reasons.append("Minimum moves (+50 XP)")
        elif data["moves"] <= optimal + 2:
            xp += 25
            reasons.append("Low moves (+25 XP)")

        # Stars bonus
        if data["stars"] == 3:
            xp += 50
            reasons.append("3-star game (+50 XP)")

        # Perfect game bonus
        if data["accuracy"] >= 100 and data["stars"] == 3:
            xp += 100
            reasons.append("Perfect game (+100 XP)")

        # First game of the day
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_games = await db.syntax_match_games.count_documents({
            "user_id": user_id, "created_at": {"$gte": today_start},
        })
        if today_games <= 1:
            xp += 25
            reasons.append("First game today (+25 XP)")

        # Streak bonus
        if streak >= 7:
            xp += 50
            reasons.append(f"{streak}-day streak bonus (+50 XP)")
        elif streak >= 3:
            xp += 20
            reasons.append(f"{streak}-day streak bonus (+20 XP)")

        # Check daily challenge completion for bonus
        daily = await self._check_daily_challenge_completion(user_id, data)
        if daily:
            xp += 100
            reasons.append("Daily challenge completed (+100 XP)")

        # Award XP
        await db.syntax_match_xp.insert_one({
            "user_id": user_id, "amount": xp, "reason": "; ".join(reasons),
            "source": "game", "game_id": game_id, "created_at": now,
        })

        # Update cumulative XP
        total_xp_result = await db.syntax_match_xp.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]).to_list(None)
        total_xp = total_xp_result[0]["total"] if total_xp_result else xp

        old_level = await self._calculate_level(total_xp - xp)
        new_level = await self._calculate_level(total_xp)
        level_up = new_level["level"] > old_level["level"]

        # Save level info
        level_info = await self._calculate_level(total_xp)
        await db.syntax_match_levels.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id, "level": level_info["level"],
                "current_xp": total_xp, "xp_for_next": level_info["xp_for_next"],
                "rank": level_info["rank"], "updated_at": now,
            }},
            upsert=True,
        )

        # Create notification for level up
        if level_up:
            await self._create_notification(
                user_id, "level_up", "Level Up!",
                f"You reached level {new_level['level']} ({new_level['rank']})!",
                "trending-up", now,
            )

        return {
            "xp_awarded": xp, "total_xp": total_xp,
            "level": new_level["level"], "level_up": level_up,
        }

    async def _calculate_level(self, total_xp: int) -> dict:
        level = 1
        xp_for_current = 0
        while True:
            xp_needed = int(250 * (level ** 1.5))
            if total_xp < xp_for_current + xp_needed:
                break
            xp_for_current += xp_needed
            level += 1
        xp_for_next = int(250 * (level ** 1.5))
        progress = ((total_xp - xp_for_current) / xp_for_next) * 100 if xp_for_next else 100
        return {
            "level": level,
            "current_xp": total_xp,
            "xp_for_next": xp_for_next,
            "xp_in_level": total_xp - xp_for_current,
            "progress_percent": round(progress, 1),
            "rank": self._get_rank_name(level),
        }

    def _get_rank_name(self, level: int) -> str:
        if level <= 3: return "Beginner"
        if level <= 6: return "Explorer"
        if level <= 10: return "Coder"
        if level <= 15: return "Developer"
        if level <= 20: return "Engineer"
        if level <= 25: return "Senior Engineer"
        if level <= 30: return "Architect"
        if level <= 35: return "Master"
        return "Legend"

    # ── Achievement Engine ──

    ACHIEVEMENT_DEFINITIONS = [
        {"id": "first_match", "title": "First Match", "description": "Complete your first match", "icon": "target", "xp_reward": 50, "category": "milestone", "requirement_type": "total_games", "requirement_value": 1},
        {"id": "first_win", "title": "First Win", "description": "Win your first game with 3 stars", "icon": "trophy", "xp_reward": 100, "category": "milestone", "requirement_type": "three_star_games", "requirement_value": 1},
        {"id": "ten_games", "title": "Dedicated Learner", "description": "Complete 10 games", "icon": "book", "xp_reward": 150, "category": "milestone", "requirement_type": "total_games", "requirement_value": 10},
        {"id": "fifty_games", "title": "Committed", "description": "Complete 50 games", "icon": "award", "xp_reward": 300, "category": "milestone", "requirement_type": "total_games", "requirement_value": 50},
        {"id": "hundred_games", "title": "Dedication Master", "description": "Complete 100 games", "icon": "star", "xp_reward": 500, "category": "milestone", "requirement_type": "total_games", "requirement_value": 100},
        {"id": "perfect_accuracy", "title": "Perfect Accuracy", "description": "Get 100% accuracy in a game", "icon": "target", "xp_reward": 200, "category": "skill", "requirement_type": "best_accuracy", "requirement_value": 100},
        {"id": "html_master", "title": "HTML Master", "description": "Complete 5 HTML games", "icon": "code", "xp_reward": 200, "category": "language", "requirement_type": "html_games", "requirement_value": 5},
        {"id": "css_master", "title": "CSS Master", "description": "Complete 5 CSS games", "icon": "code", "xp_reward": 200, "category": "language", "requirement_type": "css_games", "requirement_value": 5},
        {"id": "js_master", "title": "JavaScript Master", "description": "Complete 10 JavaScript games", "icon": "code", "xp_reward": 300, "category": "language", "requirement_type": "javascript_games", "requirement_value": 10},
        {"id": "react_master", "title": "React Expert", "description": "Complete 10 React games", "icon": "code", "xp_reward": 300, "category": "language", "requirement_type": "react_games", "requirement_value": 10},
        {"id": "seven_day_streak", "title": "Week Warrior", "description": "Maintain a 7-day streak", "icon": "flame", "xp_reward": 250, "category": "streak", "requirement_type": "longest_streak", "requirement_value": 7},
        {"id": "thirty_day_streak", "title": "Unstoppable", "description": "Maintain a 30-day streak", "icon": "flame", "xp_reward": 1000, "category": "streak", "requirement_type": "longest_streak", "requirement_value": 30},
        {"id": "speed_master", "title": "Speed Master", "description": "Complete a game under 30 seconds", "icon": "zap", "xp_reward": 250, "category": "skill", "requirement_type": "fastest_completion", "requirement_value": 30},
        {"id": "move_master", "title": "Move Master", "description": "Complete a game with minimum moves", "icon": "trending-up", "xp_reward": 200, "category": "skill", "requirement_type": "best_moves", "requirement_value": 4},
        {"id": "easy_legend", "title": "Easy Legend", "description": "Complete 10 Easy games", "icon": "layers", "xp_reward": 200, "category": "difficulty", "requirement_type": "easy_games", "requirement_value": 10},
        {"id": "medium_hero", "title": "Medium Hero", "description": "Complete 10 Medium games", "icon": "layers", "xp_reward": 300, "category": "difficulty", "requirement_type": "medium_games", "requirement_value": 10},
        {"id": "hard_champion", "title": "Hard Champion", "description": "Complete 10 Hard games", "icon": "layers", "xp_reward": 500, "category": "difficulty", "requirement_type": "hard_games", "requirement_value": 10},
    ]

    async def _check_achievements(self, user_id: str) -> list:
        db = get_db()
        stats = await self.get_statistics(user_id)
        total = stats.get("total_games", 0)
        three_star = stats.get("three_star_games", 0)
        best_acc = stats.get("best_accuracy", 0)
        fastest = stats.get("fastest_completion") or 9999
        best_moves = stats.get("best_moves") or 9999
        longest_streak = stats.get("longest_streak", 0)

        # Per-language counts
        lang_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$language", "count": {"$sum": 1}}},
        ]
        lang_results = await db.syntax_match_games.aggregate(lang_pipeline).to_list(None)
        lang_counts = {r["_id"]: r["count"] for r in lang_results}

        # Per-difficulty counts
        diff_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$difficulty", "count": {"$sum": 1}}},
        ]
        diff_results = await db.syntax_match_games.aggregate(diff_pipeline).to_list(None)
        diff_counts = {r["_id"]: r["count"] for r in diff_results}

        new_unlocks = []
        for ach in self.ACHIEVEMENT_DEFINITIONS:
            existing = await db.syntax_match_achievements.find_one(
                {"user_id": user_id, "achievement_id": ach["id"]}
            )
            if existing:
                continue

            current = 0
            rt = ach["requirement_type"]
            if rt == "total_games":
                current = total
            elif rt == "three_star_games":
                current = three_star
            elif rt == "best_accuracy":
                current = best_acc
            elif rt == "fastest_completion":
                current = fastest if fastest else 9999
                if current <= ach["requirement_value"]:
                    current = ach["requirement_value"]  # trigger unlock
            elif rt == "best_moves":
                current = best_moves if best_moves else 9999
                if current <= ach["requirement_value"]:
                    current = ach["requirement_value"]
            elif rt == "longest_streak":
                current = longest_streak
            elif rt.endswith("_games"):
                lang_key = rt.replace("_games", "")
                current = lang_counts.get(lang_key, 0)
            elif rt.endswith("_games") and rt in ["easy_games", "medium_games", "hard_games"]:
                diff_key = rt.replace("_games", "")
                current = diff_counts.get(diff_key, 0)

            if current >= ach["requirement_value"]:
                now = datetime.utcnow()
                await db.syntax_match_achievements.insert_one({
                    "user_id": user_id,
                    "achievement_id": ach["id"],
                    "title": ach["title"],
                    "description": ach["description"],
                    "icon": ach["icon"],
                    "xp_reward": ach["xp_reward"],
                    "category": ach["category"],
                    "unlocked_at": now,
                })
                # Award XP for achievement
                await db.syntax_match_xp.insert_one({
                    "user_id": user_id, "amount": ach["xp_reward"],
                    "reason": f"Achievement unlocked: {ach['title']} (+{ach['xp_reward']} XP)",
                    "source": "achievement", "created_at": now,
                })
                await self._create_notification(
                    user_id, "achievement", f"Achievement: {ach['title']}",
                    f"You unlocked '{ach['title']}' — +{ach['xp_reward']} XP!",
                    ach["icon"], now,
                )
                new_unlocks.append({
                    "id": ach["id"], "title": ach["title"],
                    "description": ach["description"], "icon": ach["icon"],
                    "xp_reward": ach["xp_reward"], "newly_unlocked": True,
                })

        return new_unlocks

    # ── Badge Engine ──

    BADGE_DEFINITIONS = [
        {"id": "bronze_player", "name": "Bronze Player", "description": "Reach level 5", "icon": "award", "tier": "bronze", "category": "level", "requirement_level": 5},
        {"id": "silver_coder", "name": "Silver Coder", "description": "Reach level 10", "icon": "award", "tier": "silver", "category": "level", "requirement_level": 10},
        {"id": "gold_developer", "name": "Gold Developer", "description": "Reach level 15", "icon": "award", "tier": "gold", "category": "level", "requirement_level": 15},
        {"id": "diamond_architect", "name": "Diamond Architect", "description": "Reach level 25", "icon": "award", "tier": "diamond", "category": "level", "requirement_level": 25},
        {"id": "bronze_streak", "name": "Bronze Streak", "description": "Reach 7-day streak", "icon": "flame", "tier": "bronze", "category": "streak", "requirement_streak": 7},
        {"id": "silver_streak", "name": "Silver Streak", "description": "Reach 14-day streak", "icon": "flame", "tier": "silver", "category": "streak", "requirement_streak": 14},
        {"id": "gold_streak", "name": "Gold Streak", "description": "Reach 30-day streak", "icon": "flame", "tier": "gold", "category": "streak", "requirement_streak": 30},
        {"id": "bronze_games", "name": "Bronze Gamer", "description": "Complete 25 games", "icon": "star", "tier": "bronze", "category": "games", "requirement_games": 25},
        {"id": "silver_games", "name": "Silver Gamer", "description": "Complete 50 games", "icon": "star", "tier": "silver", "category": "games", "requirement_games": 50},
        {"id": "gold_games", "name": "Gold Gamer", "description": "Complete 100 games", "icon": "star", "tier": "gold", "category": "games", "requirement_games": 100},
    ]

    async def _check_badges(self, user_id: str) -> list:
        db = get_db()
        level_data = await db.syntax_match_levels.find_one({"user_id": user_id})
        current_level = level_data["level"] if level_data else 1
        stats = await self.get_statistics(user_id)
        longest_streak = stats.get("longest_streak", 0)
        total = stats.get("total_games", 0)

        new_unlocks = []
        for badge in self.BADGE_DEFINITIONS:
            existing = await db.syntax_match_badges.find_one(
                {"user_id": user_id, "badge_id": badge["id"]}
            )
            if existing:
                continue

            unlocked = False
            if "requirement_level" in badge and current_level >= badge["requirement_level"]:
                unlocked = True
            elif "requirement_streak" in badge and longest_streak >= badge["requirement_streak"]:
                unlocked = True
            elif "requirement_games" in badge and total >= badge["requirement_games"]:
                unlocked = True

            if unlocked:
                now = datetime.utcnow()
                await db.syntax_match_badges.insert_one({
                    "user_id": user_id, "badge_id": badge["id"],
                    "name": badge["name"], "description": badge["description"],
                    "icon": badge["icon"], "tier": badge["tier"],
                    "category": badge["category"], "unlocked_at": now,
                })
                xp = {"bronze": 100, "silver": 250, "gold": 500, "diamond": 1000}.get(badge["tier"], 100)
                await db.syntax_match_xp.insert_one({
                    "user_id": user_id, "amount": xp,
                    "reason": f"Badge unlocked: {badge['name']} ({badge['tier']})",
                    "source": "badge", "created_at": now,
                })
                await self._create_notification(
                    user_id, "badge", f"Badge: {badge['name']}",
                    f"You earned the {badge['tier']} badge '{badge['name']}'!",
                    badge["icon"], now,
                )
                new_unlocks.append({
                    "id": badge["id"], "name": badge["name"],
                    "description": badge["description"], "icon": badge["icon"],
                    "tier": badge["tier"], "newly_unlocked": True,
                })

        return new_unlocks

    # ── Daily Login XP ──
    async def award_daily_login_xp(self, user_id: str) -> dict:
        db = get_db()
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        already = await db.syntax_match_xp.find_one({
            "user_id": user_id, "source": "daily_login",
            "created_at": {"$gte": today_start},
        })
        if already:
            return {"awarded": False, "xp": 0, "message": "Already claimed today"}

        await db.syntax_match_xp.insert_one({
            "user_id": user_id, "amount": 10,
            "reason": "Daily login bonus (+10 XP)",
            "source": "daily_login", "created_at": now,
        })
        return {"awarded": True, "xp": 10, "message": "Daily login bonus claimed!"}

    # ── Player Profile (Expanded) ──
    async def get_player_profile(self, user_id: str, user: dict) -> dict:
        db = get_db()
        stats = await self.get_statistics(user_id)
        level_data = await db.syntax_match_levels.find_one({"user_id": user_id})
        total_ach = len(self.ACHIEVEMENT_DEFINITIONS)
        unlocked_ach = await db.syntax_match_achievements.count_documents({"user_id": user_id})
        total_badges = len(self.BADGE_DEFINITIONS)
        unlocked_badges_db = await db.syntax_match_badges.count_documents({"user_id": user_id})
        total_stars_result = await db.syntax_match_games.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$stars"}}},
        ]).to_list(None)
        total_stars = total_stars_result[0]["total"] if total_stars_result else 0

        level = level_data["level"] if level_data else 1
        current_xp = level_data["current_xp"] if level_data else 0
        xp_for_next = level_data["xp_for_next"] if level_data else 250
        rank_name = level_data["rank"] if level_data else self._get_rank_name(1)
        progress = await self._calculate_level(current_xp)

        return {
            "full_name": user.get("full_name", "Player"),
            "email": user.get("email", ""),
            "total_games": stats.get("total_games", 0),
            "total_stars": total_stars,
            "average_accuracy": stats.get("average_accuracy", 0),
            "current_streak": stats.get("current_streak", 0),
            "longest_streak": stats.get("longest_streak", 0),
            "best_accuracy": stats.get("best_accuracy", 0),
            "best_time": stats.get("fastest_completion"),
            "best_moves": stats.get("best_moves"),
            "favorite_language": stats.get("favorite_language"),
            "favorite_difficulty": stats.get("favorite_difficulty"),
            "level": level,
            "current_xp": current_xp,
            "xp_for_next": xp_for_next,
            "rank_name": rank_name,
            "rank_icon": "star",
            "total_achievements": total_ach,
            "unlocked_achievements": unlocked_ach,
            "total_badges": total_badges,
            "unlocked_badges": unlocked_badges_db,
            "xp_progress_percent": progress["progress_percent"],
        }

    # ── Achievements ──
    async def get_achievements(self, user_id: str) -> list:
        db = get_db()
        unlocked = await db.syntax_match_achievements.find(
            {"user_id": user_id}
        ).to_list(None)
        unlocked_map = {a["achievement_id"]: a for a in unlocked}
        stats = await self.get_statistics(user_id)
        total = stats.get("total_games", 0)
        three_star = stats.get("three_star_games", 0)
        best_acc = stats.get("best_accuracy", 0)
        fastest = stats.get("fastest_completion") or 9999
        best_moves = stats.get("best_moves") or 9999
        longest_streak = stats.get("longest_streak", 0)

        lang_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$language", "count": {"$sum": 1}}},
        ]
        lang_results = await db.syntax_match_games.aggregate(lang_pipeline).to_list(None)
        lang_counts = {r["_id"]: r["count"] for r in lang_results}
        diff_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$difficulty", "count": {"$sum": 1}}},
        ]
        diff_results = await db.syntax_match_games.aggregate(diff_pipeline).to_list(None)
        diff_counts = {r["_id"]: r["count"] for r in diff_results}

        result = []
        for ach in self.ACHIEVEMENT_DEFINITIONS:
            existing = unlocked_map.get(ach["id"])
            current = 0
            rt = ach["requirement_type"]
            if rt == "total_games": current = total
            elif rt == "three_star_games": current = three_star
            elif rt == "best_accuracy": current = best_acc
            elif rt == "fastest_completion": current = fastest if fastest < 9999 else 0
            elif rt == "best_moves": current = best_moves if best_moves < 9999 else 0
            elif rt == "longest_streak": current = longest_streak
            elif rt.endswith("_games"):
                lang_key = rt.replace("_games", "")
                current = lang_counts.get(lang_key, diff_counts.get(lang_key, 0))

            result.append({
                "achievement_id": ach["id"],
                "title": ach["title"],
                "description": ach["description"],
                "icon": ach["icon"],
                "xp_reward": ach["xp_reward"],
                "category": ach["category"],
                "current": float(current),
                "target": ach["requirement_value"],
                "progress_percent": min(round((current / ach["requirement_value"]) * 100, 1), 100),
                "unlocked": existing is not None,
                "unlocked_at": existing["unlocked_at"].isoformat() if existing else None,
            })

        return result

    # ── Badges ──
    async def get_badges(self, user_id: str) -> list:
        db = get_db()
        unlocked = await db.syntax_match_badges.find(
            {"user_id": user_id}
        ).to_list(None)
        unlocked_map = {b["badge_id"]: b for b in unlocked}

        result = []
        for badge in self.BADGE_DEFINITIONS:
            existing = unlocked_map.get(badge["id"])
            result.append({
                "id": badge["id"],
                "name": badge["name"],
                "description": badge["description"],
                "icon": badge["icon"],
                "tier": badge["tier"],
                "category": badge["category"],
                "unlocked": existing is not None,
                "unlocked_at": existing["unlocked_at"].isoformat() if existing else None,
            })
        return result

    # ── Leaderboards ──
    async def get_leaderboard(self, metric: str = "xp", scope: str = "overall",
                               page: int = 1, limit: int = 50) -> dict:
        db = get_db()
        skip = (page - 1) * limit

        pipeline = []
        if scope != "overall":
            from_field = "language"
            pipeline.append({"$match": {"language": scope}})

        if metric == "xp":
            pipeline.append({"$group": {
                "_id": "$user_id",
                "score": {"$sum": "$amount"},
                "games_played": {"$sum": 1},
                "accuracy": {"$avg": 0},
                "streak": {"$max": 0},
            }})
            pipeline.append({"$sort": {"score": -1}})
            source_collection = "syntax_match_xp"
        elif metric == "games":
            pipeline.append({"$group": {
                "_id": "$user_id",
                "score": {"$sum": 1},
                "games_played": {"$sum": 1},
                "accuracy": {"$avg": "$accuracy"},
                "streak": {"$max": 0},
            }})
            pipeline.append({"$sort": {"score": -1}})
            source_collection = "syntax_match_games"
        elif metric == "accuracy":
            pipeline.append({"$group": {
                "_id": "$user_id",
                "score": {"$avg": "$accuracy"},
                "games_played": {"$sum": 1},
                "accuracy": {"$avg": "$accuracy"},
                "streak": {"$max": 0},
            }})
            pipeline.append({"$match": {"games_played": {"$gte": 3}}})
            pipeline.append({"$sort": {"score": -1}})
            source_collection = "syntax_match_games"
        elif metric == "streak":
            pipeline.append({"$sort": {"longest_streak": -1}})
            pipeline.append({"$limit": 200})
            source_collection = "syntax_match_statistics"
            # Use statistics directly
            cursor = db.syntax_match_statistics.find(
                {}, {"user_id": 1, "longest_streak": 1, "total_games": 1, "average_accuracy": 1}
            ).sort("longest_streak", -1).skip(skip).limit(limit)
            entries_raw = await cursor.to_list(None)
            total = await db.syntax_match_statistics.count_documents({})
            # Enrich with level data
            entries = []
            for i, e in enumerate(entries_raw):
                level_data = await db.syntax_match_levels.find_one({"user_id": e["user_id"]})
                entries.append({
                    "rank": skip + i + 1,
                    "user_id": str(e["user_id"]),
                    "username": "Player",
                    "level": level_data["level"] if level_data else 1,
                    "rank_name": level_data["rank"] if level_data else "Beginner",
                    "score": float(e.get("longest_streak", 0)),
                    "games_played": e.get("total_games", 0),
                    "accuracy": round(e.get("average_accuracy", 0), 1),
                    "streak": int(e.get("longest_streak", 0)),
                })
            return {"entries": entries, "total": total, "page": page, "limit": limit,
                    "metric": metric, "scope": scope}

        # Generic pipeline for XP/Games/Accuracy from a collection
        if source_collection == "syntax_match_games":
            cursor = db.syntax_match_games.aggregate(pipeline).to_list(None)
        else:
            cursor = db.syntax_match_xp.aggregate(pipeline).to_list(None)

        # Actually compute manually
        if metric in ("xp",):
            entries_raw = await db.syntax_match_xp.aggregate([
                {"$group": {
                    "_id": "$user_id",
                    "score": {"$sum": "$amount"},
                }},
                {"$sort": {"score": -1}},
                {"$skip": skip},
                {"$limit": limit},
            ]).to_list(None)
            total = len(await db.syntax_match_xp.distinct("user_id"))
        elif metric in ("games",):
            match = {}
            if scope != "overall":
                match["language"] = scope
            entries_raw = await db.syntax_match_games.aggregate([
                {"$match": match},
                {"$group": {
                    "_id": "$user_id",
                    "score": {"$sum": 1},
                    "avg_accuracy": {"$avg": "$accuracy"},
                }},
                {"$sort": {"score": -1}},
                {"$skip": skip},
                {"$limit": limit},
            ]).to_list(None)
            total = len(await db.syntax_match_games.distinct("user_id", match))
        elif metric in ("accuracy",):
            match = {}
            if scope != "overall":
                match["language"] = scope
            entries_raw = await db.syntax_match_games.aggregate([
                {"$match": match},
                {"$group": {
                    "_id": "$user_id",
                    "score": {"$avg": "$accuracy"},
                    "games_count": {"$sum": 1},
                }},
                {"$match": {"games_count": {"$gte": 3}}},
                {"$sort": {"score": -1}},
                {"$skip": skip},
                {"$limit": limit},
            ]).to_list(None)
            total = len(await db.syntax_match_games.distinct("user_id", match))

        entries = []
        for i, e in enumerate(entries_raw):
            level_data = await db.syntax_match_levels.find_one({"user_id": e["_id"]})
            stats = await self.get_statistics(e["_id"])
            entries.append({
                "rank": skip + i + 1,
                "user_id": str(e["_id"]),
                "username": "Player",
                "level": level_data["level"] if level_data else 1,
                "rank_name": level_data["rank"] if level_data else "Beginner",
                "score": round(float(e.get("score", 0)), 1),
                "games_played": stats.get("total_games", 0),
                "accuracy": round(e.get("avg_accuracy", e.get("accuracy", stats.get("average_accuracy", 0))), 1),
                "streak": stats.get("longest_streak", 0),
            })

        return {"entries": entries, "total": total, "page": page, "limit": limit,
                "metric": metric, "scope": scope}

    async def get_player_rank(self, user_id: str) -> dict:
        db = get_db()
        level_data = await db.syntax_match_levels.find_one({"user_id": user_id})
        total_xp = level_data["current_xp"] if level_data else 0

        # Count players with more XP
        higher = await db.syntax_match_levels.count_documents(
            {"current_xp": {"$gt": total_xp}}
        )
        total_players = await db.syntax_match_levels.count_documents({})
        rank = higher + 1 if total_players > 0 else 1

        return {"rank": rank, "total_players": max(total_players, 1), "score": total_xp}

    # ── Daily Challenges ──
    async def _get_today_key(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%d")

    async def _get_week_key(self) -> str:
        now = datetime.utcnow()
        iso = now.isocalendar()
        return f"{now.year}-W{iso[1]:02d}"

    DAILY_CHALLENGE_TYPES = [
        {"id": "html_only", "title": "HTML Day", "description": "Complete a game using HTML only", "req_type": "language", "req_value": "html", "xp": 100},
        {"id": "css_only", "title": "CSS Day", "description": "Complete a game using CSS only", "req_type": "language", "req_value": "css", "xp": 100},
        {"id": "js_only", "title": "JavaScript Day", "description": "Complete a game using JavaScript only", "req_type": "language", "req_value": "javascript", "xp": 100},
        {"id": "react_only", "title": "React Day", "description": "Complete a game using React only", "req_type": "language", "req_value": "react", "xp": 100},
        {"id": "hard_mode", "title": "Hard Mode", "description": "Complete a game on Hard difficulty", "req_type": "difficulty", "req_value": "hard", "xp": 100},
        {"id": "medium_challenge", "title": "Medium Challenge", "description": "Complete a game on Medium difficulty", "req_type": "difficulty", "req_value": "medium", "xp": 75},
        {"id": "perfect_accuracy_day", "title": "Perfect Accuracy", "description": "Get 100% accuracy on any game", "req_type": "accuracy", "req_value": "100", "xp": 150},
        {"id": "speed_run", "title": "Speed Run", "description": "Finish a game under 90 seconds", "req_type": "time", "req_value": "90", "xp": 100},
        {"id": "low_moves", "title": "Efficient", "description": "Finish a game with under 15 moves", "req_type": "moves", "req_value": "15", "xp": 100},
        {"id": "three_star_day", "title": "Star Collector", "description": "Get 3 stars on any game", "req_type": "stars", "req_value": "3", "xp": 75},
        {"id": "nextjs_day", "title": "Next.js Day", "description": "Complete a game using Next.js", "req_type": "language", "req_value": "next.js", "xp": 150},
        {"id": "typescript_day", "title": "TypeScript Day", "description": "Complete a game using TypeScript", "req_type": "language", "req_value": "typescript", "xp": 150},
    ]

    WEEKLY_CHALLENGE_TYPES = [
        {"id": "week_games_20", "title": "Game Marathon", "description": "Complete 20 games this week", "req_type": "games_count", "req_value": 20, "xp": 500},
        {"id": "week_all_languages", "title": "Polyglot", "description": "Complete a game in every language", "req_type": "all_languages", "req_value": 9, "xp": 750},
        {"id": "week_accuracy_95", "title": "Precision Player", "description": "Achieve 95% average accuracy this week", "req_type": "avg_accuracy", "req_value": 95, "xp": 500},
        {"id": "week_hard_5", "title": "Hard Core", "description": "Complete 5 Hard games", "req_type": "hard_count", "req_value": 5, "xp": 600},
        {"id": "week_stars_15", "title": "Star Seeker", "description": "Collect 15 stars this week", "req_type": "stars_count", "req_value": 15, "xp": 400},
        {"id": "week_streak_7", "title": "Daily Devotion", "description": "Play every day this week (7 days)", "req_type": "streak_days", "req_value": 7, "xp": 1000},
    ]

    async def _get_daily_challenge_for_today(self) -> dict:
        day_key = await self._get_today_key()
        import hashlib
        idx = int(hashlib.md5(day_key.encode()).hexdigest(), 16) % len(self.DAILY_CHALLENGE_TYPES)
        ct = self.DAILY_CHALLENGE_TYPES[idx]
        now = datetime.utcnow()
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return {
            "id": f"daily_{day_key}",
            "title": ct["title"],
            "description": ct["description"],
            "type": "daily",
            "requirement_type": ct["req_type"],
            "requirement_value": float(ct["req_value"]) if isinstance(ct["req_value"], (int, float)) else ct["req_value"],
            "xp_reward": ct["xp"],
            "badge_reward": None,
            "starts_at": day_key + "T00:00:00",
            "expires_at": today_end.isoformat(),
            "status": "active",
        }

    async def _get_weekly_challenge(self) -> dict:
        week_key = await self._get_week_key()
        import hashlib
        idx = int(hashlib.md5(week_key.encode()).hexdigest(), 16) % len(self.WEEKLY_CHALLENGE_TYPES)
        ct = self.WEEKLY_CHALLENGE_TYPES[idx]
        now = datetime.utcnow()
        week_end = (now + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
        return {
            "id": f"weekly_{week_key}",
            "title": ct["title"],
            "description": ct["description"],
            "type": "weekly",
            "requirement_type": ct["req_type"],
            "requirement_value": float(ct["req_value"]),
            "xp_reward": ct["xp"],
            "badge_reward": None,
            "starts_at": week_key,
            "expires_at": week_end.isoformat(),
            "status": "active",
        }

    async def _check_daily_challenge_completion(self, user_id: str, data: dict) -> bool:
        db = get_db()
        challenge = await self._get_daily_challenge_for_today()
        day_key = await self._get_today_key()

        # Check if already completed
        existing = await db.syntax_match_challenges.find_one({
            "user_id": user_id, "challenge_id": challenge["id"], "type": "daily",
        })
        if existing and existing.get("status") == "completed":
            return False

        completed = False
        rt = challenge["requirement_type"]
        rv = challenge["requirement_value"]

        if rt == "language":
            completed = data.get("language", "").lower() == str(rv).lower()
        elif rt == "difficulty":
            completed = data.get("difficulty", "").lower() == str(rv).lower()
        elif rt == "accuracy":
            completed = data.get("accuracy", 0) >= float(rv)
        elif rt == "time":
            completed = data.get("completion_time_seconds", 9999) <= float(rv)
        elif rt == "moves":
            completed = data.get("moves", 9999) <= float(rv)
        elif rt == "stars":
            completed = data.get("stars", 0) >= float(rv)

        if completed:
            await db.syntax_match_challenges.update_one(
                {"user_id": user_id, "challenge_id": challenge["id"], "type": "daily"},
                {"$set": {
                    "user_id": user_id, "challenge_id": challenge["id"],
                    "type": "daily", "status": "completed",
                    "progress": 1.0, "completed_at": datetime.utcnow(),
                    "xp_reward": challenge["xp_reward"],
                }},
                upsert=True,
            )
            await self._create_notification(
                user_id, "challenge", "Daily Challenge Complete!",
                f"You completed '{challenge['title']}' — +{challenge['xp_reward']} XP!",
                "zap", datetime.utcnow(),
            )

        return completed

    async def _check_weekly_challenge_progress(self, user_id: str) -> dict:
        db = get_db()
        challenge = await self._get_weekly_challenge()
        week_key = await self._get_week_key()
        week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        existing = await db.syntax_match_challenges.find_one({
            "user_id": user_id, "challenge_id": challenge["id"], "type": "weekly",
        })
        if existing and existing.get("status") == "completed":
            return {"completed": True, "progress": 1.0}

        rt = challenge["requirement_type"]
        rv = challenge["requirement_value"]
        progress = 0.0

        if rt == "games_count":
            count = await db.syntax_match_games.count_documents({
                "user_id": user_id, "created_at": {"$gte": week_start, "$lt": week_end},
            })
            progress = min(count / rv, 1.0)
        elif rt == "all_languages":
            games = await db.syntax_match_games.find({
                "user_id": user_id, "created_at": {"$gte": week_start, "$lt": week_end},
            }).to_list(None)
            langs = set(g["language"] for g in games)
            progress = min(len(langs) / rv, 1.0)
        elif rt == "avg_accuracy":
            games = await db.syntax_match_games.find({
                "user_id": user_id, "created_at": {"$gte": week_start, "$lt": week_end},
            }).to_list(None)
            if games:
                avg = sum(g["accuracy"] for g in games) / len(games)
                progress = min(avg / rv, 1.0)
        elif rt == "hard_count":
            count = await db.syntax_match_games.count_documents({
                "user_id": user_id, "difficulty": "hard",
                "created_at": {"$gte": week_start, "$lt": week_end},
            })
            progress = min(count / rv, 1.0)
        elif rt == "stars_count":
            games = await db.syntax_match_games.find({
                "user_id": user_id, "created_at": {"$gte": week_start, "$lt": week_end},
            }).to_list(None)
            stars = sum(g["stars"] for g in games)
            progress = min(stars / rv, 1.0)
        elif rt == "streak_days":
            stats = await self.get_statistics(user_id)
            progress = min(stats.get("current_streak", 0) / rv, 1.0)

        completed = progress >= 1.0
        if completed:
            await db.syntax_match_challenges.update_one(
                {"user_id": user_id, "challenge_id": challenge["id"], "type": "weekly"},
                {"$set": {
                    "user_id": user_id, "challenge_id": challenge["id"],
                    "type": "weekly", "status": "completed",
                    "progress": 1.0, "completed_at": datetime.utcnow(),
                    "xp_reward": challenge["xp_reward"],
                }},
                upsert=True,
            )
            await self._create_notification(
                user_id, "challenge", "Weekly Challenge Complete!",
                f"You completed '{challenge['title']}' — +{challenge['xp_reward']} XP!",
                "award", datetime.utcnow(),
            )

        await db.syntax_match_challenges.update_one(
            {"user_id": user_id, "challenge_id": challenge["id"], "type": "weekly"},
            {"$set": {"progress": progress}},
            upsert=True,
        )

        return {"completed": completed, "progress": progress}

    async def get_daily_challenge(self, user_id: str) -> dict:
        challenge = await self._get_daily_challenge_for_today()
        db = get_db()
        existing = await db.syntax_match_challenges.find_one({
            "user_id": user_id, "challenge_id": challenge["id"], "type": "daily",
        })
        completed = existing and existing.get("status") == "completed"
        return {"challenge": challenge, "progress": 1.0 if completed else 0.0, "completed": completed}

    async def get_weekly_challenge(self, user_id: str) -> dict:
        challenge = await self._get_weekly_challenge()
        progress_data = await self._check_weekly_challenge_progress(user_id)
        return {
            "challenge": challenge,
            "progress": progress_data["progress"],
            "completed": progress_data["completed"],
        }

    async def get_challenge_history(self, user_id: str) -> list:
        db = get_db()
        challenges = await db.syntax_match_challenges.find(
            {"user_id": user_id}
        ).sort("completed_at", -1).limit(50).to_list(None)
        return [
            {
                "id": c.get("challenge_id", ""),
                "title": c.get("challenge_id", "Challenge").replace("daily_", "").replace("weekly_", ""),
                "type": c.get("type", "daily"),
                "status": c.get("status", "active"),
                "xp_reward": c.get("xp_reward", 0),
                "progress": c.get("progress", 0),
                "completed_at": c.get("completed_at").isoformat() if c.get("completed_at") else None,
            }
            for c in challenges
        ]

    # ── Rewards ──
    async def get_rewards(self, user_id: str) -> dict:
        db = get_db()
        # Get recent XP awards
        xp_entries = await db.syntax_match_xp.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(20).to_list(None)

        total_xp_result = await db.syntax_match_xp.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]).to_list(None)
        total_xp = total_xp_result[0]["total"] if total_xp_result else 0

        recent = []
        for e in xp_entries:
            recent.append({
                "id": str(e["_id"]),
                "type": e.get("source", "xp"),
                "title": e.get("reason", "XP earned").split("(")[0].strip()[:50],
                "description": e.get("reason", ""),
                "icon": "zap" if e.get("source") == "game" else "star",
                "tier": "bronze" if e["amount"] < 50 else "silver" if e["amount"] < 150 else "gold" if e["amount"] < 500 else "diamond",
                "xp_awarded": e["amount"],
                "source": e.get("source", "xp"),
                "unlocked_at": e["created_at"].isoformat(),
                "claimed": True,
            })

        return {"recent": recent, "total_xp_earned": total_xp, "total_rewards": len(recent)}

    # ── Notifications ──
    async def _create_notification(self, user_id: str, ntype: str, title: str, message: str, icon: str, now: datetime):
        db = get_db()
        await db.syntax_match_notifications.insert_one({
            "user_id": user_id, "type": ntype, "title": title,
            "message": message, "icon": icon, "read": False, "created_at": now,
        })

    async def get_notifications(self, user_id: str) -> dict:
        db = get_db()
        notifs = await db.syntax_match_notifications.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(20).to_list(None)
        unread = await db.syntax_match_notifications.count_documents(
            {"user_id": user_id, "read": False}
        )
        return {
            "notifications": [
                {
                    "id": str(n["_id"]),
                    "type": n["type"],
                    "title": n["title"],
                    "message": n["message"],
                    "icon": n["icon"],
                    "read": n.get("read", False),
                    "created_at": n["created_at"].isoformat(),
                }
                for n in notifs
            ],
            "unread_count": unread,
        }

    async def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        from bson.objectid import ObjectId
        db = get_db()
        result = await db.syntax_match_notifications.update_one(
            {"_id": ObjectId(notification_id), "user_id": user_id},
            {"$set": {"read": True}},
        )
        return result.modified_count > 0

    async def mark_all_notifications_read(self, user_id: str) -> bool:
        db = get_db()
        result = await db.syntax_match_notifications.update_many(
            {"user_id": user_id, "read": False},
            {"$set": {"read": True}},
        )
        return result.modified_count > 0


syntax_match_service = SyntaxMatchService()
