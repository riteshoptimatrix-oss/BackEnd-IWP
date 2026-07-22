import os
from typing import Tuple, Optional
from app.database import get_db

class DownloadService:
    """
    Download Service facilitating secure authenticated ZIP downloads.
    Guarantees failed or incomplete builds cannot be downloaded.
    """
    @staticmethod
    async def get_download_file(job_id: str, user_id: str) -> Tuple[Optional[str], Optional[str]]:
        db = get_db()
        job = await db.generation_jobs.find_one({"_id": job_id})
        if not job:
            return None, None

        # Verify owner permission
        if str(job.get("user_id")) != str(user_id):
            return None, None

        # Verify completed status
        if job.get("status") != "COMPLETED":
            return None, None

        export_dir = job.get("export_path")
        if not export_dir or not os.path.exists(export_dir):
            return None, None

        company_name = job.get("company_name", "Website")
        sanitized_company = "".join(c if c.isalnum() else "-" for c in company_name).strip("-")
        zip_filename = f"{sanitized_company}-Website.zip"
        zip_path = os.path.join(export_dir, zip_filename)

        if not os.path.exists(zip_path):
            return None, None

        # Increment download count & update timestamp
        from datetime import datetime
        await db.generation_jobs.update_one(
            {"_id": job_id},
            {
                "$inc": {"download_count": 1},
                "$set": {"last_downloaded": datetime.utcnow()}
            }
        )

        return zip_path, zip_filename
