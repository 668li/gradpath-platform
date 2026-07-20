import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.cache import cache
from app.database import Base, get_db
from app.main import app, limiter


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """每个测试前后重置限流器存储，避免限流计数跨测试累积。

    register/login 等端点已加限流，若不重置，前一个测试消耗的额度会影响后一个测试。
    """
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(autouse=True)
def _clear_cache():
    """每个测试前后清空缓存，避免缓存污染跨测试。

    服务层（external_data_service / employment_service 等）引入了 RedisCache，
    而每个测试使用独立的 SQLite 内存数据库。若不清空缓存，前一个测试写入的
    缓存会被后一个测试命中，导致返回错误数据或跳过 DB 查询。
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def db_session():
    """使用 SQLite 内存数据库做测试"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """注册并登录，返回认证头"""
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Test1234!", "name": "测试用户"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "Test1234!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
