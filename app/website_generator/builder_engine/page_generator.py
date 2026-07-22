import os
from typing import Dict, List, Any
from app.website_generator.schemas.payload import WebsiteGeneratorPayload
from app.website_generator.template_engine.template_registry import TemplateRegistry
from app.website_generator.template_engine.placeholder_service import PlaceholderService
from app.website_generator.utils.logger import generator_logger

class PageGenerator:
    """
    Production Static Page Generator assembling all category-specific and feature-conditional pages.
    """
    @classmethod
    def generate_all_pages(cls, output_dir: str, payload: WebsiteGeneratorPayload) -> List[str]:
        # Priority 1: Category selection from businessInfo, Priority 2: websiteType
        category_key = payload.businessInfo.category or payload.websiteType
        template_dir = TemplateRegistry.get_template_dir(category_key)
        context = PlaceholderService.generate_context(payload)
        info = payload.businessInfo

        # Category-driven pages structure
        pages_to_build = list(TemplateRegistry.get_category_pages(category_key))

        # Feature conditional pages
        feats = payload.selectedFeatures
        if "Gallery" in feats and "gallery.html" not in pages_to_build:
            pages_to_build.append("gallery.html")
        if "Blog" in feats and "blog.html" not in pages_to_build:
            pages_to_build.append("blog.html")
        if "Pricing" in feats and "pricing.html" not in pages_to_build:
            pages_to_build.append("pricing.html")
        if "Careers" in feats and "careers.html" not in pages_to_build:
            pages_to_build.append("careers.html")

        # Legal & Utility pages
        for legal_page in ["privacy.html", "terms.html", "404.html"]:
            if legal_page not in pages_to_build:
                pages_to_build.append(legal_page)

        generated_files = []

        for fname in pages_to_build:
            template_file = os.path.join(template_dir, fname)
            if not os.path.exists(template_file):
                # Fallback template content generator for extra pages
                raw_html = cls._generate_fallback_page_html(fname, info.companyName, payload.theme)
            else:
                with open(template_file, "r", encoding="utf-8") as f:
                    raw_html = f.read()

            rendered_html = PlaceholderService.render_content(raw_html, context)
            out_file = os.path.join(output_dir, fname)
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(rendered_html)

            generated_files.append(fname)
            generator_logger.info(f"PageGenerator built '{fname}' from template '{template_dir}' successfully")

        return generated_files

    @staticmethod
    def _generate_fallback_page_html(fname: str, company_name: str, theme: str) -> str:
        page_title = fname.replace(".html", "").replace("_", " ").capitalize()
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{page_title} - {{company_name}}</title>
  <link rel="stylesheet" href="assets/css/main.css">
</head>
<body class="{{theme_class}}">
  <header>
    <div class="logo">{{logo_html}} <span>{{company_name}}</span></div>
    <nav>
      <ul>
        <li><a href="index.html">Home</a></li>
        <li><a href="about.html">About</a></li>
        <li><a href="services.html">Services</a></li>
        <li><a href="contact.html">Contact</a></li>
        <li><a href="faq.html">FAQ</a></li>
      </ul>
    </nav>
  </header>
  <main class="container">
    <h1>{page_title}</h1>
    <div class="card" style="margin-top: 1.5rem;">
      <p>Welcome to {page_title} page for {{company_name}}. All business details and content are fully configured.</p>
    </div>
  </main>
  <footer>
    <p>&copy; {{year}} {{company_name}}. All rights reserved.</p>
  </footer>
  <script src="assets/js/main.js"></script>
</body>
</html>"""
