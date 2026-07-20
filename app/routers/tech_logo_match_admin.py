from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from app.database import get_db
from app.middleware.admin_auth import get_admin_user, get_write_admin
from app.schemas.tech_logo_match_admin import (
    AdminDashboardStats,
    AssetResponse,
    BulkImportResponse,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    ExportFormat,
    PackCreate,
    PackResponse,
    PackUpdate,
    QuestionCreate,
    QuestionListResponse,
    QuestionResponse,
    QuestionUpdate,
    TechnologyCreate,
    TechnologyListResponse,
    TechnologyResponse,
    TechnologyUpdate,
    ValidationResponse,
    VersionResponse,
)
from app.services import tech_logo_match_admin_service as svc

router = APIRouter(prefix="/api/v1/tech-logo-match/admin", tags=["tech-logo-match-admin"])


def _admin_or_viewer(current_user: dict = Depends(get_admin_user)):
    return current_user


def _admin_or_writer(current_user: dict = Depends(get_write_admin)):
    return current_user


# ── Dashboard ──

@router.get("/dashboard", response_model=AdminDashboardStats)
async def get_dashboard(_: dict = Depends(_admin_or_viewer)):
    return await svc.get_admin_dashboard_stats()


# ── Technologies ──

@router.get("/technologies", response_model=TechnologyListResponse)
async def list_technologies(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    category: str = Query(""),
    difficulty: str = Query(""),
    status: str = Query(""),
    sort_by: str = Query("display_order"),
    sort_order: int = Query(1),
    _: dict = Depends(_admin_or_viewer),
):
    return await svc.list_technologies(page, limit, search, category, difficulty, status, sort_by, sort_order)


@router.get("/technologies/{tech_id}", response_model=TechnologyResponse)
async def get_technology(tech_id: str, _: dict = Depends(_admin_or_viewer)):
    result = await svc.get_technology(tech_id)
    if not result:
        raise HTTPException(status_code=404, detail="Technology not found")
    return result


@router.post("/technologies", response_model=TechnologyResponse, status_code=201)
async def create_technology(data: TechnologyCreate, current_user: dict = Depends(_admin_or_writer)):
    return await svc.create_technology(data, str(current_user.get("_id", "")))


@router.put("/technologies/{tech_id}", response_model=TechnologyResponse)
async def update_technology(tech_id: str, data: TechnologyUpdate, current_user: dict = Depends(_admin_or_writer)):
    result = await svc.update_technology(tech_id, data, str(current_user.get("_id", "")))
    if not result:
        raise HTTPException(status_code=404, detail="Technology not found")
    return result


@router.delete("/technologies/{tech_id}")
async def delete_technology(tech_id: str, current_user: dict = Depends(_admin_or_writer)):
    result = await svc.delete_technology(tech_id, str(current_user.get("_id", "")))
    if not result:
        raise HTTPException(status_code=404, detail="Technology not found")
    return {"message": "Technology deleted"}


@router.post("/technologies/{tech_id}/archive", response_model=TechnologyResponse)
async def archive_technology(tech_id: str, current_user: dict = Depends(_admin_or_writer)):
    result = await svc.archive_technology(tech_id, str(current_user.get("_id", "")))
    if not result:
        raise HTTPException(status_code=404, detail="Technology not found")
    return result


@router.post("/technologies/{tech_id}/restore", response_model=TechnologyResponse)
async def restore_technology(tech_id: str, current_user: dict = Depends(_admin_or_writer)):
    result = await svc.restore_technology(tech_id, str(current_user.get("_id", "")))
    if not result:
        raise HTTPException(status_code=404, detail="Technology not found")
    return result


# ── Categories ──

@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(search: str = Query(""), _: dict = Depends(_admin_or_viewer)):
    return await svc.list_categories(search)


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(data: CategoryCreate, current_user: dict = Depends(_admin_or_writer)):
    return await svc.create_category(data)


@router.put("/categories/{cat_id}", response_model=CategoryResponse)
async def update_category(cat_id: str, data: CategoryUpdate, _: dict = Depends(_admin_or_writer)):
    result = await svc.update_category(cat_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Category not found")
    return result


@router.delete("/categories/{cat_id}")
async def delete_category(cat_id: str, _: dict = Depends(_admin_or_writer)):
    result = await svc.delete_category(cat_id)
    if not result:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted"}


# ── Packs ──

@router.get("/packs", response_model=list[PackResponse])
async def list_packs(search: str = Query(""), _: dict = Depends(_admin_or_viewer)):
    return await svc.list_packs(search)


@router.post("/packs", response_model=PackResponse, status_code=201)
async def create_pack(data: PackCreate, current_user: dict = Depends(_admin_or_writer)):
    return await svc.create_pack(data)


@router.put("/packs/{pack_id}", response_model=PackResponse)
async def update_pack(pack_id: str, data: PackUpdate, _: dict = Depends(_admin_or_writer)):
    result = await svc.update_pack(pack_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Pack not found")
    return result


@router.delete("/packs/{pack_id}")
async def delete_pack(pack_id: str, _: dict = Depends(_admin_or_writer)):
    result = await svc.delete_pack(pack_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pack not found")
    return {"message": "Pack deleted"}


# ── Questions ──

@router.get("/questions", response_model=QuestionListResponse)
async def list_questions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    question_type: str = Query(""),
    difficulty: str = Query(""),
    category: str = Query(""),
    technology_id: str = Query(""),
    sort_by: str = Query("created_at"),
    sort_order: int = Query(-1),
    _: dict = Depends(_admin_or_viewer),
):
    return await svc.list_questions(page, limit, search, question_type, difficulty, category, technology_id, sort_by, sort_order)


@router.get("/questions/{q_id}", response_model=QuestionResponse)
async def get_question(q_id: str, _: dict = Depends(_admin_or_viewer)):
    result = await svc.get_question(q_id)
    if not result:
        raise HTTPException(status_code=404, detail="Question not found")
    return result


@router.post("/questions", response_model=QuestionResponse, status_code=201)
async def create_question(data: QuestionCreate, current_user: dict = Depends(_admin_or_writer)):
    return await svc.create_question(data, str(current_user.get("_id", "")))


@router.put("/questions/{q_id}", response_model=QuestionResponse)
async def update_question(q_id: str, data: QuestionUpdate, current_user: dict = Depends(_admin_or_writer)):
    result = await svc.update_question(q_id, data, str(current_user.get("_id", "")))
    if not result:
        raise HTTPException(status_code=404, detail="Question not found")
    return result


@router.delete("/questions/{q_id}")
async def delete_question(q_id: str, _: dict = Depends(_admin_or_writer)):
    result = await svc.delete_question(q_id)
    if not result:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"message": "Question deleted"}


# ── Assets ──

@router.get("/assets", response_model=list[AssetResponse])
async def list_assets(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    technology_id: str = Query(""),
    _: dict = Depends(_admin_or_viewer),
):
    return await svc.list_assets(page, limit, technology_id)


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: str, _: dict = Depends(_admin_or_viewer)):
    result = await svc.get_asset(asset_id)
    if not result:
        raise HTTPException(status_code=404, detail="Asset not found")
    return result


