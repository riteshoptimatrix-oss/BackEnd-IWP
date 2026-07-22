import os
import shutil
from datetime import datetime
from typing import Dict, Any
from app.database import get_db
from app.website_generator.schemas.payload import WebsiteGeneratorPayload
from app.website_generator.builder_engine.page_generator import PageGenerator
from app.website_generator.builder_engine.asset_builder import AssetBuilder
from app.website_generator.builder_engine.seo_builder import SEOBuilder
from app.website_generator.builder_engine.website_validator import WebsiteValidator
from app.website_generator.builder_engine.zip_builder import ZipBuilder
from app.website_generator.utils.logger import generator_logger

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPORTS_DIR = os.path.join(BACKEND_DIR, "exports")

class ExportBuilder:
    """
    Phase 6 Website Builder Orchestrator.
    Executes full build pipeline across granular progress stages:
    PREPARING -> GENERATING_CONTENT -> BUILDING_PAGES -> BUILDING_ASSETS -> OPTIMIZING -> PACKAGING -> COMPLETED
    """
    @staticmethod
    async def update_progress(job_id: str, stage: str, percentage: int, message: str) -> None:
        db = get_db()
        now = datetime.utcnow()
        await db.generation_jobs.update_one(
            {"_id": job_id},
            {"$set": {
                "status": stage,
                "progress_percentage": percentage,
                "progress_message": message,
                "updated_at": now,
            }}
        )

    @classmethod
    async def build_website(cls, job_id: str, payload: WebsiteGeneratorPayload) -> Dict[str, Any]:
        generator_logger.info(f"Starting Phase 6 Website Builder Engine for job '{job_id}'...")
        db = get_db()

        # Stage 1: PREPARING (10%)
        await cls.update_progress(job_id, "PREPARING", 10, "Preparing website build workspace...")
        job_output_dir = os.path.join(EXPORTS_DIR, job_id)
        if os.path.exists(job_output_dir):
            shutil.rmtree(job_output_dir)
        os.makedirs(job_output_dir, exist_ok=True)

        try:
            # Stage 2: GENERATING_CONTENT (30%)
            await cls.update_progress(job_id, "GENERATING_CONTENT", 30, "Generating business copy with AI Content Engine...")

            # Stage 3: BUILDING_PAGES (50%)
            await cls.update_progress(job_id, "BUILDING_PAGES", 50, "Rendering static HTML pages...")
            generated_pages = PageGenerator.generate_all_pages(job_output_dir, payload)

            # Stage 4: BUILDING_ASSETS (70%)
            await cls.update_progress(job_id, "BUILDING_ASSETS", 70, "Organizing CSS, JS, fonts, and shared image assets...")
            AssetBuilder.build_and_optimize_assets(job_output_dir)

            # Stage 5: OPTIMIZING (85%)
            await cls.update_progress(job_id, "OPTIMIZING", 85, "Building SEO tags, sitemaps, robots.txt, and validating site...")
            SEOBuilder.build_seo_assets(job_output_dir, payload, generated_pages)

            is_valid, validation_errors = WebsiteValidator.validate_build(job_output_dir, generated_pages)
            if not is_valid:
                raise ValueError(f"Build validation error: {', '.join(validation_errors)}")

            # Stage 6: PACKAGING (95%)
            await cls.update_progress(job_id, "PACKAGING", 95, "Compressing website package into ZIP archive...")
            zip_path, zip_filename = ZipBuilder.create_zip_archive(job_output_dir, payload.businessInfo.companyName)

            # Stage 7: COMPLETED (100%)
            now = datetime.utcnow()
            await db.generation_jobs.update_one(
                {"_id": job_id},
                {"$set": {
                    "status": "COMPLETED",
                    "progress_percentage": 100,
                    "progress_message": "Website build and ZIP packaging completed successfully!",
                    "updated_at": now,
                    "export_path": job_output_dir,
                    "zip_filename": zip_filename,
                    "pages_generated": generated_pages,
                }}
            )

            await db.generation_history.update_one(
                {"job_id": job_id},
                {"$set": {"status": "COMPLETED"}}
            )

            generator_logger.info(f"Phase 6 Website Builder Engine successfully completed job '{job_id}'!")
            return {
                "job_id": job_id,
                "status": "COMPLETED",
                "zip_filename": zip_filename,
                "export_dir": job_output_dir,
                "pages": generated_pages,
            }

        except Exception as exc:
            generator_logger.error(f"Website Builder Engine failed for job '{job_id}': {str(exc)}")
            await db.generation_jobs.update_one(
                {"_id": job_id},
                {"$set": {
                    "status": "FAILED",
                    "progress_percentage": 0,
                    "error_message": f"Build failure: {str(exc)}",
                    "updated_at": datetime.utcnow(),
                }}
            )
            raise exc
