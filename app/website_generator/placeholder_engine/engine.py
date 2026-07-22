from typing import Dict, Any
from app.website_generator.schemas.payload import WebsiteGeneratorPayload

class PlaceholderEngine:
    """
    Generates normalized JSON/AST structure metadata placeholders
    preparing for Phase 4 template rendering without producing raw HTML.
    """
    @staticmethod
    def generate_placeholder_payload(payload: WebsiteGeneratorPayload) -> Dict[str, Any]:
        info = payload.businessInfo
        return {
            "meta": {
                "title": f"{info.companyName} | Official Website",
                "description": info.description,
                "category": info.category,
                "target_framework": "nextjs_15_app_router",
                "ui_library": "tailwind_v4_framer_motion",
            },
            "theme_tokens": {
                "theme_preset": payload.theme,
                "primary_color": "oklch(0.546 0.245 262)",
                "background": "oklch(1 0 0)",
            },
            "layout_tree": {
                "header": {
                    "show_logo": bool(info.logoUrl),
                    "nav_items": ["Home", "About", "Services", "Contact"],
                },
                "sections": [
                    {"type": "hero", "headline": f"Welcome to {info.companyName}", "subheadline": info.description},
                    {"type": "features", "items": payload.selectedFeatures},
                    {"type": "contact", "phone": info.phone, "email": info.email, "address": info.fullAddress},
                ],
                "footer": {
                    "company_name": info.companyName,
                    "working_hours": info.workingHours,
                    "social_links": info.socialLinks.dict() if info.socialLinks else {},
                },
            },
        }
