import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Any
from app.repositories.admin_repository import AdminRepository
from app.repositories.user_repository import UserRepository
from app.utils.security import hash_password, verify_password, create_access_token


class AdminService:
    def __init__(self):
        self.admin_repo = AdminRepository()
        self.user_repo = UserRepository()

    # ─── Authentication ────────────────────────────────────────────

    async def admin_login(self, email: str, password: str) -> dict:
        user = await self.user_repo.find_by_email(email)
        if not user:
            raise ValueError("Invalid credentials")

        if not verify_password(password, user["password_hash"]):
            raise ValueError("Invalid credentials")

        role = user.get("role", "user")
        admin_roles = {"super_admin", "admin", "moderator", "content_manager", "support"}
        if role not in admin_roles:
            raise ValueError("Admin access required")

        if user.get("account_status") != "active":
            raise ValueError("Account is not active")

        await self.user_repo.update_last_login(user["_id"])

        from datetime import timedelta
        access_token = create_access_token(
            {"sub": user["_id"], "email": user["email"]},
            expires_delta=timedelta(hours=12),
        )

        await self.admin_repo.log_admin_action({
            "admin_id": user["_id"],
            "admin_email": user["email"],
            "action": "login",
            "resource_type": "auth",
            "ip_address": None,
        })

        user.pop("password_hash", None)
        user.pop("reset_token", None)
        user.pop("reset_token_expires", None)
        user.pop("verification_token", None)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 43200,
            "user": user,
        }

    # ─── Dashboard ─────────────────────────────────────────────────

    async def get_dashboard_stats(self) -> dict:
        total_users = await self.admin_repo.count_users()
        active_today = await self.admin_repo.count_active_users_today()
        new_registrations = await self.admin_repo.count_new_registrations(days=7)
        avg_stats = await self.admin_repo.get_average_stats()
        lang_dist = await self.admin_repo.get_language_distribution()
        user_growth = await self.admin_repo.get_user_growth(days=30)
        activity = await self.admin_repo.get_activity_data(days=30)
        completed_challenges = await self.admin_repo.count_completed_challenges()
        total_certs = await self.admin_repo.count_certificates()
        leaderboard_count = await self.admin_repo.get_leaderboard_count()

        return {
            "total_users": total_users,
            "active_users_today": active_today,
            "new_registrations": new_registrations,
            "completed_tests": avg_stats.get("total_sessions", 0),
            "daily_challenges_completed": completed_challenges,
            "average_accuracy": avg_stats.get("average_accuracy", 0),
            "average_wpm": avg_stats.get("average_wpm", 0),
            "certificates_issued": total_certs,
            "leaderboard_entries": leaderboard_count,
            "server_status": "operational",
            "api_status": "operational",
            "database_status": "connected",
            "user_growth_data": user_growth,
            "language_distribution": lang_dist,
            "activity_data": activity,
        }

    # ─── User Management ───────────────────────────────────────────

    async def get_users(self, **kwargs) -> dict:
        return await self.admin_repo.get_users(**kwargs)

    async def get_user(self, user_id: str) -> Optional[dict]:
        return await self.admin_repo.get_user_by_id(user_id)

    async def update_user_role(self, user_id: str, role: str, admin_id: str) -> bool:
        result = await self.admin_repo.update_user(user_id, {"role": role})
        if result:
            await self.admin_repo.log_admin_action({
                "admin_id": admin_id,
                "admin_email": "",
                "action": "assign_role",
                "resource_type": "user",
                "resource_id": user_id,
                "details": {"new_role": role},
            })
        return result

    async def suspend_user(self, user_id: str, reason: str, admin_id: str) -> bool:
        result = await self.admin_repo.update_user(user_id, {"account_status": "suspended"})
        if result:
            await self.admin_repo.log_admin_action({
                "admin_id": admin_id,
                "admin_email": "",
                "action": "suspend",
                "resource_type": "user",
                "resource_id": user_id,
                "details": {"reason": reason},
            })
        return result

    async def reactivate_user(self, user_id: str, admin_id: str) -> bool:
        result = await self.admin_repo.update_user(user_id, {"account_status": "active"})
        if result:
            await self.admin_repo.log_admin_action({
                "admin_id": admin_id,
                "admin_email": "",
                "action": "reactivate",
                "resource_type": "user",
                "resource_id": user_id,
            })
        return result

    async def delete_user(self, user_id: str, admin_id: str) -> bool:
        result = await self.admin_repo.delete_user(user_id)
        if result:
            await self.admin_repo.log_admin_action({
                "admin_id": admin_id,
                "admin_email": "",
                "action": "delete",
                "resource_type": "user",
                "resource_id": user_id,
            })
        return result

    async def reset_user_stats(self, user_id: str, admin_id: str) -> bool:
        from app.database import get_db
        db = get_db()
        await db.codesprint_user_stats.update_one(
            {"user_id": user_id},
            {"$set": {
                "total_tests": 0, "total_practice_seconds": 0,
                "avg_wpm": 0, "best_wpm": 0, "avg_accuracy": 0, "best_accuracy": 0,
            }},
        )
        await self.admin_repo.log_admin_action({
            "admin_id": admin_id,
            "admin_email": "",
            "action": "reset_stats",
            "resource_type": "user",
            "resource_id": user_id,
        })
        return True

    # ─── Snippet Management ────────────────────────────────────────

    async def get_snippets(self, **kwargs) -> dict:
        return await self.admin_repo.get_snippets(**kwargs)

    async def create_snippet(self, data: dict, admin_id: str) -> str:
        snippet_id = await self.admin_repo.create_snippet(data)
        await self.admin_repo.log_admin_action({
            "admin_id": admin_id,
            "admin_email": "",
            "action": "create",
            "resource_type": "snippet",
            "resource_id": snippet_id,
        })
        return snippet_id

    async def update_snippet(self, snippet_id: str, data: dict, admin_id: str) -> bool:
        result = await self.admin_repo.update_snippet(snippet_id, data)
        if result:
            await self.admin_repo.log_admin_action({
                "admin_id": admin_id,
                "admin_email": "",
                "action": "update",
                "resource_type": "snippet",
                "resource_id": snippet_id,
            })
        return result

    async def delete_snippet(self, snippet_id: str, admin_id: str) -> bool:
        result = await self.admin_repo.delete_snippet(snippet_id)
        if result:
            await self.admin_repo.log_admin_action({
                "admin_id": admin_id,
                "admin_email": "",
                "action": "delete",
                "resource_type": "snippet",
                "resource_id": snippet_id,
            })
        return result

    async def duplicate_snippet(self, snippet_id: str, admin_id: str) -> Optional[str]:
        from app.database import get_db
        db = get_db()
        from bson import ObjectId
        original = await db.codesprint_snippets.find_one({"_id": ObjectId(snippet_id)})
        if not original:
            return None
        original.pop("_id", None)
        original["title"] = original.get("title", "") + " (Copy)"
        original["created_at"] = datetime.utcnow()
        original["updated_at"] = datetime.utcnow()
        result = await db.codesprint_snippets.insert_one(original)
        new_id = str(result.inserted_id)
        await self.admin_repo.log_admin_action({
            "admin_id": admin_id,
            "admin_email": "",
            "action": "create",
            "resource_type": "snippet",
            "resource_id": new_id,
            "details": {"duplicated_from": snippet_id},
        })
        return new_id

    async def bulk_import_snippets(self, snippets: list, admin_id: str) -> int:
        count = await self.admin_repo.bulk_create_snippets(snippets)
        await self.admin_repo.log_admin_action({
            "admin_id": admin_id,
            "admin_email": "",
            "action": "import",
            "resource_type": "snippet",
            "details": {"count": count},
        })
        return count

    # ─── Category Management ───────────────────────────────────────

    async def get_categories(self, language: Optional[str] = None) -> list:
        return await self.admin_repo.get_categories(language)

    async def create_category(self, data: dict, admin_id: str) -> str:
        cat_id = await self.admin_repo.create_category(data)
        await self.admin_repo.log_admin_action({
            "admin_id": admin_id,
            "admin_email": "",
            "action": "create",
            "resource_type": "category",
            "resource_id": cat_id,
        })
        return cat_id

    async def update_category(self, cat_id: str, data: dict, admin_id: str) -> bool:
        result = await self.admin_repo.update_category(cat_id, data)
        if result:
            await self.admin_repo.log_admin_action({
                "admin_id": admin_id,
                "admin_email": "",
                "action": "update",
                "resource_type": "category",
                "resource_id": cat_id,
            })
        return result

    async def delete_category(self, cat_id: str, admin_id: str) -> bool:
        result = await self.admin_repo.delete_category(cat_id)
        if result:
            await self.admin_repo.log_admin_action({
                "admin_id": admin_id,
                "admin_email": "",
                "action": "delete",
                "resource_type": "category",
                "resource_id": cat_id,
            })
        return result

    # ─── Challenge Management ──────────────────────────────────────

    async def get_challenges(self, **kwargs) -> dict:
        return await self.admin_repo.get_challenges(**kwargs)

    async def get_weekly_challenges(self, **kwargs) -> dict:
        return await self.admin_repo.get_weekly_challenges(**kwargs)

    async def create_challenge(self, data: dict, admin_id: str) -> str:
        challenge_id = await self.admin_repo.create_challenge(data)
        await self.admin_repo.log_admin_action({
            "admin_id": admin_id,
            "admin_email": "",
            "action": "challenge_create",
            "resource_type": "challenge",
            "resource_id": challenge_id,
        })
        return challenge_id

    async def archive_challenge(self, challenge_id: str, admin_id: str) -> bool:
        result = await self.admin_repo.update_challenge(challenge_id, {"archived": True})
        if result:
            await self.admin_repo.log_admin_action({
                "admin_id": admin_id,
                "admin_email": "",
                "action": "challenge_archive",
                "resource_type": "challenge",
                "resource_id": challenge_id,
            })
        return result

    async def delete_challenge(self, challenge_id: str, admin_id: str) -> bool:
        result = await self.admin_repo.delete_challenge(challenge_id)
        if result:
            await self.admin_repo.log_admin_action({
                "admin_id": admin_id,
                "admin_email": "",
                "action": "delete",
                "resource_type": "challenge",
                "resource_id": challenge_id,
            })
        return result

    # ─── Certificate Management ────────────────────────────────────

    async def get_certificates(self, **kwargs) -> dict:
        return await self.admin_repo.get_certificates(**kwargs)

    async def create_certificate(self, data: dict, admin_id: str) -> str:
        data["verification_code"] = secrets.token_urlsafe(32)
        user = await self.admin_repo.get_user_by_id(data.get("user_id", ""))
        if user:
            data["user_name"] = user.get("full_name", "")
            data["user_email"] = user.get("email", "")
        cert_id = await self.admin_repo.create_certificate(data)
        await self.admin_repo.log_admin_action({
            "admin_id": admin_id,
            "admin_email": "",
            "action": "certificate_issue",
            "resource_type": "certificate",
            "resource_id": cert_id,
        })
        return cert_id

    async def revoke_certificate(self, cert_id: str, reason: str, admin_id: str) -> bool:
        result = await self.admin_repo.revoke_certificate(cert_id, reason)
        if result:
            await self.admin_repo.log_admin_action({
                "admin_id": admin_id,
                "admin_email": "",
                "action": "certificate_revoke",
                "resource_type": "certificate",
                "resource_id": cert_id,
                "details": {"reason": reason},
            })
        return result

    async def verify_certificate(self, code: str) -> Optional[dict]:
        return await self.admin_repo.verify_certificate(code)

    async def get_certificate_templates(self) -> list:
        return await self.admin_repo.get_certificate_templates()

    async def create_certificate_template(self, data: dict, admin_id: str) -> str:
        tmpl_id = await self.admin_repo.create_certificate_template(data)
        await self.admin_repo.log_admin_action({
            "admin_id": admin_id,
            "admin_email": "",
            "action": "create",
            "resource_type": "certificate_template",
            "resource_id": tmpl_id,
        })
        return tmpl_id

    async def update_certificate_template(self, tmpl_id: str, data: dict, admin_id: str) -> bool:
        return await self.admin_repo.update_certificate_template(tmpl_id, data)

    async def delete_certificate_template(self, tmpl_id: str, admin_id: str) -> bool:
        return await self.admin_repo.delete_certificate_template(tmpl_id)

    # ─── Leaderboard Management ────────────────────────────────────

    async def refresh_leaderboard(self, metrics: list, admin_id: str) -> dict:
        results = {}
        for metric in metrics:
            results[metric] = await self.admin_repo.get_leaderboard(metric, 100)
        await self.admin_repo.log_admin_action({
            "admin_id": admin_id,
            "admin_email": "",
            "action": "leaderboard_refresh",
            "resource_type": "leaderboard",
            "details": {"metrics": metrics},
        })
        return results

    async def remove_invalid_scores(self, admin_id: str) -> int:
        count = await self.admin_repo.remove_invalid_scores()
        await self.admin_repo.log_admin_action({
            "admin_id": admin_id,
            "admin_email": "",
            "action": "update",
            "resource_type": "leaderboard",
            "details": {"removed_invalid_scores": count},
        })
        return count

    async def detect_suspicious_activity(self, threshold: float = 0.95) -> list:
        return await self.admin_repo.detect_suspicious(threshold)

    # ─── Reports ───────────────────────────────────────────────────

    async def generate_report(self, report_type: str, days: int = 30) -> dict:
        if report_type == "user_growth":
            return await self.admin_repo.generate_user_growth_report(days)
        elif report_type == "practice_stats":
            return await self.admin_repo.generate_practice_stats_report()
        elif report_type == "popular_languages":
            return await self.admin_repo.generate_popular_languages_report()
        elif report_type == "top_performers":
            return await self.admin_repo.generate_top_performers_report()
        elif report_type == "inactive_users":
            return await self.admin_repo.generate_inactive_users_report(days)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    # ─── Audit Log ─────────────────────────────────────────────────

    async def get_audit_logs(self, **kwargs) -> dict:
        return await self.admin_repo.get_audit_logs(**kwargs)

    # ─── Settings ──────────────────────────────────────────────────

    async def get_settings(self, category: Optional[str] = None) -> list:
        return await self.admin_repo.get_settings(category)

    async def update_setting(self, key: str, value: Any, category: str, admin_id: str) -> bool:
        result = await self.admin_repo.update_setting(key, value, category, admin_id)
        if result:
            await self.admin_repo.log_admin_action({
                "admin_id": admin_id,
                "admin_email": "",
                "action": "settings_change",
                "resource_type": "settings",
                "details": {"key": key, "value": value},
            })
        return result

    # ─── Notifications ─────────────────────────────────────────────

    async def broadcast_notification(self, data: dict, admin_id: str) -> str:
        data["sent_by"] = admin_id
        data["sent_at"] = datetime.utcnow()
        notif_id = await self.admin_repo.create_notification(data)
        await self.admin_repo.log_admin_action({
            "admin_id": admin_id,
            "admin_email": "",
            "action": "broadcast",
            "resource_type": "notification",
            "resource_id": notif_id,
        })
        return notif_id

    async def get_notifications(self, **kwargs) -> dict:
        return await self.admin_repo.get_notifications(**kwargs)

    async def delete_notification(self, notif_id: str, admin_id: str) -> bool:
        result = await self.admin_repo.delete_notification(notif_id)
        if result:
            await self.admin_repo.log_admin_action({
                "admin_id": admin_id,
                "admin_email": "",
                "action": "delete",
                "resource_type": "notification",
                "resource_id": notif_id,
            })
        return result

    # ─── Global Search ─────────────────────────────────────────────

    async def global_search(self, query_str: str, types: list, page: int = 1, limit: int = 20) -> dict:
        return await self.admin_repo.global_search(query_str, types, page, limit)


admin_service = AdminService()
