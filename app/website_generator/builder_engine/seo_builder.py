import os
import json
from typing import Any
from app.website_generator.schemas.payload import WebsiteGeneratorPayload
from app.website_generator.ai_content_engine.service import AIContentService
from app.website_generator.utils.logger import generator_logger

class SEOBuilder:
    """
    SEO Builder generating meta tags, OpenGraph tags, Twitter cards,
    JSON-LD structured data, robots.txt, sitemap.xml, and manifest.json.
    """
    @classmethod
    def build_seo_assets(cls, output_dir: str, payload: WebsiteGeneratorPayload, pages: list) -> None:
        info = payload.businessInfo
        domain_name = info.companyName.lower().replace(" ", "")
        base_url = f"https://{domain_name}.com"

        # AI Copy for SEO
        ai_content = AIContentService.generate_content(payload.dict())

        # 1. robots.txt
        robots_content = f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n"
        with open(os.path.join(output_dir, "robots.txt"), "w", encoding="utf-8") as f:
            f.write(robots_content)

        # 2. sitemap.xml
        urls_xml = "".join([
            f"  <url><loc>{base_url}/{p}</loc><priority>0.8</priority></url>\n"
            for p in pages
        ])
        sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls_xml}</urlset>"""
        with open(os.path.join(output_dir, "sitemap.xml"), "w", encoding="utf-8") as f:
            f.write(sitemap_content)

        # 3. manifest.json
        manifest = {
            "name": info.companyName,
            "short_name": info.companyName[:12],
            "description": ai_content.seo.description,
            "start_url": "/index.html",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#2563eb",
            "icons": [
                {"src": "assets/images/logo.png", "sizes": "192x192", "type": "image/png"}
            ]
        }
        with open(os.path.join(output_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 4. Inject SEO meta tags, OpenGraph, Twitter, and JSON-LD schema into HTML files
        cls._inject_seo_head_tags(output_dir, pages, info, ai_content, base_url)
        generator_logger.info("SEOBuilder completed SEO meta tags and manifest files generation.")

    @staticmethod
    def _inject_seo_head_tags(output_dir: str, pages: list, info: Any, ai_content: Any, base_url: str) -> None:
        for page_name in pages:
            file_path = os.path.join(output_dir, page_name)
            if not os.path.exists(file_path):
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            canonical_url = f"{base_url}/{page_name}"
            json_ld_schema = json.dumps({
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": info.companyName,
                "url": base_url,
                "description": info.description,
                "telephone": info.phone,
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": info.fullAddress,
                    "addressLocality": info.city,
                    "addressRegion": info.state,
                    "postalCode": info.pincode,
                    "addressCountry": info.country,
                }
            }, indent=2)

            head_injection = f"""
  <!-- OpenGraph Tags -->
  <meta property="og:title" content="{ai_content.seo.og_title}">
  <meta property="og:description" content="{ai_content.seo.og_description}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:image:alt" content="{getattr(ai_content.seo, 'og_image_alt', info.companyName)}">

  <!-- Twitter Card Tags -->
  <meta name="twitter:card" content="{getattr(ai_content.seo, 'twitter_card', 'summary_large_image')}">
  <meta name="twitter:title" content="{ai_content.seo.og_title}">
  <meta name="twitter:description" content="{ai_content.seo.description}">

  <!-- SEO Keywords -->
  <meta name="keywords" content="{', '.join(ai_content.seo.keywords)}">

  <!-- Canonical URL -->
  <link rel="canonical" href="{canonical_url}">

  <!-- JSON-LD Structured Data -->
  <script type="application/ld+json">
  {json_ld_schema}
  </script>
</head>"""

            if "</head>" in html_content:
                updated_html = html_content.replace("</head>", head_injection)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated_html)
