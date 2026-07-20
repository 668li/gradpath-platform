# backend/tests/test_config.py
"""配置校验测试（Task 2）。"""
import pytest

from app.config import Settings


def test_default_environment_is_development(monkeypatch):
    """默认环境为 development。"""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    # _env_file=None 阻止从 .env 加载，仅使用环境变量与默认值
    # 同时设置 SECRET_KEY 以通过非空校验
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-unit-test-0123456789")
    s = Settings(_env_file=None)
    assert s.ENVIRONMENT == "development"


def test_production_with_default_secret_key_raises(monkeypatch):
    """生产环境 + 默认 SECRET_KEY 必须抛出 ValueError。

    修复：pydantic-settings 默认从 .env 文件加载，monkeypatch.delenv 仅清除环境变量，
    不影响 .env 加载。需传入 _env_file=None 阻止 .env 加载，才能验证默认值场景。
    """
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_production_with_custom_secret_key_works(monkeypatch):
    """生产环境 + 自定义 SECRET_KEY 可正常构造。"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "a-very-secure-random-key-0123456789")
    # 生产环境不允许 SQLite，需设置 PostgreSQL DATABASE_URL
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://gradpath:strongpass@localhost:5432/gradpath"
    )
    # 生产环境强制 Redis (A15)
    monkeypatch.setenv("REDIS_URL", "redis://:strongpass@redis:6379/0")
    s = Settings(_env_file=None)
    assert s.ENVIRONMENT == "production"
    assert s.SECRET_KEY == "a-very-secure-random-key-0123456789"


def test_production_with_sqlite_raises(monkeypatch):
    """生产环境 + SQLite DATABASE_URL 必须抛出 ValueError (A15)。"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "a-very-secure-random-key-0123456789")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./gradpath.db")
    # 给定合法 Redis URL，确保报错只源于 SQLite
    monkeypatch.setenv("REDIS_URL", "redis://:strongpass@redis:6379/0")
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_production_without_redis_raises(monkeypatch):
    """生产环境 + 未配置 REDIS_URL 必须抛出 ValueError (A15)。"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "a-very-secure-random-key-0123456789")
    # 给定合法 PostgreSQL URL，确保报错只源于缺失 Redis
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://gradpath:strongpass@localhost:5432/gradpath"
    )
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_production_with_invalid_redis_scheme_raises(monkeypatch):
    """生产环境 + REDIS_URL 协议错误必须抛出 ValueError (A15)。"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "a-very-secure-random-key-0123456789")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://gradpath:strongpass@localhost:5432/gradpath"
    )
    # 非法协议（应使用 redis:// 或 rediss://）
    monkeypatch.setenv("REDIS_URL", "http://redis:6379/0")
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_production_with_empty_redis_password_raises(monkeypatch):
    """生产环境 + Redis 密码为空字符串必须抛出 ValueError (A15)。"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "a-very-secure-random-key-0123456789")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://gradpath:strongpass@localhost:5432/gradpath"
    )
    # URL 含 password 字段但为空字符串
    monkeypatch.setenv("REDIS_URL", "redis://:@redis:6379/0")
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_production_with_rediss_scheme_works(monkeypatch):
    """生产环境 + rediss:// (TLS) 协议合法 (A15)。"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "a-very-secure-random-key-0123456789")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://gradpath:strongpass@localhost:5432/gradpath"
    )
    monkeypatch.setenv("REDIS_URL", "rediss://:strongpass@redis:6379/0")
    s = Settings(_env_file=None)
    assert s.REDIS_URL.startswith("rediss://")
    assert s.DATABASE_URL.startswith("postgresql+psycopg://")


def test_production_with_valid_config_works(monkeypatch):
    """生产环境 + PostgreSQL + Redis 完整配置可正常构造 (A15)。"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "a-very-secure-random-key-0123456789")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://gradpath:strongpass@localhost:5432/gradpath"
    )
    monkeypatch.setenv("REDIS_URL", "redis://:strongpass@redis:6379/0")
    s = Settings(_env_file=None)
    assert s.ENVIRONMENT == "production"
    assert s.DATABASE_URL.startswith("postgresql://")
    assert s.REDIS_URL.startswith("redis://")
