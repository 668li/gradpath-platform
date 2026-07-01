# backend/tests/test_config.py
"""配置校验测试（Task 2）。"""
import pytest

from app.config import Settings


def test_default_environment_is_development():
    """默认环境为 development。"""
    s = Settings()
    assert s.ENVIRONMENT == "development"


def test_production_with_default_secret_key_raises(monkeypatch):
    """生产环境 + 默认 SECRET_KEY 必须抛出 ValueError。"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    # SECRET_KEY 未设置，保持默认 "change-me-in-production"
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValueError):
        Settings()


def test_production_with_custom_secret_key_works(monkeypatch):
    """生产环境 + 自定义 SECRET_KEY 可正常构造。"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "a-very-secure-random-key-0123456789")
    s = Settings()
    assert s.ENVIRONMENT == "production"
    assert s.SECRET_KEY == "a-very-secure-random-key-0123456789"
