from fastapi import APIRouter, Depends, HTTPException, status
from app.middleware.auth import get_current_user
from app.website_generator.ai_content_engine.schemas import (
    GenerateContentRequest,
    RegenerateContentRequest,
    PreviewContentResponse,
    AIContentPayload,
)
from app.website_generator.ai_content_engine.service import AIContentService
from app.website_generator.utils.logger import generator_logger

router = APIRouter(prefix="/website-generator/ai-content", tags=["AI Content Engine"])

@router.post("/generate", response_model=AIContentPayload)
async def generate_ai_content(
    body: GenerateContentRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generates structured AI copy (Hero, About, Services, FAQ, SEO, Footer)
    for a Phase 2 wizard input payload.
    """
    try:
        content = AIContentService.generate_content(body.payload, force_regenerate=False)
        return content
    except Exception as exc:
        generator_logger.error(f"AI content generation error: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI content",
        )

@router.post("/regenerate", response_model=AIContentPayload)
async def regenerate_ai_content(
    body: RegenerateContentRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Force regenerates structured AI copy for specific sections or overall site.
    """
    try:
        content = AIContentService.generate_content(body.payload, force_regenerate=True)
        return content
    except Exception as exc:
        generator_logger.error(f"AI content regeneration error: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate AI content",
        )

@router.post("/preview", response_model=PreviewContentResponse)
async def preview_ai_content(
    body: GenerateContentRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Returns structured AI content preview along with key-value placeholder mappings.
    """
    payload = body.payload
    info = payload.get("businessInfo", {})
    company_name = info.get("companyName", "Business")
    website_type = payload.get("websiteType", "Business")
    theme = payload.get("theme", "White")

    content = AIContentService.generate_content(payload)

    mapping = {
        "{{company_name}}": company_name,
        "{{hero_title}}": content.hero.title,
        "{{hero_subtitle}}": content.hero.subtitle,
        "{{business_description}}": content.about.overview,
        "{{seo_title}}": content.seo.title,
        "{{seo_description}}": content.seo.description,
    }

    return PreviewContentResponse(
        company_name=company_name,
        website_type=website_type,
        theme=theme,
        ai_content=content,
        placeholder_mapping=mapping,
    )
