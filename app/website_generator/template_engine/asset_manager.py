import os
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED_ASSETS_DIR = os.path.join(BASE_DIR, "shared_assets")

class AssetManager:
    """
    Asset Manager copying CSS, JS, and image assets to target build directory.
    """
    @staticmethod
    def copy_assets(output_dir: str) -> None:
        target_assets_dir = os.path.join(output_dir, "assets")
        if os.path.exists(target_assets_dir):
            shutil.rmtree(target_assets_dir)

        os.makedirs(target_assets_dir, exist_ok=True)

        if os.path.exists(SHARED_ASSETS_DIR):
            for item in os.listdir(SHARED_ASSETS_DIR):
                s = os.path.join(SHARED_ASSETS_DIR, item)
                d = os.path.join(target_assets_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
