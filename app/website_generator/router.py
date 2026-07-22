from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, FileResponse
from typing import Dict, Any, Optional

from app.middleware.auth import get_current_user
from app.database import get_db
from app.website_generator.schemas.payload import (
    WebsiteGeneratorPayload,
    ValidateResponseSchema,
    StartGenerationRequestSchema,
    StartGenerationResponseSchema,
    JobStatusResponseSchema,
    GenerationHistoryResponseSchema,
    GenerationHistoryItemSchema,
)
from app.website_generator.validators.payload_validator import PayloadValidator
from app.website_generator.services.generation_service import GenerationService
from app.website_generator.services.project_service import ProjectService
from app.website_generator.history.history_service import HistoryService
from app.website_generator.preview_engine.preview_service import PreviewService
from app.website_generator.download_engine.download_service import DownloadService
from app.website_generator.utils.logger import generator_logger

router = APIRouter(prefix="/website-generator", tags=["Website Generator"])

@router.post("/validate", response_model=ValidateResponseSchema)
async def validate_wizard_payload(payload: WebsiteGeneratorPayload):
    """
    Validates a Phase 2 Website Generator wizard input payload.
    Does not mutate database state or trigger jobs.
    """
    generator_logger.info(f"Validating payload for: {payload.businessInfo.companyName}")
    is_valid, errors = PayloadValidator.validate(payload)

    summary = {
        "company_name": payload.businessInfo.companyName,
        "category": payload.businessInfo.category,
        "website_type": payload.websiteType,
        "theme": payload.theme,
        "features_count": len(payload.selectedFeatures),
    }

    return ValidateResponseSchema(
        valid=is_valid,
        errors=errors,
        summary=summary,
    )

@router.post("/start", response_model=StartGenerationResponseSchema, status_code=status.HTTP_201_CREATED)
async def start_website_generation(
    body: StartGenerationRequestSchema,
    current_user: dict = Depends(get_current_user),
):
    """
    Initiates a new website generation pipeline job for the authenticated user.
    Executes validation, normalization, AI content, static site build, and ZIP packaging.
    """
    user_id = str(current_user.get("_id") or current_user.get("id", ""))
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized user account")

    try:
        result = await GenerationService.create_generation_job(
            user_id=user_id,
            payload=body.payload,
        )
        return StartGenerationResponseSchema(**result)
    except ValueError as val_err:
        generator_logger.warning(f"Generation start validation error: {str(val_err)}")
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        generator_logger.error(f"Unexpected generation start error: {str(exc)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize generation job: {str(exc)}")

@router.get("/status/{job_id}", response_model=JobStatusResponseSchema)
async def get_generation_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves status lifecycle state and metadata for a specific generation job.
    """
    user_id = str(current_user.get("_id") or current_user.get("id", ""))
    job = await GenerationService.get_job_status(job_id=job_id, user_id=user_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Generation job with ID '{job_id}' not found or access denied",
        )
    return JobStatusResponseSchema(**job)

@router.get("/build-progress/{job_id}")
async def get_build_progress(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Returns granular build progress stage (PREPARING, GENERATING_CONTENT, BUILDING_PAGES, BUILDING_ASSETS, OPTIMIZING, PACKAGING, COMPLETED), percentage (0-100%), and status message for frontend polling.
    """
    user_id = str(current_user.get("_id") or current_user.get("id", ""))
    db = get_db()
    job = await db.generation_jobs.find_one({"_id": job_id})
    if not job or str(job.get("user_id")) != user_id:
        raise HTTPException(status_code=404, detail="Job not found or access denied")

    return {
        "job_id": job["job_id"],
        "status": job.get("status", "PENDING"),
        "progress_percentage": job.get("progress_percentage", 0),
        "progress_message": job.get("progress_message", "Initializing build..."),
        "error_message": job.get("error_message"),
        "updated_at": str(job.get("updated_at")),
    }

