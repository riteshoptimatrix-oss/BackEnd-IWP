from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class HeroContent(BaseModel):
    title: str = Field(..., description="High-converting Hero Section headline")
    subtitle: str = Field(..., description="Engaging Hero Section subheadline")
    cta_text: str = Field("Get Started Now", description="Primary call to action button text")
    cta_link: str = Field("contact.html", description="Primary call to action target URL")
    secondary_cta_text: Optional[str] = Field(None, description="Secondary call to action button text")
    secondary_cta_link: Optional[str] = Field(None, description="Secondary call to action target URL")

class AboutContent(BaseModel):
    overview: str = Field(..., description="Company overview statement")
    story: str = Field(..., description="Company brand narrative or story")
    mission: str = Field(..., description="Company mission statement")
    vision: str = Field(..., description="Company vision for the future")

class ServiceItem(BaseModel):
    title: str = Field(..., description="Service title")
    description: str = Field(..., description="Detailed service description")
    benefits: Optional[List[str]] = Field(default_factory=list, description="Key benefits")

class FAQItem(BaseModel):
    question: str = Field(..., description="Frequently asked question")
    answer: str = Field(..., description="Clear and informative answer")

class SEOContent(BaseModel):
    title: str = Field(..., description="Page SEO title tag")
    description: str = Field(..., description="Meta description tag")
    og_title: str = Field(..., description="Open Graph title")
    og_description: str = Field(..., description="Open Graph social description")
    og_image_alt: str = Field(..., description="Open Graph image alt text")
    twitter_card: str = Field("summary_large_image", description="Twitter card type")
    keywords: List[str] = Field(..., description="Target SEO keywords")

class DynamicSectionItem(BaseModel):
    section_type: str = Field(..., description="Type of section (e.g., pricing, gallery, team, menu, doctors)")
    title: str = Field(..., description="Section title")
    subtitle: Optional[str] = Field(None, description="Section subtitle")
    items: List[Dict[str, Any]] = Field(..., description="List of items for this section (e.g., pricing plans, team members)")

class FooterContent(BaseModel):
    copyright_text: str = Field(..., description="Footer copyright statement")
    slogan: str = Field(..., description="Brand slogan or tag line")

class ContactContent(BaseModel):
    intro_copy: str = Field(..., description="Contact page introductory text")
    response_time_promise: str = Field("We reply within 24 business hours.", description="Response guarantee")

class AIContentPayload(BaseModel):
    hero: HeroContent
    about: AboutContent
    services: List[ServiceItem]
    faq: List[FAQItem]
    dynamic_sections: List[DynamicSectionItem] = Field(default_factory=list, description="Industry-specific dynamic sections")
    seo: SEOContent
    footer: FooterContent
    contact: ContactContent

class GenerateContentRequest(BaseModel):
    payload: Dict[str, Any] = Field(..., description="Phase 2 Website Generator Payload")

class RegenerateContentRequest(BaseModel):
    payload: Dict[str, Any] = Field(..., description="Phase 2 Website Generator Payload")
    section: Optional[str] = Field(None, description="Specific section to regenerate (e.g. hero, about, faq)")
    tone: Optional[str] = Field("professional", description="Target tone: professional, creative, minimal")

class PreviewContentResponse(BaseModel):
    status: str = "success"
    company_name: str
    website_type: str
    theme: str
    ai_content: AIContentPayload
    placeholder_mapping: Dict[str, str]
