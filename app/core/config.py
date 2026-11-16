import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from dotenv import load_dotenv

# Ensure .env is loaded regardless of current working directory
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_env_path = os.path.join(_backend_dir, ".env")
load_dotenv(_env_path)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_path,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name: str = os.getenv("DATABASE_NAME", "servicebookingdb")

    # Security & JWT
    jwt_secret: str = os.getenv("JWT_SECRET", "default_jwt_secret_change_in_production_key_123456")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "43200"))
    session_expire_days: int = int(os.getenv("SESSION_EXPIRE_DAYS", "30"))

    # AI Integration
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    # Server Configuration
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    environment: str = os.getenv("ENVIRONMENT", "development")
    enable_docs: bool = os.getenv("ENABLE_DOCS", "true").lower() in ("true", "1", "yes")

    # Security Rate Limiting
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    rate_limit_auth_per_minute: int = int(os.getenv("RATE_LIMIT_AUTH_PER_MINUTE", "20"))


settings = Settings()

