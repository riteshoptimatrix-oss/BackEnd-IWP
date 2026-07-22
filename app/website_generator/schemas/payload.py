from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

class SocialLinksSchema(BaseModel):
    facebook: Optional[str] = Field(None, description="Facebook profile URL")
    instagram: Optional[str] = Field(None, description="Instagram profile URL")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    twitter: Optional[str] = Field(None, description="Twitter/X profile URL")
    youtube: Optional[str] = Field(None, description="YouTube channel URL")

class BusinessInfoSchema(BaseModel):
    companyName: str = Field(..., min_length=2, max_length=120, description="Company or business name")
    logoUrl: Optional[str] = Field(None, description="Uploaded company logo data URL or link")
    category: str = Field(..., description="Primary business industry category")
    description: str = Field(..., min_length=10, max_length=500, description="Business description")
    phone: str = Field(..., min_length=7, max_length=20, description="Primary contact phone number")
    altPhone: Optional[str] = Field(None, description="Alternative phone number")
    whatsapp: Optional[str] = Field(None, description="WhatsApp contact number")
    email: EmailStr = Field(..., description="Valid company email address")
    existingWebsite: Optional[str] = Field(None, description="Existing website URL")
    country: str = Field("India", description="Country name")
    state: str = Field(..., description="State or province")
    city: str = Field(..., description="City or district")
    pincode: str = Field(..., description="Postal pincode")
    fullAddress: str = Field(..., description="Street or office address")
    googleMapsUrl: Optional[str] = Field(None, description="Google Maps location link")
    workingHours: str = Field("Mon - Sat: 9:00 AM - 7:00 PM", description="Operating business hours")
    socialLinks: Optional[SocialLinksSchema] = Field(default_factory=SocialLinksSchema)

class WebsiteGeneratorPayload(BaseModel):
    businessInfo: BusinessInfoSchema
    websiteType: str = Field(..., description="Selected website type e.g. Software Company, E-Commerce")
    theme: str = Field(..., description="Selected visual theme preset e.g. White, Dark, Blue White")
    selectedFeatures: List[str] = Field(..., min_items=1, description="List of enabled features")

class ValidateResponseSchema(BaseModel):
    valid: bool
    errors: Dict[str, str] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)

class StartGenerationRequestSchema(BaseModel):
    payload: WebsiteGeneratorPayload

class StartGenerationResponseSchema(BaseModel):
    job_id: str
    status: str
    message: str
    company_name: str
    estimated_duration_seconds: int = 5
    created_at: str

class JobStatusResponseSchema(BaseModel):
    job_id: str
    user_id: str
    company_name: str
    website_type: str
    theme: str
    status: str  # PENDING | VALIDATING | READY | PROCESSING | COMPLETED | FAILED
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    placeholder_meta: Optional[Dict[str, Any]] = None

class GenerationHistoryItemSchema(BaseModel):
    id: str
    job_id: str
    company_name: str
    website_type: str
    theme: str
    selected_features: List[str]
    status: str
    created_at: str

class GenerationHistoryResponseSchema(BaseModel):
    total: int
    items: List[GenerationHistoryItemSchema]
