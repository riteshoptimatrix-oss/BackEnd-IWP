import os
from typing import List, Tuple
from app.website_generator.utils.logger import generator_logger

class WebsiteValidator:
    """
    Website Validator verifying build output integrity, HTML file presence,
    and asset availability prior to ZIP packaging.
    """
    @staticmethod
    def validate_build(output_dir: str, pages: List[str]) -> Tuple[bool, List[str]]:
        errors = []

        # 1. Check HTML page existence & size
        for fname in pages:
            fpath = os.path.join(output_dir, fname)
            if not os.path.exists(fpath):
                errors.append(f"Required page '{fname}' was not generated.")
            elif os.path.getsize(fpath) == 0:
                errors.append(f"Generated page '{fname}' is empty (0 bytes).")

        # 2. Check assets directory
        assets_dir = os.path.join(output_dir, "assets")
        if not os.path.exists(assets_dir):
            errors.append("Assets directory is missing.")
        else:
            css_file = os.path.join(assets_dir, "css", "main.css")
            if not os.path.exists(css_file):
                errors.append("Main CSS stylesheet 'assets/css/main.css' is missing.")

        # 3. Check SEO files
        for seo_file in ["robots.txt", "sitemap.xml", "manifest.json"]:
            if not os.path.exists(os.path.join(output_dir, seo_file)):
                errors.append(f"SEO file '{seo_file}' is missing.")

        is_valid = len(errors) == 0
        if is_valid:
            generator_logger.info(f"WebsiteValidator successfully validated build output in '{output_dir}'")
        else:
            generator_logger.warning(f"WebsiteValidator found {len(errors)} build errors: {', '.join(errors)}")

        return is_valid, errors