@router.get("/preview/{job_id}/{page_name:path}", response_class=HTMLResponse)
async def get_page_preview_html(
    job_id: str,
    page_name: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Renders live HTML preview page for a completed or processing build.
    """
    user_id = str(current_user.get("_id") or current_user.get("id", ""))
    html_content = await PreviewService.get_page_preview(job_id=job_id, page_name=page_name, user_id=user_id)
    if not html_content:
        raise HTTPException(status_code=404, detail="Preview page not found or build not ready")
    return HTMLResponse(content=html_content)

@router.get("/download/{job_id}")
async def download_website_zip(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Streams the completed CompanyName-Website.zip package for authenticated download.
    Prevents download if job is incomplete or failed.
    """
    user_id = str(current_user.get("_id") or current_user.get("id", ""))
    zip_path, zip_filename = await DownloadService.get_download_file(job_id=job_id, user_id=user_id)
    if not zip_path or not zip_filename:
        raise HTTPException(
            status_code=400,
            detail="ZIP download is not available. Ensure the build job is COMPLETED.",
        )
    return FileResponse(
        path=zip_path,
        filename=zip_filename,
        media_type="application/zip",
    )

@router.get("/projects")
async def list_projects(
    search: Optional[str] = Query(None, description="Search term for company/type/theme"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    website_type: Optional[str] = Query(None, description="Filter by website type"),
    theme: Optional[str] = Query(None, description="Filter by visual theme"),
    favorite_only: bool = Query(False, description="Filter by favorite projects"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    """
    Lists paginated user projects with server-side filtering and search.
    """
    user_id = str(current_user.get("_id") or current_user.get("id", ""))
    return await ProjectService.list_user_projects(
        user_id=user_id,
        search=search,
        status=status,
        website_type=website_type,
        theme=theme,
        favorite_only=favorite_only,
        page=page,
        limit=limit,
    )

@router.get("/projects/{job_id}")
async def get_project_details(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves complete project details, business metadata, build logs, and page listings.
    """
    user_id = str(current_user.get("_id") or current_user.get("id", ""))
    project = await ProjectService.get_project_details(job_id=job_id, user_id=user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    return project

@router.patch("/projects/{job_id}/rename")
async def rename_project(
    job_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """
    Renames a user project.
    """
    new_name = body.get("name", "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="New project name is required")
    user_id = str(current_user.get("_id") or current_user.get("id", ""))
    success = await ProjectService.rename_project(job_id=job_id, user_id=user_id, new_name=new_name)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found or update failed")
    return {"message": "Project renamed successfully", "custom_name": new_name}

@router.post("/projects/{job_id}/favorite")
async def toggle_favorite_project(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Toggles favorite star status for a project.
    """
    user_id = str(current_user.get("_id") or current_user.get("id", ""))
    fav_state = await ProjectService.toggle_favorite(job_id=job_id, user_id=user_id)
    if fav_state is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Favorite state updated", "favorite": fav_state}

@router.post("/projects/{job_id}/duplicate")
async def duplicate_project(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Duplicates an existing project into a new build execution.
    """
    user_id = str(current_user.get("_id") or current_user.get("id", ""))
    new_job = await ProjectService.duplicate_project(job_id=job_id, user_id=user_id)
    if not new_job:
        raise HTTPException(status_code=400, detail="Failed to duplicate project configuration")
    return new_job

@router.delete("/projects/{job_id}")
async def delete_project(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Soft-deletes a user project.
    """
    user_id = str(current_user.get("_id") or current_user.get("id", ""))
    success = await ProjectService.soft_delete_project(job_id=job_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found or already deleted")
    return {"message": "Project soft deleted successfully"}

@router.get("/dashboard-stats")
async def get_workspace_dashboard_stats(
    current_user: dict = Depends(get_current_user),
):
    """
    Returns workspace metrics for Total Websites Generated, Total Downloads,
    Active Builds, Failed Builds, Most Used Theme, and Most Used Website Type.
    """
    user_id = str(current_user.get("_id") or current_user.get("id", ""))
    return await ProjectService.get_dashboard_stats(user_id=user_id)

@router.get("/history", response_model=GenerationHistoryResponseSchema)
async def get_generation_history(
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves historical generation logs for the current authenticated user.
    """
    user_id = str(current_user.get("_id") or current_user.get("id", ""))
    history_items = await HistoryService.get_user_history(user_id=user_id)

    items = [GenerationHistoryItemSchema(**item) for item in history_items]
    return GenerationHistoryResponseSchema(
        total=len(items),
        items=items,
    )
