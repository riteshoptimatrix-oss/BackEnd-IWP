import os
import json
from typing import Dict
from app.website_generator.schemas.payload import WebsiteGeneratorPayload
from app.website_generator.template_engine.template_registry import TemplateRegistry
from app.website_generator.template_engine.placeholder_service import PlaceholderService

class PageBuilder:
    """
    Static Page Builder rendering HTML pages and manifest files.
    """
    @staticmethod
    def build_pages(output_dir: str, payload: WebsiteGeneratorPayload) -> Dict[str, str]:
        template_dir = TemplateRegistry.get_template_dir(payload.websiteType)
        context = PlaceholderService.generate_context(payload)

        created_files = {}

        # 1. Render HTML files
        # Dynamically determine pages from CATEGORY_PAGES_MAP
        pages_to_render = TemplateRegistry.CATEGORY_PAGES_MAP.get(payload.websiteType, ["index.html", "about.html", "services.html", "contact.html", "faq.html"])
        
        for fname in pages_to_render:
            template_path = os.path.join(template_dir, fname)
            if not os.path.exists(template_path):
                # Fallback to business template if file missing
                template_path = os.path.join(TemplateRegistry.get_template_dir("business"), fname)

            with open(template_path, "r", encoding="utf-8") as f:
                raw_html = f.read()

            rendered_html = PlaceholderService.render_content(raw_html, context)
            out_file = os.path.join(output_dir, fname)
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(rendered_html)
            created_files[fname] = out_file

        # 2. Generate robots.txt
        robots_content = (
            "User-agent: *\n"
            "Allow: /\n"
            f"Sitemap: https://{payload.businessInfo.companyName.lower().replace(' ', '')}.com/sitemap.xml\n"
        )
        robots_path = os.path.join(output_dir, "robots.txt")
        with open(robots_path, "w", encoding="utf-8") as f:
            f.write(robots_content)
        created_files["robots.txt"] = robots_path

        # 3. Generate sitemap.xml
        domain = f"https://{payload.businessInfo.companyName.lower().replace(' ', '')}.com"
        sitemap_urls = ""
        for idx, fname in enumerate(pages_to_render):
            priority = "1.0" if fname == "index.html" else "0.8"
            sitemap_urls += f"  <url><loc>{domain}/{fname}</loc><priority>{priority}</priority></url>\n"
            
        sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{sitemap_urls.rstrip()}
</urlset>"""
        sitemap_path = os.path.join(output_dir, "sitemap.xml")
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write(sitemap_content)
        created_files["sitemap.xml"] = sitemap_path

        # 4. Generate manifest.json
        manifest_data = {
            "name": payload.businessInfo.companyName,
            "short_name": payload.businessInfo.companyName[:12],
            "description": payload.businessInfo.description,
            "start_url": "/index.html",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#2563eb",
            "icons": [
                {
                    "src": "assets/images/logo.png",
                    "sizes": "192x192",
                    "type": "image/png"
                }
            ]
        }
        manifest_path = os.path.join(output_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
        created_files["manifest.json"] = manifest_path

        # 5. Generate schema.json (Organization Schema)
        schema_data = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": payload.businessInfo.companyName,
            "description": payload.businessInfo.description,
            "url": domain,
            "logo": f"{domain}/assets/images/logo.png"
        }
        schema_path = os.path.join(output_dir, "schema.json")
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema_data, f, indent=2)
        created_files["schema.json"] = schema_path

        return created_files
