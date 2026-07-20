import json
import logging
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger("app.config")


def parse_cors_origins(value: Optional[str]) -> List[str]:
    if not value or not value.strip():
        logger.warning("CORS_ORIGINS is empty or missing — defaulting to ['http://localhost:3000']")
        return ["http://localhost:3000"]

    stripped = value.strip()

    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return _validate_origins(parsed)
            logger.warning("CORS_ORIGINS JSON is not a list — treating as plain string")
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("CORS_ORIGINS contains invalid JSON (%s) — falling back to comma parsing", e)

    parts = [p.strip().strip('"').strip("'") for p in stripped.split(",")]
    return _validate_origins(parts)


def _validate_origins(origins: List[str]) -> List[str]:
    seen: set[str] = set()
    result: list[str] = []
    for origin in origins:
        origin = origin.strip()
        if not origin:
            continue
        if origin in seen:
            continue
        result.append(origin)
        seen.add(origin)
    return result


class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "indiawebprogrammers"
    JWT_SECRET_KEY: str = "change-this-to-a-secure-random-string-in-production"
    JWT_REFRESH_SECRET_KEY: str = "change-this-to-another-secure-random-string-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = '["http://localhost:3000"]'
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins_list(self) -> List[str]:
        return parse_cors_origins(self.CORS_ORIGINS)

    @field_validator("PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if v < 1 or v > 65535:
            return 8000
        return v

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "production", "staging", "testing"}
        val = v.lower().strip()
        if val not in allowed:
            return "development"
        return val

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        val = v.upper().strip()
        if val not in allowed:
            return "INFO"
        return val

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_access_token_expiry(cls, v: int) -> int:
        if v < 1:
            return 30
        return v

    @field_validator("REFRESH_TOKEN_EXPIRE_DAYS")
    @classmethod
    def validate_refresh_token_expiry(cls, v: int) -> int:
        if v < 1:
            return 7
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)

logger.info("Environment: %s", settings.ENVIRONMENT)
logger.info("CORS origins: %s", settings.cors_origins_list)
logger.info("MongoDB: %s", settings.MONGODB_URL.split("@")[-1] if "@" in settings.MONGODB_URL else settings.MONGODB_URL)
logger.info("Debug: %s", settings.DEBUG)
