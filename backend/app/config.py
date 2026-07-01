from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./gradpath.db"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # 环境与运行时配置
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # LLM 配置（Phase 2 管道用）
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "glm-4"
    LLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _check_production_secret_key(self):
        """生产环境禁止使用默认 SECRET_KEY，避免令牌签名密钥泄露风险。"""
        if self.ENVIRONMENT == "production" and self.SECRET_KEY == "change-me-in-production":
            raise ValueError("生产环境必须设置非默认 SECRET_KEY")
        return self


settings = Settings()
