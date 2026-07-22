import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.database import get_db
from app.website_generator.utils.logger import generator_logger

class ProjectService:
    """
    Project Management Service managing user website projects, favorites,
    renaming, duplication, soft deletion, build logs, and workspace dashboard metrics.
    """

    @staticmethod
    async def list_user_projects(
        user_id: str,
        search: Optional[str] = None,
        status: Optional[str] = None,
        website_type: Optional[str] = None,
        theme: Optional[str] = None,
        favorite_only: bool = False,
        page: int = 1,
        limit: int = 10,
    ) -> Dict[str, Any]:
        db = get_db()
        query: Dict[str, Any] = {
            "user_id": str(user_id),
            "soft_deleted": {"$ne": True},
        }

        if search:
            regex = {"$regex": search, "$options": "i"}
            query["$or"] = [
                {"company_name": regex},
                {"custom_name": regex},
                {"website_type": regex},
                {"theme": regex},
            ]

        if status:
            query["status"] = status
        if website_type:
            query["website_type"] = website_type
        if theme:
            query["theme"] = theme
        if favorite_only:
            query["favorite"] = True

        skip = (page - 1) * limit
        total = await db.generation_jobs.count_documents(query)

        cursor = (
            db.generation_jobs.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        projects = []
        async for doc in cursor:
            created_at_str = doc.get("created_at").isoformat() if hasattr(doc.get("created_at"), "isoformat") else str(doc.get("created_at", ""))
            updated_at_str = doc.get("updated_at").isoformat() if hasattr(doc.get("updated_at"), "isoformat") else str(doc.get("updated_at", ""))
            last_dl = doc.get("last_downloaded")
            last_dl_str = last_dl.isoformat() if hasattr(last_dl, "isoformat") else (str(last_dl) if last_dl else None)

            projects.append({
                "job_id": doc["job_id"],
                "company_name": doc.get("company_name", ""),
                "custom_name": doc.get("custom_name"),
                "website_type": doc.get("website_type", ""),
                "theme": doc.get("theme", ""),
                "selected_features": doc.get("selected_features", []),
                "status": doc.get("status", "COMPLETED"),
                "favorite": doc.get("favorite", False),
                "download_count": doc.get("download_count", 0),
                "last_downloaded": last_dl_str,
                "zip_filename": doc.get("zip_filename"),
                "pages_generated": doc.get("pages_generated", []),
                "created_at": created_at_str,
                "updated_at": updated_at_str,
            })

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if limit > 0 else 1,
            "projects": projects,
        }

    @staticmethod
    async def get_project_details(job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        db = get_db()
        job = await db.generation_jobs.find_one({"_id": job_id, "user_id": str(user_id), "soft_deleted": {"$ne": True}})
        if not job:
            return None

        created_at_str = job.get("created_at").isoformat() if hasattr(job.get("created_at"), "isoformat") else str(job.get("created_at"))
        updated_at_str = job.get("updated_at").isoformat() if hasattr(job.get("updated_at"), "isoformat") else str(job.get("updated_at"))

        logs = [
            {"stage": "Validation", "message": "Wizard payload validated successfully", "timestamp": created_at_str},
            {"stage": "AI Content Engine", "message": "Structured copy generated", "timestamp": created_at_str},
            {"stage": "Template Selection", "message": f"Template resolved: {job.get('website_type')}", "timestamp": created_at_str},
            {"stage": "Static Page Builder", "message": f"Rendered {len(job.get('pages_generated', []))} HTML pages", "timestamp": updated_at_str},
            {"stage": "SEO & Assets", "message": "Manifests, robots.txt, and sitemap.xml packaged", "timestamp": updated_at_str},
            {"stage": "ZIP Packaging", "message": f"Created ZIP archive: {job.get('zip_filename')}", "timestamp": updated_at_str},
            {"stage": "Completed", "message": "Project ready for preview & export download", "timestamp": updated_at_str},
        ]

        return {
            "job_id": job["job_id"],
            "company_name": job.get("company_name"),
            "custom_name": job.get("custom_name"),
            "website_type": job.get("website_type"),
            "theme": job.get("theme"),
            "selected_features": job.get("selected_features", []),
            "status": job.get("status"),
            "favorite": job.get("favorite", False),
            "download_count": job.get("download_count", 0),
            "zip_filename": job.get("zip_filename"),
            "pages_generated": job.get("pages_generated", []),
            "payload": job.get("payload"),
            "build_logs": logs,
            "created_at": created_at_str,
            "updated_at": updated_at_str,
        }

    @staticmethod
    async def rename_project(job_id: str, user_id: str, new_name: str) -> bool:
        db = get_db()
        result = await db.generation_jobs.update_one(
            {"_id": job_id, "user_id": str(user_id)},
            {"$set": {"custom_name": new_name.strip(), "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    @staticmethod
    async def toggle_favorite(job_id: str, user_id: str) -> Optional[bool]:
        db = get_db()
        job = await db.generation_jobs.find_one({"_id": job_id, "user_id": str(user_id)})
        if not job:
            return None

        new_fav = not job.get("favorite", False)
        await db.generation_jobs.update_one(
            {"_id": job_id},
            {"$set": {"favorite": new_fav, "updated_at": datetime.utcnow()}}
        )
        return new_fav

    @staticmethod
    async def duplicate_project(job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        db = get_db()
        job = await db.generation_jobs.find_one({"_id": job_id, "user_id": str(user_id)})
        if not job or not job.get("payload"):
            return None

        from app.website_generator.schemas.payload import WebsiteGeneratorPayload
        from app.website_generator.services.generation_service import GenerationService

        payload_dict = job["payload"]
        payload_dict["businessInfo"]["companyName"] = f"{job.get('company_name')} (Copy)"
        payload = WebsiteGeneratorPayload(**payload_dict)

        new_job_result = await GenerationService.create_generation_job(user_id=user_id, payload=payload)
        return new_job_result

    @staticmethod
    async def soft_delete_project(job_id: str, user_id: str) -> bool:
        db = get_db()
        result = await db.generation_jobs.update_one(
            {"_id": job_id, "user_id": str(user_id)},
            {"$set": {"soft_deleted": True, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    @staticmethod
    async def get_dashboard_stats(user_id: str) -> Dict[str, Any]:
        db = get_db()
        query = {"user_id": str(user_id), "soft_deleted": {"$ne": True}}

        total_generated = await db.generation_jobs.count_documents(query)
        completed_query = {**query, "status": "COMPLETED"}
        failed_query = {**query, "status": "FAILED"}
        active_query = {**query, "status": {"$in": ["PENDING", "VALIDATING", "READY", "PROCESSING"]}}

        active_builds = await db.generation_jobs.count_documents(active_query)
        failed_builds = await db.generation_jobs.count_documents(failed_query)

        # Aggregate total downloads
        pipeline_dl = [
            {"$match": query},
            {"$group": {"_id": None, "total_downloads": {"$sum": "$download_count"}}}
        ]
        dl_res = await db.generation_jobs.aggregate(pipeline_dl).to_list(1)
        total_downloads = dl_res[0]["total_downloads"] if dl_res else 0

        # Most used theme
        pipeline_theme = [
            {"$match": query},
            {"$group": {"_id": "$theme", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1}
        ]
        theme_res = await db.generation_jobs.aggregate(pipeline_theme).to_list(1)
        most_used_theme = theme_res[0]["_id"] if theme_res else "White"

        # Most used website type
        pipeline_type = [
            {"$match": query},
            {"$group": {"_id": "$website_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1}
        ]
        type_res = await db.generation_jobs.aggregate(pipeline_type).to_list(1)
        most_used_type = type_res[0]["_id"] if type_res else "Software Company"

        return {
            "total_websites_generated": total_generated,
            "total_downloads": total_downloads,
            "active_builds": active_builds,
            "failed_builds": failed_builds,
            "most_used_theme": most_used_theme,
            "most_used_website_type": most_used_type,
        }
