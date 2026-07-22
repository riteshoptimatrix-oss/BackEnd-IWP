import html
from typing import Any, Dict, List

class ContentSanitizer:
    """
    Sanitizes AI-generated strings by performing HTML entity escaping
    to prevent script injection (XSS) while preserving structure.
    """
    @classmethod
    def sanitize_text(cls, text: str) -> str:
        if not text:
            return ""
        # Escape raw HTML tags
        return html.escape(text.strip())

    @classmethod
    def sanitize_object(cls, obj: Any) -> Any:
        if isinstance(obj, str):
            return cls.sanitize_text(obj)
        elif isinstance(obj, list):
            return [cls.sanitize_object(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: cls.sanitize_object(v) for k, v in obj.items()}
        return obj
