import secrets
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./gradpath.db"
    # 修复: FASTAPI-SECRETS-001 / FASTAPI-AUTH-003
    # SECRET_KEY 必须由 env 注入，禁止使用硬编码默认值。
    # 此处空字符串作为占位符，启动时 _validate_config 会强制校验。
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Environment and runtime
    # ENV: 短别名，供 Sentry / 日志 / 第三方 SDK 使用；与 ENVIRONMENT 保持一致。
    ENV: str = "production"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Sentry (optional) — 未配置时跳过初始化
    SENTRY_DSN: Optional[str] = None

    # LLM config
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "glm-4"
    LLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    # B8: 每用户每日 LLM 调用预算（次）。Redis 不可用时降级到不限制。
    LLM_DAILY_QUOTA: int = 100

    # Redis (optional)
    REDIS_URL: Optional[str] = None

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _validate_config(self):
        """Validate configuration on startup.

        修复: FASTAPI-SECRETS-001 / FASTAPI-AUTH-003
        所有环境均强制校验 SECRET_KEY：必须存在且长度 >= 32。
        生产环境额外禁止使用占位符或默认值。

        修复: FASTAPI-AUTH-003 — 禁止 ALGORITHM="none"，否则 JWT 签名校验
        可被绕过（python-jose 默认拒绝，但显式校验可防御配置错误）。
        """
        errors = []

        # 所有环境都必须有 SECRET_KEY，且长度 >= 32
        if not self.SECRET_KEY:
            errors.append(
                "SECRET_KEY 必须通过环境变量或 .env 配置，禁止为空。"
                "生成方式: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        elif len(self.SECRET_KEY) < 32:
            errors.append(
                "SECRET_KEY 长度必须 >= 32 字符以满足 FASTAPI-AUTH-003 安全要求。"
                "生成方式: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )

        # 修复: FASTAPI-AUTH-003 — 显式拒绝 ALGORITHM="none"
        # python-jose 已默认拒绝，但显式校验可在配置阶段提前暴露错误。
        if self.ALGORITHM.lower() == "none":
            errors.append(
                "ALGORITHM 不能为 'none' (FASTAPI-AUTH-003)，"
                "必须使用强签名算法，如 HS256 / HS512 / RS256。"
            )

        # Production SECRET_KEY must not be default
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY.startswith("change-me-in-production"):
                errors.append(
                    "SECRET_KEY must be set to a secure random value in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )

        # 生产环境强制 PostgreSQL + Redis (A15)
        # SQLite 不适合生产环境（并发写入、类型系统、外键约束等均有限制）；
        # Redis 是缓存/限流/会话依赖，生产环境必须配置。
        if self.ENVIRONMENT == "production":
            # DATABASE_URL 必须以 postgresql:// 或 postgresql+psycopg:// 开头
            if not (
                self.DATABASE_URL.startswith("postgresql://")
                or self.DATABASE_URL.startswith("postgresql+psycopg://")
            ):
                errors.append("生产环境必须使用 PostgreSQL，禁止 SQLite")

            # REDIS_URL 必须非空且以 redis:// 或 rediss:// 开头
            if not self.REDIS_URL or not (
                self.REDIS_URL.startswith("redis://")
                or self.REDIS_URL.startswith("rediss://")
            ):
                errors.append("生产环境必须配置 Redis")
            else:
                # 校验 Redis 密码：URL 包含 password 时不能为空字符串
                # redis://:pass@host / redis://user:pass@host 合法；
                # redis://:@host 或 redis://user:@host 视为密码为空，拒绝。
                from urllib.parse import urlparse
                _parsed_redis = urlparse(self.REDIS_URL)
                if _parsed_redis.password == "":
                    errors.append("生产环境 Redis 密码不能为空字符串")

        if errors:
            raise ValueError("\n".join(errors))

        return self


settings = Settings()