@router.post("/assets", response_model=AssetResponse, status_code=201)
async def upload_asset(
    file: UploadFile = File(...),
    technology_id: str = Form(""),
    is_alternative: bool = Form(False),
    label: str = Form(""),
    current_user: dict = Depends(_admin_or_writer),
):
    result = await svc.upload_asset(
        file,
        technology_id or None,
        is_alternative,
        label,
        str(current_user.get("_id", "")),
    )
    if not result:
        raise HTTPException(status_code=400, detail="Invalid file. Only SVG, PNG, WebP under 5MB allowed.")
    return result


@router.put("/assets/{asset_id}/replace", response_model=AssetResponse)
async def replace_asset(
    asset_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(_admin_or_writer),
):
    result = await svc.replace_asset(asset_id, file, str(current_user.get("_id", "")))
    if not result:
        raise HTTPException(status_code=400, detail="Invalid file or asset not found")
    return result


@router.delete("/assets/{asset_id}")
async def delete_asset(asset_id: str, _: dict = Depends(_admin_or_writer)):
    result = await svc.delete_asset(asset_id)
    if not result:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted"}


# ── Bulk Import ──

@router.post("/bulk/technologies", response_model=BulkImportResponse)
async def bulk_import_technologies(data: list[dict], current_user: dict = Depends(_admin_or_writer)):
    return await svc.bulk_import_technologies(data, str(current_user.get("_id", "")))


@router.post("/bulk/questions", response_model=BulkImportResponse)
async def bulk_import_questions(data: list[dict], current_user: dict = Depends(_admin_or_writer)):
    return await svc.bulk_import_questions(data, str(current_user.get("_id", "")))


# ── Export ──

@router.get("/export/technologies")
async def export_technologies(format: ExportFormat = ExportFormat.json, _: dict = Depends(_admin_or_viewer)):
    content, filename, media_type = await svc.export_technologies(format)
    return StreamingResponse(iter([content]), media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/export/questions")
async def export_questions(format: ExportFormat = ExportFormat.json, _: dict = Depends(_admin_or_viewer)):
    content, filename, media_type = await svc.export_questions(format)
    return StreamingResponse(iter([content]), media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})


# ── Validation ──

@router.post("/validate", response_model=ValidationResponse)
async def run_validation(_: dict = Depends(_admin_or_writer)):
    return await svc.run_validation()


# ── Version History ──

@router.get("/versions", response_model=list[VersionResponse])
async def get_versions(
    entity_type: str = Query(""),
    entity_id: str = Query(""),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: dict = Depends(_admin_or_viewer),
):
    return await svc.get_version_history(entity_type, entity_id, page, limit)


# ── Game Content Endpoints ──

@router.get("/content/technologies")
async def get_game_technologies():
    db = get_db()
    docs = await db.tech_logo_match_technologies.find(
        {"status": "active"},
        {"official_name": 1, "short_name": 1, "category": 1, "description": 1, "difficulty": 1,
         "aliases": 1, "logo_url": 1, "logo_mime": 1, "display_order": 1},
    ).sort("display_order", 1).to_list(length=200)
    return [{**d, "id": str(d.pop("_id"))} for d in docs]


@router.get("/content/categories")
async def get_game_categories():
    db = get_db()
    docs = await db.tech_logo_match_categories.find({}).sort("display_order", 1).to_list(length=50)
    return [{**d, "id": str(d.pop("_id"))} for d in docs]


@router.get("/content/questions")
async def get_game_questions(
    category: str = Query(""),
    difficulty: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
):
    db = get_db()
    query = {}
    if category:
        query["category"] = category
    if difficulty:
        query["difficulty"] = difficulty
    docs = await db.tech_logo_match_questions.aggregate([
        {"$match": query},
        {"$sample": {"size": limit}},
    ]).to_list(length=limit)
    return [{**d, "id": str(d.pop("_id"))} for d in docs]


@router.get("/content/packs")
async def get_game_packs():
    db = get_db()
    docs = await db.tech_logo_match_packs.find({}).sort("name", 1).to_list(length=50)
    return [{**d, "id": str(d.pop("_id"))} for d in docs]
