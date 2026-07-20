import csv
import io
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import UploadFile

from app.database import get_db
from app.schemas.tech_logo_match_admin import (
    AdminDashboardStats,
    AssetResponse,
    BulkImportItem,
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
    TechnologyStatus,
    TechnologyUpdate,
    ValidationIssue,
    ValidationResponse,
    VersionResponse,
)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "tech-logo-match")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_MIME = {"image/svg+xml", "image/png", "image/webp"}


def _id_str(doc) -> str:
    return str(doc["_id"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize(doc):
    doc["id"] = _id_str(doc)
    doc.pop("_id", None)
    return doc


# ── Audit ──

async def _log_action(entity_type: str, entity_id: str, action: str, changes: dict, user_id: Optional[str] = None):
    db = get_db()
    await db.tech_logo_match_versions.insert_one({
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "changes": changes,
        "changed_by": user_id,
        "changed_at": _now(),
        "version": int(_now().timestamp() * 1000),
    })


# ── Technology CRUD ──

async def create_technology(data: TechnologyCreate, user_id: Optional[str] = None) -> TechnologyResponse:
    db = get_db()
    now = _now()
    doc = {
        "official_name": data.official_name,
        "short_name": data.short_name,
        "category": data.category,
        "description": data.description,
        "difficulty": data.difficulty,
        "aliases": data.aliases,
        "official_url": data.official_url,
        "display_order": data.display_order,
        "status": data.status.value,
        "logo_path": None,
        "logo_url": None,
        "logo_mime": None,
        "logo_size": None,
        "created_at": now,
        "updated_at": now,
        "created_by": user_id,
        "version": 1,
    }
    result = await db.tech_logo_match_technologies.insert_one(doc)
    doc["_id"] = result.inserted_id
    await _log_action("technology", _id_str(result.inserted_id), "create", doc, user_id)
    return TechnologyResponse(**_serialize(doc))


async def update_technology(tech_id: str, data: TechnologyUpdate, user_id: Optional[str] = None) -> Optional[TechnologyResponse]:
    db = get_db()
    existing = await db.tech_logo_match_technologies.find_one({"_id": tech_id})
    if not existing:
        return None
    update = {"updated_at": _now()}
    changes = {}
    for field in ["official_name", "short_name", "category", "description", "difficulty",
                   "aliases", "official_url", "display_order"]:
        val = getattr(data, field, None)
        if val is not None:
            old = existing.get(field)
            if old != val:
                update[field] = val
                changes[field] = {"old": old, "new": val}
    if data.status is not None:
        old = existing.get("status")
        if old != data.status.value:
            update["status"] = data.status.value
            changes["status"] = {"old": old, "new": data.status.value}
    update["version"] = existing.get("version", 1) + 1
    await db.tech_logo_match_technologies.update_one({"_id": tech_id}, {"$set": update})
    changes["version"] = {"old": existing.get("version", 1), "new": update["version"]}
    await _log_action("technology", tech_id, "update", changes, user_id)
    updated = await db.tech_logo_match_technologies.find_one({"_id": tech_id})
    return TechnologyResponse(**_serialize(updated))


async def delete_technology(tech_id: str, user_id: Optional[str] = None) -> bool:
    db = get_db()
    doc = await db.tech_logo_match_technologies.find_one({"_id": tech_id})
    if not doc:
        return False
    await db.tech_logo_match_technologies.delete_one({"_id": tech_id})
    await _log_action("technology", tech_id, "delete", {"deleted": doc}, user_id)
    return True


async def archive_technology(tech_id: str, user_id: Optional[str] = None) -> Optional[TechnologyResponse]:
    db = get_db()
    doc = await db.tech_logo_match_technologies.find_one({"_id": tech_id})
    if not doc:
        return None
    old_status = doc.get("status")
    await db.tech_logo_match_technologies.update_one(
        {"_id": tech_id},
        {"$set": {"status": "archived", "updated_at": _now(), "version": doc.get("version", 1) + 1}}
    )
    await _log_action("technology", tech_id, "archive", {"old_status": old_status, "new_status": "archived"}, user_id)
    updated = await db.tech_logo_match_technologies.find_one({"_id": tech_id})
    return TechnologyResponse(**_serialize(updated))


async def restore_technology(tech_id: str, user_id: Optional[str] = None) -> Optional[TechnologyResponse]:
    db = get_db()
    doc = await db.tech_logo_match_technologies.find_one({"_id": tech_id})
    if not doc:
        return None
    old_status = doc.get("status")
    await db.tech_logo_match_technologies.update_one(
        {"_id": tech_id},
        {"$set": {"status": "active", "updated_at": _now(), "version": doc.get("version", 1) + 1}}
    )
    await _log_action("technology", tech_id, "restore", {"old_status": old_status, "new_status": "active"}, user_id)
    updated = await db.tech_logo_match_technologies.find_one({"_id": tech_id})
    return TechnologyResponse(**_serialize(updated))


async def get_technology(tech_id: str) -> Optional[TechnologyResponse]:
    db = get_db()
    doc = await db.tech_logo_match_technologies.find_one({"_id": tech_id})
    return TechnologyResponse(**_serialize(doc)) if doc else None


async def list_technologies(
    page: int = 1,
    limit: int = 20,
    search: str = "",
    category: str = "",
    difficulty: str = "",
    status: str = "",
    sort_by: str = "display_order",
    sort_order: int = 1,
) -> TechnologyListResponse:
    db = get_db()
    query = {}
    if search:
        query["$or"] = [
            {"official_name": {"$regex": search, "$options": "i"}},
            {"short_name": {"$regex": search, "$options": "i"}},
            {"aliases": {"$regex": search, "$options": "i"}},
        ]
    if category:
        query["category"] = category
    if difficulty:
        query["difficulty"] = difficulty
    if status:
        query["status"] = status
    total = await db.tech_logo_match_technologies.count_documents(query)
    cursor = db.tech_logo_match_technologies.find(query).sort(sort_by, sort_order)
    docs = await cursor.skip((page - 1) * limit).limit(limit).to_list(length=limit)
    return TechnologyListResponse(
        technologies=[TechnologyResponse(**_serialize(d)) for d in docs],
        total=total,
        page=page,
        limit=limit,
        has_more=(page * limit) < total,
    )


# ── Category CRUD ──

async def create_category(data: CategoryCreate) -> CategoryResponse:
    db = get_db()
    now = _now()
    doc = {
        "name": data.name,
        "description": data.description,
        "icon": data.icon,
        "display_order": data.display_order,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.tech_logo_match_categories.insert_one(doc)
    doc["_id"] = result.inserted_id
    await _log_action("category", _id_str(result.inserted_id), "create", doc)
    return CategoryResponse(**_serialize(doc))


async def update_category(cat_id: str, data: CategoryUpdate) -> Optional[CategoryResponse]:
    db = get_db()
    existing = await db.tech_logo_match_categories.find_one({"_id": cat_id})
    if not existing:
        return None
    update = {"updated_at": _now()}
    changes = {}
    for field in ["name", "description", "icon", "display_order"]:
        val = getattr(data, field, None)
        if val is not None:
            old = existing.get(field)
            if old != val:
                update[field] = val
                changes[field] = {"old": old, "new": val}
    if changes:
        await db.tech_logo_match_categories.update_one({"_id": cat_id}, {"$set": update})
        await _log_action("category", cat_id, "update", changes)
    return await get_category(cat_id)


async def delete_category(cat_id: str) -> bool:
    db = get_db()
    doc = await db.tech_logo_match_categories.find_one({"_id": cat_id})
    if not doc:
        return False
    await db.tech_logo_match_categories.delete_one({"_id": cat_id})
    await _log_action("category", cat_id, "delete", {"deleted": doc})
    return True


async def get_category(cat_id: str) -> Optional[CategoryResponse]:
    db = get_db()
    doc = await db.tech_logo_match_categories.find_one({"_id": cat_id})
    if not doc:
        return None
    count = await db.tech_logo_match_technologies.count_documents({"category": doc["name"], "status": "active"})
    resp = CategoryResponse(**_serialize(doc))
    resp.technology_count = count
    return resp


async def list_categories(search: str = "") -> list[CategoryResponse]:
    db = get_db()
    query = {}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    docs = await db.tech_logo_match_categories.find(query).sort("display_order", 1).to_list(length=100)
    result = []
    for d in docs:
        count = await db.tech_logo_match_technologies.count_documents({"category": d["name"], "status": "active"})
        resp = CategoryResponse(**_serialize(d))
        resp.technology_count = count
        result.append(resp)
    return result


# ── Pack CRUD ──

async def create_pack(data: PackCreate) -> PackResponse:
    db = get_db()
    now = _now()
    doc = {
        "name": data.name,
        "description": data.description,
        "technologies": data.technologies,
        "difficulty": data.difficulty,
        "estimated_minutes": data.estimated_minutes,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.tech_logo_match_packs.insert_one(doc)
    doc["_id"] = result.inserted_id
    await _log_action("pack", _id_str(result.inserted_id), "create", doc)
    return PackResponse(**_serialize(doc))


async def update_pack(pack_id: str, data: PackUpdate) -> Optional[PackResponse]:
    db = get_db()
    existing = await db.tech_logo_match_packs.find_one({"_id": pack_id})
    if not existing:
        return None
    update = {"updated_at": _now()}
    for field in ["name", "description", "technologies", "difficulty", "estimated_minutes"]:
        val = getattr(data, field, None)
        if val is not None:
            update[field] = val
    await db.tech_logo_match_packs.update_one({"_id": pack_id}, {"$set": update})
    await _log_action("pack", pack_id, "update", update)
    return await get_pack(pack_id)


async def delete_pack(pack_id: str) -> bool:
    db = get_db()
    doc = await db.tech_logo_match_packs.find_one({"_id": pack_id})
    if not doc:
        return False
    await db.tech_logo_match_packs.delete_one({"_id": pack_id})
    await _log_action("pack", pack_id, "delete", {"deleted": doc})
    return True


async def get_pack(pack_id: str) -> Optional[PackResponse]:
    db = get_db()
    doc = await db.tech_logo_match_packs.find_one({"_id": pack_id})
    if not doc:
        return None
    resp = PackResponse(**_serialize(doc))
    resp.technology_count = len(doc.get("technologies", []))
    return resp


async def list_packs(search: str = "") -> list[PackResponse]:
    db = get_db()
    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]
    docs = await db.tech_logo_match_packs.find(query).sort("name", 1).to_list(length=100)
    result = []
    for d in docs:
        resp = PackResponse(**_serialize(d))
        resp.technology_count = len(d.get("technologies", []))
        result.append(resp)
    return result


# ── Question CRUD ──

async def create_question(data: QuestionCreate, user_id: Optional[str] = None) -> QuestionResponse:
    db = get_db()
    now = _now()
    tech_name = ""
    if data.technology_id:
        tech = await db.tech_logo_match_technologies.find_one({"_id": data.technology_id})
        if tech:
            tech_name = tech.get("official_name", "")
    doc = {
        "technology_id": data.technology_id,
        "technology_name": tech_name,
        "question_type": data.question_type.value,
        "prompt": data.prompt,
        "correct_answer": data.correct_answer,
        "options": data.options,
        "difficulty": data.difficulty,
        "category": data.category,
        "tags": data.tags,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.tech_logo_match_questions.insert_one(doc)
    doc["_id"] = result.inserted_id
    await _log_action("question", _id_str(result.inserted_id), "create", doc, user_id)
    return QuestionResponse(**_serialize(doc))


async def update_question(q_id: str, data: QuestionUpdate, user_id: Optional[str] = None) -> Optional[QuestionResponse]:
    db = get_db()
    existing = await db.tech_logo_match_questions.find_one({"_id": q_id})
    if not existing:
        return None
    update = {"updated_at": _now()}
    for field in ["technology_id", "question_type", "prompt", "correct_answer", "options", "difficulty", "category", "tags"]:
        val = getattr(data, field, None)
        if val is not None:
            update[field] = val.value if field == "question_type" and hasattr(val, "value") else val
    if "technology_id" in update:
        tech = await db.tech_logo_match_technologies.find_one({"_id": update["technology_id"]})
        update["technology_name"] = tech.get("official_name", "") if tech else ""
    await db.tech_logo_match_questions.update_one({"_id": q_id}, {"$set": update})
    await _log_action("question", q_id, "update", update, user_id)
    updated = await db.tech_logo_match_questions.find_one({"_id": q_id})
    return QuestionResponse(**_serialize(updated)) if updated else None


async def delete_question(q_id: str) -> bool:
    db = get_db()
    doc = await db.tech_logo_match_questions.find_one({"_id": q_id})
    if not doc:
        return False
    await db.tech_logo_match_questions.delete_one({"_id": q_id})
    await _log_action("question", q_id, "delete", {"deleted": doc})
    return True


async def get_question(q_id: str) -> Optional[QuestionResponse]:
    db = get_db()
    doc = await db.tech_logo_match_questions.find_one({"_id": q_id})
    return QuestionResponse(**_serialize(doc)) if doc else None


async def list_questions(
    page: int = 1,
    limit: int = 20,
    search: str = "",
    question_type: str = "",
    difficulty: str = "",
    category: str = "",
    technology_id: str = "",
    sort_by: str = "created_at",
    sort_order: int = -1,
) -> QuestionListResponse:
    db = get_db()
    query = {}
    if search:
        query["$or"] = [
            {"prompt": {"$regex": search, "$options": "i"}},
            {"correct_answer": {"$regex": search, "$options": "i"}},
            {"technology_name": {"$regex": search, "$options": "i"}},
        ]
    if question_type:
        query["question_type"] = question_type
    if difficulty:
        query["difficulty"] = difficulty
    if category:
        query["category"] = category
    if technology_id:
        query["technology_id"] = technology_id
    total = await db.tech_logo_match_questions.count_documents(query)
    cursor = db.tech_logo_match_questions.find(query).sort(sort_by, sort_order)
    docs = await cursor.skip((page - 1) * limit).limit(limit).to_list(length=limit)
    return QuestionListResponse(
        questions=[QuestionResponse(**_serialize(d)) for d in docs],
        total=total,
        page=page,
        limit=limit,
        has_more=(page * limit) < total,
    )


# ── Asset Management ──

async def upload_asset(
    file: UploadFile,
    technology_id: Optional[str] = None,
    is_alternative: bool = False,
    label: str = "",
    user_id: Optional[str] = None,
) -> Optional[AssetResponse]:
    if file.content_type not in ALLOWED_MIME:
        return None
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "png"
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(content)
    url = f"/uploads/tech-logo-match/{unique_name}"
    now = _now()
    doc = {
        "filename": unique_name,
        "original_name": file.filename,
        "mime_type": file.content_type,
        "size_bytes": len(content),
        "width": None,
        "height": None,
        "url": url,
        "path": file_path,
        "version": 1,
        "technology_id": technology_id,
        "is_alternative": is_alternative,
        "label": label,
        "created_at": now,
        "created_by": user_id,
    }
    db = get_db()
    result = await db.tech_logo_match_assets.insert_one(doc)
    doc["_id"] = result.inserted_id
    if technology_id:
        await db.tech_logo_match_technologies.update_one(
            {"_id": technology_id},
            {"$set": {"logo_path": url, "logo_url": url, "logo_mime": file.content_type, "logo_size": len(content)}}
        )
    await _log_action("asset", _id_str(result.inserted_id), "upload", {"filename": unique_name}, user_id)
    return AssetResponse(**_serialize(doc))


async def replace_asset(asset_id: str, file: UploadFile, user_id: Optional[str] = None) -> Optional[AssetResponse]:
    db = get_db()
    existing = await db.tech_logo_match_assets.find_one({"_id": asset_id})
    if not existing:
        return None
    if file.content_type not in ALLOWED_MIME:
        return None
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "png"
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(content)

    old_path = existing.get("path")
    if old_path and os.path.exists(old_path):
        try:
            os.remove(old_path)
        except OSError:
            pass

    url = f"/uploads/tech-logo-match/{unique_name}"
    new_version = existing.get("version", 1) + 1
    await db.tech_logo_match_assets.update_one(
        {"_id": asset_id},
        {"$set": {
            "filename": unique_name,
            "original_name": file.filename,
            "mime_type": file.content_type,
            "size_bytes": len(content),
            "url": url,
            "path": file_path,
            "version": new_version,
        }}
    )
    tech_id = existing.get("technology_id")
    if tech_id:
        await db.tech_logo_match_technologies.update_one(
            {"_id": tech_id},
            {"$set": {"logo_path": url, "logo_url": url, "logo_mime": file.content_type, "logo_size": len(content)}}
        )
    await _log_action("asset", asset_id, "replace", {"old_file": existing["filename"], "new_file": unique_name}, user_id)
    updated = await db.tech_logo_match_assets.find_one({"_id": asset_id})
    return AssetResponse(**_serialize(updated)) if updated else None


async def delete_asset(asset_id: str) -> bool:
    db = get_db()
    doc = await db.tech_logo_match_assets.find_one({"_id": asset_id})
    if not doc:
        return False
    file_path = doc.get("path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
    await db.tech_logo_match_assets.delete_one({"_id": asset_id})
    await _log_action("asset", asset_id, "delete", {"deleted": doc})
    return True


async def list_assets(page: int = 1, limit: int = 20, technology_id: str = "") -> list[AssetResponse]:
    db = get_db()
    query = {}
    if technology_id:
        query["technology_id"] = technology_id
    docs = await db.tech_logo_match_assets.find(query).sort("created_at", -1).skip((page - 1) * limit).limit(limit).to_list(length=limit)
    return [AssetResponse(**_serialize(d)) for d in docs]


async def get_asset(asset_id: str) -> Optional[AssetResponse]:
    db = get_db()
    doc = await db.tech_logo_match_assets.find_one({"_id": asset_id})
    return AssetResponse(**_serialize(doc)) if doc else None


# ── Version History ──

async def get_version_history(entity_type: str = "", entity_id: str = "", page: int = 1, limit: int = 20) -> list[VersionResponse]:
    db = get_db()
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    docs = await db.tech_logo_match_versions.find(query).sort("changed_at", -1).skip((page - 1) * limit).limit(limit).to_list(length=limit)
    return [VersionResponse(**_serialize(d)) for d in docs]


# ── Bulk Import ──

async def bulk_import_technologies(items: list[dict], user_id: Optional[str] = None) -> BulkImportResponse:
    result_items = []
    for i, item in enumerate(items):
        try:
            data = TechnologyCreate(**item)
            await create_technology(data, user_id)
            result_items.append(BulkImportItem(row=i + 1, status="success", message="Imported", data=item))
        except Exception as e:
            result_items.append(BulkImportItem(row=i + 1, status="error", message=str(e), data=item))
    succeeded = sum(1 for r in result_items if r.status == "success")
    return BulkImportResponse(total=len(items), succeeded=succeeded, failed=len(items) - succeeded, items=result_items)


async def bulk_import_questions(items: list[dict], user_id: Optional[str] = None) -> BulkImportResponse:
    result_items = []
    for i, item in enumerate(items):
        try:
            data = QuestionCreate(**item)
            await create_question(data, user_id)
            result_items.append(BulkImportItem(row=i + 1, status="success", message="Imported", data=item))
        except Exception as e:
            result_items.append(BulkImportItem(row=i + 1, status="error", message=str(e), data=item))
    succeeded = sum(1 for r in result_items if r.status == "success")
    return BulkImportResponse(total=len(items), succeeded=succeeded, failed=len(items) - succeeded, items=result_items)


# ── Export ──

async def export_technologies(format_type: ExportFormat) -> tuple[str, str, str]:
    db = get_db()
    docs = await db.tech_logo_match_technologies.find({"status": "active"}).sort("display_order", 1).to_list(length=500)
    data = [{k: v for k, v in _serialize(d).items() if k not in ("id", "created_at", "updated_at", "created_by", "version", "logo_path", "logo_url", "logo_mime", "logo_size")} for d in docs]
    if format_type == ExportFormat.json:
        content = json.dumps(data, indent=2, default=str)
        return content, "technologies.json", "application/json"
    elif format_type == ExportFormat.csv:
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)
        content = output.getvalue()
        return content, "technologies.csv", "text/csv"
    return "", "", ""


async def export_questions(format_type: ExportFormat) -> tuple[str, str, str]:
    db = get_db()
    docs = await db.tech_logo_match_questions.find({}).sort("created_at", -1).to_list(length=500)
    data = [{k: v for k, v in _serialize(d).items() if k not in ("id", "created_at", "updated_at")} for d in docs]
    if format_type == ExportFormat.json:
        content = json.dumps(data, indent=2, default=str)
        return content, "questions.json", "application/json"
    elif format_type == ExportFormat.csv:
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)
        content = output.getvalue()
        return content, "questions.csv", "text/csv"
    return "", "", ""


# ── Validation ──

async def run_validation() -> ValidationResponse:
    db = get_db()
    issues: list[ValidationIssue] = []

    technologies = await db.tech_logo_match_technologies.find({}).to_list(length=500)
    tech_names = set()
    tech_by_name = {}
    for t in technologies:
        name = t.get("official_name", "")
        tech_names.add(name)
        tech_by_name[t.get("short_name", "")] = _id_str(t)
        for a in t.get("aliases", []):
            tech_by_name[a] = _id_str(t)

    for t in technologies:
        tid = _id_str(t)
        name = t.get("official_name", "")
        if not t.get("logo_path"):
            issues.append(ValidationIssue(type="missing_logo", severity="warning", entity_type="technology", entity_id=tid, entity_name=name, message=f"Technology '{name}' has no logo uploaded"))
        if not t.get("description"):
            issues.append(ValidationIssue(type="missing_description", severity="info", entity_type="technology", entity_id=tid, entity_name=name, message=f"Technology '{name}' has no description"))

    name_counts = {}
    for t in technologies:
        n = t.get("official_name", "").lower()
        name_counts[n] = name_counts.get(n, 0) + 1
    for n, c in name_counts.items():
        if c > 1:
            issues.append(ValidationIssue(type="duplicate_technology", severity="error", entity_type="technology", message=f"Duplicate technology name: '{n}' found {c} times"))

    categories = await db.tech_logo_match_categories.find({}).to_list(length=100)
    cat_names = {c["name"] for c in categories}
    for t in technologies:
        cat = t.get("category", "")
        if cat and cat not in cat_names:
            issues.append(ValidationIssue(type="broken_category_reference", severity="warning", entity_type="technology", entity_id=_id_str(t), entity_name=t.get("official_name", ""), message=f"Technology '{t.get('official_name', '')}' references missing category '{cat}'"))

    questions = await db.tech_logo_match_questions.find({}).to_list(length=500)
    for q in questions:
        tech_id = q.get("technology_id", "")
        if tech_id:
            tech = await db.tech_logo_match_technologies.find_one({"_id": tech_id})
            if not tech:
                issues.append(ValidationIssue(type="broken_question_reference", severity="error", entity_type="question", entity_id=_id_str(q), message=f"Question references non-existent technology ID '{tech_id}'"))

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    return ValidationResponse(
        total_issues=len(issues),
        errors=len(errors),
        warnings=len(warnings),
        issues=issues,
        passed=len(errors) == 0,
    )


# ── Dashboard ──

async def get_admin_dashboard_stats() -> AdminDashboardStats:
    db = get_db()
    total_tech = await db.tech_logo_match_technologies.count_documents({})
    active_tech = await db.tech_logo_match_technologies.count_documents({"status": "active"})
    archived_tech = await db.tech_logo_match_technologies.count_documents({"status": "archived"})
    total_cats = await db.tech_logo_match_categories.count_documents({})
    total_packs = await db.tech_logo_match_packs.count_documents({})
    total_questions = await db.tech_logo_match_questions.count_documents({})
    total_assets = await db.tech_logo_match_assets.count_documents({})
    no_logo = await db.tech_logo_match_technologies.count_documents({"$or": [{"logo_path": None}, {"logo_path": ""}]})
    diff_counts = await db.tech_logo_match_technologies.aggregate([
        {"$group": {"_id": "$difficulty", "count": {"$sum": 1}}}
    ]).to_list(length=20)
    cat_counts = await db.tech_logo_match_technologies.aggregate([
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]).to_list(length=50)
    total_size = 0
    async for a in db.tech_logo_match_assets.find({}, {"size_bytes": 1}):
        total_size += a.get("size_bytes", 0)
    recent_versions = await db.tech_logo_match_versions.find({}).sort("changed_at", -1).limit(10).to_list(length=10)
    return AdminDashboardStats(
        total_technologies=total_tech,
        active_technologies=active_tech,
        archived_technologies=archived_tech,
        total_categories=total_cats,
        total_packs=total_packs,
        total_questions=total_questions,
        total_assets=total_assets,
        assets_size_bytes=total_size,
        technologies_without_logo=no_logo,
        technologies_by_difficulty={d["_id"] or "unknown": d["count"] for d in diff_counts},
        technologies_by_category={c["_id"] or "unknown": c["count"] for c in cat_counts},
        recent_activity=[VersionResponse(**_serialize(v)) for v in recent_versions],
    )
