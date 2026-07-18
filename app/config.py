from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "indiawebprogrammers"
    JWT_SECRET_KEY: str = "change-this-to-a-secure-random-string-in-production"
    JWT_REFRESH_SECRET_KEY: str = "change-this-to-another-secure-random-string-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:3001"]'
    ENVIRONMENT: str = "development"

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.CORS_ORIGINS)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
