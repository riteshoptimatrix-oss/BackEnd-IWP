from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional, List
from app.middleware.admin_auth import get_admin_user, get_write_admin, get_super_admin
from app.schemas.admin import (
    UserListRequest, UserActionRequest, UserRoleRequest,
    SnippetCreateRequest, SnippetUpdateRequest, SnippetBulkImportRequest,
    CategoryCreateRequest, CategoryUpdateRequest,
    ChallengeCreateRequest, ChallengeArchiveRequest,
    CertificateCreateRequest, CertificateRevokeRequest,
    LeaderboardRefreshRequest, SuspiciousActivityRequest,
    ReportGenerateRequest, BroadcastNotificationRequest,
    SettingsUpdateRequest, AuditLogQuery, GlobalSearchRequest,
    AdminResponse,
)
from app.services.admin_service import admin_service

router = APIRouter(prefix="/admin", tags=["Admin Panel"])


def _ok(data=None, message="Success"):
    return AdminResponse(success=True, message=message, data=data)


# ─── Admin Login ───────────────────────────────────────────────────

@router.post("/login")
async def admin_login(request: Request):
    body = await request.json()
    email = body.get("email", "")
    password = body.get("password", "")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    try:
        result = await admin_service.admin_login(email, password)
        return _ok(result, "Admin login successful")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ─── Dashboard ─────────────────────────────────────────────────────

@router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_admin_user)):
    stats = await admin_service.get_dashboard_stats()
    return _ok(stats, "Dashboard stats loaded")


# ─── User Management ───────────────────────────────────────────────

@router.get("/users")
async def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: dict = Depends(get_admin_user),
):
    result = await admin_service.get_users(
        page=page, limit=limit, search=search,
        role=role, status=status, sort_by=sort_by, sort_order=sort_order,
    )
    return _ok(result)


@router.get("/users/{user_id}")
async def get_user(user_id: str, current_user: dict = Depends(get_admin_user)):
    user = await admin_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _ok(user)


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: UserRoleRequest,
    current_user: dict = Depends(get_super_admin),
):
    result = await admin_service.update_user_role(user_id, body.role, current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return _ok(message="Role updated")


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    body: UserActionRequest,
    current_user: dict = Depends(get_write_admin),
):
    result = await admin_service.suspend_user(user_id, body.reason or "", current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return _ok(message="User suspended")


@router.post("/users/{user_id}/reactivate")
async def reactivate_user(
    user_id: str,
    current_user: dict = Depends(get_write_admin),
):
    result = await admin_service.reactivate_user(user_id, current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return _ok(message="User reactivated")


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_super_admin),
):
    result = await admin_service.delete_user(user_id, current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return _ok(message="User deleted")


@router.post("/users/{user_id}/reset-stats")
async def reset_user_stats(
    user_id: str,
    current_user: dict = Depends(get_write_admin),
):
    await admin_service.reset_user_stats(user_id, current_user["_id"])
    return _ok(message="User stats reset")


# ─── Snippet Management ────────────────────────────────────────────

@router.get("/snippets")
async def get_snippets(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    language: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_admin_user),
):
    result = await admin_service.get_snippets(
        page=page, limit=limit, language=language,
        difficulty=difficulty, search=search,
    )
    return _ok(result)


@router.post("/snippets", status_code=201)
async def create_snippet(
    body: SnippetCreateRequest,
    current_user: dict = Depends(get_write_admin),
):
    snippet_id = await admin_service.create_snippet(body.model_dump(), current_user["_id"])
    return _ok({"id": snippet_id}, "Snippet created")


