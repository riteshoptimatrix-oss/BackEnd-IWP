from typing import Dict, Any

class ZipArchiveService:
    """
    Prepares ZIP archive structure metadata for future project code exports.
    """
    @staticmethod
    def prepare_export_metadata(job_id: str, company_name: str) -> Dict[str, Any]:
        sanitized_name = "".join(c if c.isalnum() else "_" for c in company_name).lower()
        return {
            "archive_filename": f"{sanitized_name}_website_export_{job_id[:8]}.zip",
            "format": "zip",
            "included_directories": ["app/", "components/", "public/", "styles/"],
            "manifest_files": ["package.json", "tsconfig.json", "tailwind.config.js"],
            "ready_for_export": True,
        }
