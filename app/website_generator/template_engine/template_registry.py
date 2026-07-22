import os
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_REPO_DIR = os.path.join(BASE_DIR, "templates_repo")

# Scalable Category Factory mapping business categories and website types to dedicated design systems
CATEGORY_TEMPLATE_MAP: Dict[str, str] = {
    # Food & Hospitality
    "restaurant & cafe": "restaurant",
    "restaurant": "restaurant",
    "cafe": "restaurant",
    "bakery": "restaurant",
    "coffee shop": "restaurant",
    "food": "restaurant",
    
    # Fitness & Health
    "fitness & gym": "gym",
    "gym": "gym",
    "fitness": "gym",
    "yoga": "gym",
    "sports": "gym",
    
    # Healthcare & Medical
    "healthcare & clinic": "hospital",
    "hospital": "hospital",
    "clinic": "hospital",
    "doctor": "hospital",
    "dentist": "hospital",
    "pharmacy": "hospital",
    "medical": "hospital",
    
    # Legal & Professional Services
    "law firm & legal": "lawyer",
    "lawyer": "lawyer",
    "legal": "lawyer",
    "chartered accountant": "lawyer",
    "consultancy": "lawyer",
    
    # Real Estate & Construction
    "real estate & construction": "real_estate",
    "real estate": "real_estate",
    "construction": "real_estate",
    "interior": "real_estate",
    "architect": "real_estate",
    "property": "real_estate",
    
    # Technology & SaaS
    "software company": "software_company",
    "digital agency": "software_company",
    "tech": "software_company",
    "saas": "software_company",
    "it": "software_company",
    
    # Luxury Hotel & Hospitality
    "hotel & hospitality": "hotel",
    "hotel": "hotel",
    "resort": "hotel",
    "travel & tourism": "hotel",
    
    # Beauty, Salon & Wellness
    "salon & spa": "salon",
    "salon": "salon",
    "spa": "salon",
    "beauty": "salon",
    "boutique": "salon",
    
    # E-Commerce & Retail
    "e-commerce & retail": "ecommerce",
    "ecommerce": "ecommerce",
    "e-commerce": "ecommerce",
    "e-commerce store": "ecommerce",
    "digital marketing agency": "software_company",
    "jewellery": "ecommerce",
    "fashion": "ecommerce",
    "electronics": "ecommerce",
    
    # Portfolio & Creative
    "portfolio & professional": "portfolio",
    "portfolio": "portfolio",
    "photography": "portfolio",
    "event": "portfolio",
    
    # Landing Page & Marketing
    "landing page": "landing_page",
    "landing_page": "landing_page",
    
    # Informative & Media
    "education & coaching": "informative",
    "blog": "informative",
    "news": "informative",
    "ngo": "informative",
}

# Category specific default pages
CATEGORY_PAGES_MAP: Dict[str, List[str]] = {
    "restaurant": ["index.html", "about.html", "services.html", "contact.html", "faq.html", "menu.html", "reservations.html"],
    "gym": ["index.html", "about.html", "services.html", "contact.html", "faq.html", "workouts.html", "trainers.html"],
    "hospital": ["index.html", "about.html", "services.html", "contact.html", "faq.html", "doctors.html", "appointment.html"],
    "lawyer": ["index.html", "about.html", "services.html", "contact.html", "faq.html", "practice_areas.html", "consultation.html"],
    "real_estate": ["index.html", "about.html", "services.html", "contact.html", "faq.html", "properties.html", "tour.html"],
    "software_company": ["index.html", "about.html", "services.html", "contact.html", "faq.html", "solutions.html", "case_studies.html"],
    "hotel": ["index.html", "about.html", "services.html", "contact.html", "faq.html", "rooms.html", "dining.html"],
    "salon": ["index.html", "about.html", "services.html", "contact.html", "faq.html", "services_menu.html", "book_appointment.html"],
    "ecommerce": ["index.html", "about.html", "services.html", "contact.html", "faq.html"],
    "portfolio": ["index.html", "about.html", "services.html", "contact.html", "faq.html"],
    "landing_page": ["index.html", "about.html", "services.html", "contact.html", "faq.html"],
    "informative": ["index.html", "about.html", "services.html", "contact.html", "faq.html"],
    "business": ["index.html", "about.html", "services.html", "contact.html", "faq.html"],
}

class TemplateRegistry:
    """
    Scalable Template Registry / Factory Pattern.
    Dynamically maps business category input to dedicated design system repositories.
    """
    @classmethod
    def resolve_template_key(cls, category_or_type: str) -> str:
        if not category_or_type:
            return "business"
        key = category_or_type.lower().strip()
        return CATEGORY_TEMPLATE_MAP.get(key, "business")

    @classmethod
    def get_template_dir(cls, category_or_type: str) -> str:
        resolved_key = cls.resolve_template_key(category_or_type)
        target_path = os.path.abspath(os.path.join(TEMPLATES_REPO_DIR, resolved_key))

        # Security check: Prevent Path Traversal
        if not target_path.startswith(os.path.abspath(TEMPLATES_REPO_DIR)):
            raise ValueError(f"Path traversal detected for template: '{category_or_type}'")

        if not os.path.exists(target_path):
            target_path = os.path.join(TEMPLATES_REPO_DIR, "business")

        return target_path

    @classmethod
    def get_category_pages(cls, category_or_type: str) -> List[str]:
        resolved_key = cls.resolve_template_key(category_or_type)
        return CATEGORY_PAGES_MAP.get(resolved_key, ["index.html", "about.html", "services.html", "contact.html", "faq.html"])
