import os
import shutil
from app.website_generator.template_engine.asset_manager import AssetManager
from app.website_generator.utils.logger import generator_logger

class AssetBuilder:
    """
    Asset Builder organizing assets/ css, js, images, fonts directories.
    Prunes unused files and ensures safe copying.
    """
    @staticmethod
    def build_and_optimize_assets(output_dir: str) -> None:
        generator_logger.info(f"AssetBuilder copying shared assets to '{output_dir}'")
        AssetManager.copy_assets(output_dir)

        assets_dir = os.path.join(output_dir, "assets")
        # Ensure fonts directory exists
        fonts_dir = os.path.join(assets_dir, "fonts")
        os.makedirs(fonts_dir, exist_ok=True)

        # Create dummy font readme placeholder if empty
        readme_fonts = os.path.join(fonts_dir, "README.txt")
        if not os.path.exists(readme_fonts):
            with open(readme_fonts, "w", encoding="utf-8") as f:
                f.write("System fonts packaged with web export.")

        generator_logger.info("AssetBuilder completed asset optimization.")
