import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from bson import ObjectId
from app.database import get_db
from app.website_generator.schemas.payload import WebsiteGeneratorPayload
from app.website_generator.builder.pipeline_builder import PipelineBuilder
from app.website_generator.utils.logger import generator_logger

class GenerationService:
    """
    Service managing generation job lifecycles and MongoDB persistence.
    Status Lifecycle: PENDING -> VALIDATING -> READY -> PROCESSING -> COMPLETED / FAILED
    """
    @staticmethod
    async def create_generation_job(user_id: str, payload: WebsiteGeneratorPayload) -> Dict[str, Any]:
        db = get_db()
        job_uuid = str(uuid.uuid4())
        now = datetime.utcnow()

        generator_logger.info(f"Creating job {job_uuid} for user {user_id}")

        # Step A: Create PENDING job doc
        job_doc = {
            "_id": job_uuid,
            "job_id": job_uuid,
            "user_id": str(user_id),
            "company_name": payload.businessInfo.companyName,
            "website_type": payload.websiteType,
            "theme": payload.theme,
            "selected_features": payload.selectedFeatures,
            "status": "PENDING",
            "payload": payload.dict(),
            "placeholder_meta": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
        await db.generation_jobs.insert_one(job_doc)

        # Step B: Transition to VALIDATING & process pipeline
        await db.generation_jobs.update_one(
            {"_id": job_uuid},
            {"$set": {"status": "VALIDATING", "updated_at": datetime.utcnow()}}
        )

        is_valid, errors, pipeline_result = PipelineBuilder.process_pipeline(payload)
        if not is_valid:
            error_msg = f"Validation failed: {', '.join(errors.values())}"
            await db.generation_jobs.update_one(
                {"_id": job_uuid},
                {"$set": {"status": "FAILED", "error_message": error_msg, "updated_at": datetime.utcnow()}}
            )
            generator_logger.error(f"Job {job_uuid} failed validation")
            raise ValueError(error_msg)

        # Step C: Transition to READY & attach placeholder metadata
        placeholder_meta = pipeline_result.get("placeholder_meta")
        await db.generation_jobs.update_one(
            {"_id": job_uuid},
            {"$set": {
                "status": "READY",
                "placeholder_meta": placeholder_meta,
                "updated_at": datetime.utcnow()
            }}
        )

        # Step D: Record in generation_history collection
        history_doc = {
            "job_id": job_uuid,
            "user_id": str(user_id),
            "company_name": payload.businessInfo.companyName,
            "website_type": payload.websiteType,
            "theme": payload.theme,
            "selected_features": payload.selectedFeatures,
            "status": "READY",
            "created_at": now,
        }
        await db.generation_history.insert_one(history_doc)

        # Step E: Trigger Phase 4 Static Website Builder
        from app.website_generator.template_engine.export_builder import ExportBuilder
        build_result = await ExportBuilder.build_website(job_uuid, payload)

        return {
            "job_id": job_uuid,
            "status": "COMPLETED",
            "message": "Static website build completed successfully via Phase 4 Template Engine.",
            "company_name": payload.businessInfo.companyName,
            "estimated_duration_seconds": 0,
            "created_at": now.isoformat(),
        }

    @staticmethod
    async def get_job_status(job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        db = get_db()
        job = await db.generation_jobs.find_one({"_id": job_id})
        if not job:
            return None

        # Verify owner permissions
        if str(job.get("user_id")) != str(user_id):
            return None

        created_at_str = job.get("created_at").isoformat() if hasattr(job.get("created_at"), "isoformat") else str(job.get("created_at"))
        updated_at_str = job.get("updated_at").isoformat() if hasattr(job.get("updated_at"), "isoformat") else str(job.get("updated_at"))

        return {
            "job_id": job["job_id"],
            "user_id": str(job["user_id"]),
            "company_name": job["company_name"],
            "website_type": job["website_type"],
            "theme": job["theme"],
            "status": job["status"],
            "error_message": job.get("error_message"),
            "created_at": created_at_str,
            "updated_at": updated_at_str,
            "placeholder_meta": job.get("placeholder_meta"),
        }
