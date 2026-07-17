import secrets
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./gradpath.db"
    SECRET_KEY: str = "change-me-in-production-do-not-use-default"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Environment and runtime
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # LLM config
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "glm-4"
    LLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"

    # Redis (optional)
    REDIS_URL: Optional[str] = None

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _validate_config(self):
        """Validate configuration on startup."""
        errors = []

        # Production SECRET_KEY must not be default
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "change-me-in-production":
                errors.append(
                    "SECRET_KEY must be set to a secure random value in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
            if len(self.SECRET_KEY) < 32:
                errors.append("SECRET_KEY must be at least 32 characters for security")

        # DATABASE_URL validation
        if self.DATABASE_URL == "sqlite:///./gradpath.db" and self.ENVIRONMENT == "production":
            errors.append("SQLite is not recommended for production. Use PostgreSQL.")

        if errors:
            raise ValueError("\n".join(errors))

        return self


settings = Settings()
