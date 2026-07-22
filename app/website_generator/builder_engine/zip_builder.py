import os
import zipfile
from typing import Tuple
from app.website_generator.utils.logger import generator_logger

class ZipBuilder:
    """
    ZIP Builder packaging static site output into CompanyName-Website.zip
    and verifying zip archive entry integrity.
    """
    @staticmethod
    def create_zip_archive(output_dir: str, company_name: str) -> Tuple[str, str]:
        sanitized_company = "".join(c if c.isalnum() else "-" for c in company_name).strip("-")
        zip_filename = f"{sanitized_company}-Website.zip"
        zip_path = os.path.join(output_dir, zip_filename)

        generator_logger.info(f"ZipBuilder creating ZIP archive: '{zip_filename}'")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    if file == zip_filename:
                        continue  # Skip zip file itself
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, output_dir)
                    zipf.write(abs_path, arcname=rel_path)

        # Validate ZIP archive integrity
        if not zipfile.is_zipfile(zip_path):
            raise ValueError(f"Generated file '{zip_filename}' is not a valid zip archive.")

        generator_logger.info(f"ZipBuilder successfully created and validated '{zip_filename}'")
        return zip_path, zip_filename
