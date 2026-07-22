import hashlib
import json
from typing import Dict, Any, Optional
from app.website_generator.ai_content_engine.schemas import (
    AIContentPayload,
    HeroContent,
    AboutContent,
    ServiceItem,
    FAQItem,
    DynamicSectionItem,
    SEOContent,
    FooterContent,
    ContactContent,
)
from app.website_generator.ai_content_engine.sanitizers import ContentSanitizer
from app.website_generator.utils.logger import generator_logger

class AIContentService:
    """
    AI Content Service orchestrating business copy generation, caching,
    and sanitization for placeholder engine injection.
    """
    _cache: Dict[str, AIContentPayload] = {}

    @classmethod
    def _compute_hash(cls, company_name: str, category: str, description: str, features: list) -> str:
        raw = f"{company_name}:{category}:{description}:{','.join(features)}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    @classmethod
    def generate_content(cls, payload_dict: Dict[str, Any], force_regenerate: bool = False) -> AIContentPayload:
        info = payload_dict.get("businessInfo", {})
        company_name = info.get("companyName", "Acme Business")
        category = info.get("category", "Software Company")
        description = info.get("description", "Enterprise software solutions provider.")
        features = payload_dict.get("selectedFeatures", [])

        cache_key = cls._compute_hash(company_name, category, description, features)
        if not force_regenerate and cache_key in cls._cache:
            generator_logger.info(f"Retrieved cached AI content for '{company_name}'")
            return cls._cache[cache_key]

        generator_logger.info(f"Generating AI business copy for '{company_name}' ({category})...")

        hero = HeroContent(
            title=f"Elevating {category.title()} Experiences with {company_name}",
            subtitle=f"We blend innovation, strategy, and design to deliver enterprise-grade {category} solutions that drive measurable growth and unparalleled customer satisfaction. {description[:100]}",
            cta_text="Start Your Journey",
            cta_link="contact.html",
            secondary_cta_text="View Our Portfolio",
            secondary_cta_link="services.html"
        )

        about = AboutContent(
            overview=f"At {company_name}, we are redefining the landscape of the {category} industry with a relentless pursuit of excellence.",
            story=f"Founded on the principles of integrity and innovation, {company_name} began with a singular vision: to empower our clients with state-of-the-art {category} solutions. Over the years, we have scaled our operations and refined our craft to become a trusted industry leader.",
            mission=f"To democratize access to premium {category} services and empower organizations to achieve their highest potential through our bespoke solutions.",
            vision=f"To be the global benchmark for quality, sustainability, and technological innovation in the {category} sector.",
        )

        services = [
            ServiceItem(
                title=f"Premium {category.title()} Consulting",
                description=f"Leverage our decades of industry expertise. We offer bespoke architectural plans, strategic roadmaps, and actionable insights to accelerate your growth.",
                benefits=["Data-driven strategies", "Cost optimization", "Scalable frameworks"],
            ),
            ServiceItem(
                title="Enterprise-Grade Implementation",
                description="Turnkey project delivery executed with precision and technical rigor. We ensure seamless integration with your existing workflows.",
                benefits=["Accelerated time-to-market", "Flawless execution", "24/7 Priority Support"],
            ),
            ServiceItem(
                title="Continuous Optimization & Security",
                description="Hardened infrastructure ensuring 99.99% uptime, lightning-fast performance, and enterprise-level data privacy.",
                benefits=["SOC2 & GDPR Compliant", "Sub-second latency", "Proactive monitoring"],
            ),
        ]

        faq = [
            FAQItem(
                question=f"What differentiates {company_name} from other {category} providers?",
                answer=f"Our commitment to bespoke engineering, award-winning design, and measurable ROI sets {company_name} apart. We don't just deliver services; we partner with you for long-term success.",
            ),
            FAQItem(
                question="What is the typical engagement process?",
                answer="We begin with a comprehensive discovery phase, followed by strategic blueprinting, agile implementation, and continuous post-launch optimization.",
            ),
            FAQItem(
                question="Do you offer dedicated enterprise support?",
                answer=f"Yes, enterprise clients benefit from 24/7 dedicated account managers and priority SLAs during our operating hours: {info.get('workingHours', 'Mon-Sat 9AM-7PM')}.",
            ),
        ]

        dynamic_sections = []
        if "restaurant" in category.lower() or "cafe" in category.lower():
            dynamic_sections.append(
                DynamicSectionItem(
                    section_type="menu",
                    title="Our Signature Menu",
                    subtitle="Culinary masterpieces crafted by our executive chefs using locally sourced, organic ingredients.",
                    items=[
                        {"name": "Truffle Risotto", "description": "Arborio rice, wild mushrooms, black truffle shavings", "price": "$28"},
                        {"name": "Wagyu Ribeye", "description": "A5 Japanese Wagyu, garlic herb butter, roasted asparagus", "price": "$85"},
                        {"name": "Artisan Burrata", "description": "Heirloom tomatoes, basil pesto, balsamic glaze", "price": "$18"}
                    ]
                )
            )
        elif "hospital" in category.lower() or "clinic" in category.lower():
            dynamic_sections.append(
                DynamicSectionItem(
                    section_type="doctors",
                    title="Our Medical Experts",
                    subtitle="Board-certified specialists dedicated to your health and well-being.",
                    items=[
                        {"name": "Dr. Sarah Jenkins", "specialty": "Chief of Cardiology", "description": "15+ years of experience in cardiovascular surgery."},
                        {"name": "Dr. Michael Chen", "specialty": "Neurology", "description": "Pioneering research in neurodegenerative diseases."}
                    ]
                )
            )
        else:
            dynamic_sections.append(
                DynamicSectionItem(
                    section_type="pricing",
                    title="Transparent Enterprise Pricing",
                    subtitle="Flexible plans designed to scale with your business needs.",
                    items=[
                        {"plan_name": "Professional", "price": "$99/mo", "features": ["Core Features", "Standard Support", "Up to 5 Users"]},
                        {"plan_name": "Enterprise", "price": "Custom", "features": ["Dedicated Infrastructure", "24/7 SLA", "Unlimited Users", "Custom Integrations"]}
                    ]
                )
            )

        seo = SEOContent(
            title=f"{company_name} | Premium {category.title()} Solutions",
            description=f"Experience unparalleled {category} services with {company_name}. We deliver enterprise-grade solutions tailored for maximum ROI. {description[:50]}",
            og_title=f"{company_name} - Redefining {category.title()}",
            og_description=f"Join industry leaders who trust {company_name} for innovative, high-performance {category} solutions.",
            og_image_alt=f"{company_name} corporate headquarters",
            twitter_card="summary_large_image",
            keywords=[company_name.lower(), category.lower(), "enterprise solutions", "premium services", "b2b", "industry leaders", "innovation"],
        )

        footer = FooterContent(
            copyright_text=f"© {company_name}. All rights reserved. Designed with precision.",
            slogan=f"Architecting the future of {category}.",
        )

        contact = ContactContent(
            intro_copy=f"Ready to transform your business? Our enterprise consultants at {company_name} are standing by to discuss your custom requirements.",
            response_time_promise="Expect a comprehensive response from our executive team within 4 business hours.",
        )

        content_payload = AIContentPayload(
            hero=hero,
            about=about,
            services=services,
            faq=faq,
            dynamic_sections=dynamic_sections,
            seo=seo,
            footer=footer,
            contact=contact,
        )

        # Sanitize output
        sanitized_dict = ContentSanitizer.sanitize_object(content_payload.dict())
        sanitized_payload = AIContentPayload(**sanitized_dict)

        cls._cache[cache_key] = sanitized_payload
        return sanitized_payload
