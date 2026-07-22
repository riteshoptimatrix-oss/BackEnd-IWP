import re
from typing import Dict, Any, Tuple
from app.website_generator.schemas.payload import WebsiteGeneratorPayload

VALID_WEBSITE_TYPES = {
    "Corporate Business", "Restaurant & Dining", "Hotel & Resort", "Gym & Fitness Club",
    "Hospital & Medical Center", "Specialist Clinic", "Law Firm & Legal Practice",
    "Real Estate & Property", "School & Academy", "Coaching & Test Prep",
    "Software & SaaS Company", "Digital Marketing Agency", "E-Commerce Store",
    "Personal Portfolio", "High-Converting Landing Page", "Beauty Salon & Spa",
    "Wellness Spa & Retreat", "Artisanal Cafe & Coffee Shop", "Artisan Bakery & Cake Shop",
    "Travel & Tour Agency", "Construction & Engineering", "Interior Design Studio",
    "Architecture Firm", "Financial Services & Advisory", "Insurance Agency",
    "NGO & Non-Profit Foundation", "Industrial Manufacturing", "Electronics & Gadgets",
    "Modern Furniture Store", "Blog & Content Publication", "News & Media Portal",
    # Legacy options just in case
    "Business", "Informative", "E-Commerce", "Portfolio", "Landing Page",
    "Blog", "News", "Forum", "Directory", "Entertainment", "Education",
    "Restaurant", "Hotel", "Healthcare", "Gym", "Salon", "Law Firm",
    "Real Estate", "Travel", "Software Company", "Digital Agency"
}

VALID_THEMES = {
    "White", "Dark", "Blue White", "Corporate", "Startup",
    "Minimal", "Luxury", "Glass", "Gradient"
}

VALID_FEATURES = {
    "Contact Form", "Gallery", "Testimonials", "FAQ", "Newsletter",
    "Blog", "Team Section", "Services", "Pricing", "Careers",
    "WhatsApp Button", "Call Button", "Google Maps", "SEO Ready",
    "Analytics Ready", "Accessibility", "Animations", "Dark Mode Toggle"
}

URL_REGEX = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
PHONE_REGEX = re.compile(r"^[\d\s+\-()]{7,20}$")

class PayloadValidator:
    @staticmethod
    def validate(payload: WebsiteGeneratorPayload) -> Tuple[bool, Dict[str, str]]:
        errors: Dict[str, str] = {}
        info = payload.businessInfo

        # 1. Company Name
        if not info.companyName or len(info.companyName.strip()) < 2:
            errors["companyName"] = "Company name must be at least 2 characters"

        # 2. Business Category
        if not info.category or not info.category.strip():
            errors["category"] = "Business category is required"

        # 3. Description
        if not info.description or len(info.description.strip()) < 10:
            errors["description"] = "Description must be at least 10 characters"

        # 4. Phone
        if not info.phone or not PHONE_REGEX.match(info.phone.strip()):
            errors["phone"] = "Invalid primary phone number format"

        if info.altPhone and not PHONE_REGEX.match(info.altPhone.strip()):
            errors["altPhone"] = "Invalid alternative phone number format"

        if info.whatsapp and not PHONE_REGEX.match(info.whatsapp.strip()):
            errors["whatsapp"] = "Invalid WhatsApp number format"

        # 5. Email (Pydantic already checks basic email syntax, additional sanity check)
        if not info.email or "@" not in info.email:
            errors["email"] = "Invalid email address format"

        # 6. URLs
        if info.existingWebsite and not URL_REGEX.match(info.existingWebsite.strip()):
            errors["existingWebsite"] = "Website URL must begin with http:// or https://"

        if info.googleMapsUrl and not URL_REGEX.match(info.googleMapsUrl.strip()):
            errors["googleMapsUrl"] = "Google Maps URL must begin with http:// or https://"

        if info.socialLinks:
            soc = info.socialLinks
            if soc.facebook and not URL_REGEX.match(soc.facebook.strip()):
                errors["facebook"] = "Invalid Facebook URL"
            if soc.instagram and not URL_REGEX.match(soc.instagram.strip()):
                errors["instagram"] = "Invalid Instagram URL"
            if soc.linkedin and not URL_REGEX.match(soc.linkedin.strip()):
                errors["linkedin"] = "Invalid LinkedIn URL"
            if soc.twitter and not URL_REGEX.match(soc.twitter.strip()):
                errors["twitter"] = "Invalid Twitter/X URL"
            if soc.youtube and not URL_REGEX.match(soc.youtube.strip()):
                errors["youtube"] = "Invalid YouTube URL"

        # 7. Address
        if not info.country.strip():
            errors["country"] = "Country is required"
        if not info.state.strip():
            errors["state"] = "State is required"
        if not info.city.strip():
            errors["city"] = "City is required"
        if not info.pincode.strip():
            errors["pincode"] = "Pincode is required"
        if not info.fullAddress.strip():
            errors["fullAddress"] = "Full address is required"

        # 8. Website Type validation
        if payload.websiteType not in VALID_WEBSITE_TYPES:
            errors["websiteType"] = f"Invalid website type: '{payload.websiteType}'"

        # 9. Theme validation
        if payload.theme not in VALID_THEMES:
            errors["theme"] = f"Invalid theme selection: '{payload.theme}'"

        # 10. Selected Features validation
        if not payload.selectedFeatures:
            errors["selectedFeatures"] = "At least one feature must be selected"
        else:
            invalid_feats = [f for f in payload.selectedFeatures if f not in VALID_FEATURES]
            if invalid_feats:
                errors["selectedFeatures"] = f"Invalid features selected: {', '.join(invalid_feats)}"

        is_valid = len(errors) == 0
        return is_valid, errors