@router.put("/snippets/{snippet_id}")
async def update_snippet(
    snippet_id: str,
    body: SnippetUpdateRequest,
    current_user: dict = Depends(get_write_admin),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    result = await admin_service.update_snippet(snippet_id, data, current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return _ok(message="Snippet updated")


@router.delete("/snippets/{snippet_id}")
async def delete_snippet(
    snippet_id: str,
    current_user: dict = Depends(get_write_admin),
):
    result = await admin_service.delete_snippet(snippet_id, current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return _ok(message="Snippet deleted")


@router.post("/snippets/{snippet_id}/duplicate")
async def duplicate_snippet(
    snippet_id: str,
    current_user: dict = Depends(get_write_admin),
):
    new_id = await admin_service.duplicate_snippet(snippet_id, current_user["_id"])
    if not new_id:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return _ok({"id": new_id}, "Snippet duplicated")


@router.post("/snippets/bulk-import")
async def bulk_import_snippets(
    body: SnippetBulkImportRequest,
    current_user: dict = Depends(get_write_admin),
):
    snippets = [s.model_dump() for s in body.snippets]
    if body.language:
        for s in snippets:
            s["language"] = body.language
    count = await admin_service.bulk_import_snippets(snippets, current_user["_id"])
    return _ok({"count": count}, f"{count} snippets imported")


@router.get("/snippets/export")
async def export_snippets(
    language: Optional[str] = Query(None),
    current_user: dict = Depends(get_admin_user),
):
    result = await admin_service.get_snippets(limit=10000, language=language)
    return _ok(result.get("snippets", []))


# ─── Category Management ───────────────────────────────────────────

@router.get("/categories")
async def get_categories(
    language: Optional[str] = Query(None),
    current_user: dict = Depends(get_admin_user),
):
    cats = await admin_service.get_categories(language)
    return _ok(cats)


@router.post("/categories", status_code=201)
async def create_category(
    body: CategoryCreateRequest,
    current_user: dict = Depends(get_write_admin),
):
    cat_id = await admin_service.create_category(body.model_dump(), current_user["_id"])
    return _ok({"id": cat_id}, "Category created")


@router.put("/categories/{cat_id}")
async def update_category(
    cat_id: str,
    body: CategoryUpdateRequest,
    current_user: dict = Depends(get_write_admin),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    result = await admin_service.update_category(cat_id, data, current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="Category not found")
    return _ok(message="Category updated")


@router.delete("/categories/{cat_id}")
async def delete_category(
    cat_id: str,
    current_user: dict = Depends(get_write_admin),
):
    result = await admin_service.delete_category(cat_id, current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="Category not found")
    return _ok(message="Category deleted")


# ─── Challenge Management ──────────────────────────────────────────

@router.get("/challenges")
async def get_challenges(
    type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_admin_user),
):
    if type == "weekly":
        result = await admin_service.get_weekly_challenges(page=page, limit=limit)
    else:
        result = await admin_service.get_challenges(challenge_type=type, page=page, limit=limit)
    return _ok(result)


@router.post("/challenges", status_code=201)
async def create_challenge(
    body: ChallengeCreateRequest,
    current_user: dict = Depends(get_write_admin),
):
    challenge_id = await admin_service.create_challenge(body.model_dump(), current_user["_id"])
    return _ok({"id": challenge_id}, "Challenge created")


@router.post("/challenges/{challenge_id}/archive")
async def archive_challenge(
    challenge_id: str,
    current_user: dict = Depends(get_write_admin),
):
    result = await admin_service.archive_challenge(challenge_id, current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return _ok(message="Challenge archived")


@router.delete("/challenges/{challenge_id}")
async def delete_challenge(
    challenge_id: str,
    current_user: dict = Depends(get_write_admin),
):
    result = await admin_service.delete_challenge(challenge_id, current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return _ok(message="Challenge deleted")


# ─── Certificate Management ────────────────────────────────────────

@router.get("/certificates")
async def get_certificates(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_admin_user),
):
    result = await admin_service.get_certificates(page=page, limit=limit, user_id=user_id)
    return _ok(result)


@router.post("/certificates", status_code=201)
async def create_certificate(
    body: CertificateCreateRequest,
    current_user: dict = Depends(get_write_admin),
):
    cert_id = await admin_service.create_certificate(body.model_dump(), current_user["_id"])
    return _ok({"id": cert_id}, "Certificate issued")


@router.post("/certificates/{cert_id}/revoke")
async def revoke_certificate(
    cert_id: str,
    body: CertificateRevokeRequest,
    current_user: dict = Depends(get_write_admin),
):
    result = await admin_service.revoke_certificate(cert_id, body.reason, current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return _ok(message="Certificate revoked")


@router.get("/certificates/verify/{code}")
async def verify_certificate(code: str):
    cert = await admin_service.verify_certificate(code)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return _ok(cert)


@router.get("/certificate-templates")
async def get_certificate_templates(current_user: dict = Depends(get_admin_user)):
    templates = await admin_service.get_certificate_templates()
    return _ok(templates)


@router.post("/certificate-templates", status_code=201)
async def create_certificate_template(
    request: Request,
    current_user: dict = Depends(get_write_admin),
):
    body = await request.json()
    tmpl_id = await admin_service.create_certificate_template(body, current_user["_id"])
    return _ok({"id": tmpl_id}, "Template created")


@router.put("/certificate-templates/{tmpl_id}")
async def update_certificate_template(
    tmpl_id: str,
    request: Request,
    current_user: dict = Depends(get_write_admin),
):
    body = await request.json()
    result = await admin_service.update_certificate_template(tmpl_id, body, current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return _ok(message="Template updated")


@router.delete("/certificate-templates/{tmpl_id}")
async def delete_certificate_template(
    tmpl_id: str,
    current_user: dict = Depends(get_write_admin),
):
    result = await admin_service.delete_certificate_template(tmpl_id, current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return _ok(message="Template deleted")


# ─── Leaderboard Management ────────────────────────────────────────

@router.get("/leaderboard")
async def get_leaderboard(
    metric: str = Query("xp"),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_admin_user),
):
    from app.repositories.admin_repository import AdminRepository
    repo = AdminRepository()
    data = await repo.get_leaderboard(metric, limit)
    return _ok(data)


@router.post("/leaderboard/refresh")
async def refresh_leaderboard(
    body: LeaderboardRefreshRequest,
    current_user: dict = Depends(get_write_admin),
):
    result = await admin_service.refresh_leaderboard(body.metrics, current_user["_id"])
    return _ok(result, "Leaderboard refreshed")


@router.post("/leaderboard/remove-invalid")
async def remove_invalid_scores(current_user: dict = Depends(get_super_admin)):
    count = await admin_service.remove_invalid_scores(current_user["_id"])
    return _ok({"removed": count}, f"{count} invalid scores removed")


@router.post("/leaderboard/suspicious")
async def detect_suspicious(
    body: SuspiciousActivityRequest = SuspiciousActivityRequest(),
):
    result = await admin_service.detect_suspicious_activity(body.threshold)
    return _ok(result)


# ─── Reports ───────────────────────────────────────────────────────

@router.post("/reports/generate")
async def generate_report(
    body: ReportGenerateRequest,
    current_user: dict = Depends(get_admin_user),
):
    try:
        days = 30
        if body.start_date and body.end_date:
            from datetime import datetime
            d1 = datetime.fromisoformat(body.start_date)
            d2 = datetime.fromisoformat(body.end_date)
            days = (d2 - d1).days or 30
        report = await admin_service.generate_report(body.report_type, days)
        return _ok(report)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Audit Log ─────────────────────────────────────────────────────

@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_admin_user),
):
    result = await admin_service.get_audit_logs(
        page=page, limit=limit, admin_id=admin_id,
        action=action, resource_type=resource_type,
        start_date=start_date, end_date=end_date,
    )
    return _ok(result)


# ─── Notifications ─────────────────────────────────────────────────

@router.post("/notifications/broadcast")
async def broadcast_notification(
    body: BroadcastNotificationRequest,
    current_user: dict = Depends(get_write_admin),
):
    notif_id = await admin_service.broadcast_notification(body.model_dump(), current_user["_id"])
    return _ok({"id": notif_id}, "Notification broadcast")


@router.get("/notifications")
async def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_admin_user),
):
    result = await admin_service.get_notifications(page=page, limit=limit)
    return _ok(result)


@router.delete("/notifications/{notif_id}")
async def delete_notification(
    notif_id: str,
    current_user: dict = Depends(get_write_admin),
):
    result = await admin_service.delete_notification(notif_id, current_user["_id"])
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")
    return _ok(message="Notification deleted")


# ─── Settings ──────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(
    category: Optional[str] = Query(None),
    current_user: dict = Depends(get_admin_user),
):
    settings = await admin_service.get_settings(category)
    return _ok(settings)


@router.put("/settings")
async def update_settings(
    body: SettingsUpdateRequest,
    current_user: dict = Depends(get_super_admin),
):
    result = await admin_service.update_setting(
        body.key, body.value, body.category, current_user["_id"]
    )
    return _ok(message="Setting updated")


# ─── Global Search ─────────────────────────────────────────────────

@router.post("/search")
async def global_search(
    body: GlobalSearchRequest,
    current_user: dict = Depends(get_admin_user),
):
    result = await admin_service.global_search(body.query, body.types, body.page, body.limit)
    return _ok(result)
