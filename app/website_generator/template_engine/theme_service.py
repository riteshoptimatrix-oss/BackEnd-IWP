from typing import Dict

THEME_CLASS_MAP: Dict[str, str] = {
    "White": "theme-white",
    "Dark": "theme-dark",
    "Blue White": "theme-blue-white",
    "Corporate": "theme-corporate",
    "Startup": "theme-startup",
    "Minimal": "theme-minimal",
    "Luxury": "theme-luxury",
    "Glass": "theme-glass",
    "Gradient": "theme-gradient",
}

class ThemeService:
    """
    Theme Engine mapping user theme choices to CSS class tokens.
    Modifies design tokens without altering business content.
    """
    @staticmethod
    def get_theme_class(theme_name: str) -> str:
        return THEME_CLASS_MAP.get(theme_name.strip(), "theme-white")
