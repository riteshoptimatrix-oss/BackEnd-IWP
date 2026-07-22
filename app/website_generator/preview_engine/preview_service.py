import os
from typing import Optional
from app.database import get_db

class PreviewService:
    """
    Preview Service providing page preview content for completed or in-progress builds.
    """
    @staticmethod
    async def get_page_preview(job_id: str, page_name: str, user_id: str) -> Optional[str]:
        db = get_db()
        job = await db.generation_jobs.find_one({"_id": job_id})
        if not job:
            return None

        # Verify user ownership
        if str(job.get("user_id")) != str(user_id):
            return None

        export_dir = job.get("export_path")
        if not export_dir or not os.path.exists(export_dir):
            return None

        # Security check: sanitize page_name
        sanitized_page = os.path.basename(page_name)
        if not sanitized_page.endswith(".html"):
            sanitized_page += ".html"

        file_path = os.path.join(export_dir, sanitized_page)
        if not os.path.exists(file_path):
            file_path = os.path.join(export_dir, "index.html")

        if not os.path.exists(file_path):
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
