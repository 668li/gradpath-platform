# GradPath 后端实现计划（Phase 1）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 GradPath 个人职业轨迹平台的后端 API，包括认证、去向决策、职业事件、技能树、复盘、看板六大模块。

**Architecture:** FastAPI + SQLAlchemy 2.0 + PostgreSQL，三层架构（models → services → api），TDD 驱动，每个实体走 RED→GREEN→REFACTOR→COMMIT 循环。

**Tech Stack:** Python 3.11+、FastAPI、SQLAlchemy 2.0、Alembic、Pydantic v2、python-jose (JWT)、bcrypt、pytest、httpx (TestClient)

---

## 文件结构

```
backend/
├── pyproject.toml              # 依赖管理
├── .env.example                # 环境变量模板
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置加载
│   ├── database.py             # 数据库引擎/会话
│   ├── models/
│   │   ├── __init__.py         # 导出所有模型
│   │   ├── base.py             # DeclarativeBase + 公共 Mixin
│   │   ├── user.py
│   │   ├── destination_decision.py
│   │   ├── career_event.py
│   │   ├── skill_node.py
│   │   ├── retrospective.py
│   │   └── reference_snapshot.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── decision.py
│   │   ├── event.py
│   │   ├── skill.py
│   │   ├── retrospective.py
│   │   └── dashboard.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py         # JWT + bcrypt
│   │   └── deps.py             # 依赖注入（当前用户）
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── decision_service.py
│   │   ├── event_service.py
│   │   ├── skill_service.py
│   │   ├── retrospective_service.py
│   │   └── dashboard_service.py
│   └── api/
│       ├── __init__.py
│       ├── router.py           # 总路由聚合
│       ├── auth.py
│       ├── decisions.py
│       ├── events.py
│       ├── skills.py
│       ├── retrospectives.py
│       └── dashboard.py
├── alembic/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # pytest fixtures（测试 DB、客户端）
│   ├── test_auth.py
│   ├── test_decisions.py
│   ├── test_events.py
│   ├── test_skills.py
│   ├── test_retrospectives.py
│   └── test_dashboard.py
└── alembic.ini
```

---

## Stage 1: 项目初始化与数据库基础

### Task 1: 初始化后端项目结构

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "gradpath-backend"
version = "0.1.0"
description = "GradPath personal career trajectory platform backend"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy>=2.0.30",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.9",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.2.0",
    "python-jose[cryptography]>=3.3.0",
    "bcrypt>=4.1.0",
    "python-multipart>=0.0.9",
    "email-validator>=2.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: 创建 .env.example**

```env
DATABASE_URL=postgresql://gradpath:gradpath@localhost:5432/gradpath
SECRET_KEY=change-me-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

- [ ] **Step 3: 创建 config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://gradpath:gradpath@localhost:5432/gradpath"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- [ ] **Step 4: 创建 app/__init__.py（空文件）**

- [ ] **Step 5: 安装依赖并验证**

Run: `cd /workspace/backend && pip install -e ".[dev]" --break-system-packages`
Expected: 成功安装所有依赖

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: initialize backend project structure"
```

---

### Task 2: 数据库连接与 Base 模型

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建 database.py**

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: 创建 models/base.py（公共 Mixin）**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
```

- [ ] **Step 3: 创建 models/__init__.py（占位，后续填充）**

```python
# 模型将在后续 Task 中导入
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/database.py backend/app/models/
git commit -m "feat: add database connection and base models"
```

---

### Task 3: User 模型与认证

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/core/security.py`
- Create: `backend/app/core/deps.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: 写失败测试 — conftest.py**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


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
```

- [ ] **Step 2: 写失败测试 — test_auth.py**

```python
def test_register_success(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "Pass1234!", "name": "新用户"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["name"] == "新用户"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email(client):
    client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "Pass1234!", "name": "用户1"},
    )
    resp = client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "Pass1234!", "name": "用户2"},
    )
    assert resp.status_code == 409


def test_login_success(client):
    client.post(
        "/api/auth/register",
        json={"email": "login@example.com", "password": "Pass1234!", "name": "登录用户"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "Pass1234!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={"email": "wrong@example.com", "password": "Pass1234!", "name": "用户"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "WrongPass!"},
    )
    assert resp.status_code == 401


def test_get_me(auth_headers, client):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


def test_get_me_unauthorized(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
```

- [ ] **Step 3: 运行测试验证失败**

Run: `cd /workspace/backend && python -m pytest tests/test_auth.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 4: 创建 User 模型**

```python
# app/models/user.py
import enum
from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampMixin, UUIDMixin


class UserStage(str, enum.Enum):
    student = "student"
    graduating = "graduating"
    early_career = "early_career"
    experienced = "experienced"


class User(UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    current_stage: Mapped[UserStage | None] = mapped_column(Enum(UserStage), nullable=True)
    school: Mapped[str | None] = mapped_column(String(255), nullable=True)
    major: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 5: 创建 security.py**

```python
# app/core/security.py
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
```

- [ ] **Step 6: 创建 deps.py**

```python
# app/core/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    creds_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise creds_error
    except Exception:
        raise creds_error

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise creds_error
    return user
```

- [ ] **Step 7: 创建 auth schemas**

```python
# app/schemas/auth.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserStage


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    current_stage: UserStage | None = None
    school: str | None = None
    major: str | None = None
    graduation_year: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 8: 创建 auth_service.py**

```python
# app/services/auth_service.py
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest


def register(db: Session, data: RegisterRequest) -> User:
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已注册")
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(db: Session, email: str, password: str) -> dict:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")
    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
    }
```

- [ ] **Step 9: 创建 auth API 路由**

```python
# app/api/auth.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import login, register

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_endpoint(data: RegisterRequest, db: Session = Depends(get_db)):
    return register(db, data)


@router.post("/login", response_model=TokenResponse)
def login_endpoint(data: LoginRequest, db: Session = Depends(get_db)):
    return login(db, data.email, data.password)


@router.get("/me", response_model=UserResponse)
def me_endpoint(current_user: User = Depends(get_current_user)):
    return current_user
```

- [ ] **Step 10: 创建 main.py**

```python
# app/main.py
from fastapi import FastAPI

from app.api.auth import router as auth_router

app = FastAPI(title="GradPath API", version="0.1.0")

app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 11: 更新 models/__init__.py**

```python
from app.models.user import User, UserStage

__all__ = ["User", "UserStage"]
```

- [ ] **Step 12: 创建 schemas/__init__.py 和 core/__init__.py（空文件）**

- [ ] **Step 13: 运行测试验证通过**

Run: `cd /workspace/backend && python -m pytest tests/test_auth.py -v`
Expected: 全部 6 个测试 PASS

- [ ] **Step 14: Commit**

```bash
git add backend/
git commit -m "feat: add User model and JWT authentication"
```

---

## Stage 2: 去向决策模块

### Task 4: DestinationDecision 模型与 API

**Files:**
- Create: `backend/app/models/destination_decision.py`
- Create: `backend/app/schemas/decision.py`
- Create: `backend/app/services/decision_service.py`
- Create: `backend/app/api/decisions.py`
- Create: `backend/tests/test_decisions.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 写失败测试 — test_decisions.py**

```python
def test_create_decision_employment(auth_headers, client):
    resp = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-06-27",
            "destination_type": "employment",
            "status": "planned",
            "details": {
                "company": "腾讯",
                "position": "后端开发",
                "city": "深圳",
                "salary_range": "25-30k",
                "company_nature": "民企",
            },
            "reasoning": "大厂平台好，技术成长快",
            "confidence": 4,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["destination_type"] == "employment"
    assert data["details"]["company"] == "腾讯"
    assert data["confidence"] == 4


def test_create_decision_postgrad(auth_headers, client):
    resp = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-06-27",
            "destination_type": "postgrad",
            "status": "planned",
            "details": {"target_school": "清华大学", "target_major": "计算机", "result": "pending"},
            "reasoning": "想深造",
            "confidence": 3,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["destination_type"] == "postgrad"


def test_list_decisions(auth_headers, client):
    for dtype in ["employment", "abroad", "civil_service"]:
        client.post(
            "/api/decisions",
            headers=auth_headers,
            json={
                "decision_date": "2026-06-27",
                "destination_type": dtype,
                "status": "planned",
                "details": {},
                "reasoning": "...",
                "confidence": 3,
            },
        )
    resp = client.get("/api/decisions", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_get_decision_by_id(auth_headers, client):
    create = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-06-27",
            "destination_type": "phd",
            "status": "planned",
            "details": {"school": "北大", "advisor": "张教授", "field": "AI"},
            "reasoning": "走学术路线",
            "confidence": 5,
        },
    )
    did = create.json()["id"]
    resp = client.get(f"/api/decisions/{did}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == did


def test_update_decision(auth_headers, client):
    create = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-06-27",
            "destination_type": "employment",
            "status": "planned",
            "details": {"company": "A公司"},
            "reasoning": "...",
            "confidence": 3,
        },
    )
    did = create.json()["id"]
    resp = client.patch(
        f"/api/decisions/{did}",
        headers=auth_headers,
        json={"status": "confirmed", "confidence": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"
    assert resp.json()["confidence"] == 5


def test_delete_decision(auth_headers, client):
    create = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-06-27",
            "destination_type": "gap_year",
            "status": "planned",
            "details": {"plan": "旅行"},
            "reasoning": "...",
            "confidence": 2,
        },
    )
    did = create.json()["id"]
    resp = client.delete(f"/api/decisions/{did}", headers=auth_headers)
    assert resp.status_code == 204
    resp = client.get(f"/api/decisions/{did}", headers=auth_headers)
    assert resp.status_code == 404


def test_decision_stats(auth_headers, client):
    for dtype in ["employment", "employment", "postgrad", "abroad"]:
        client.post(
            "/api/decisions",
            headers=auth_headers,
            json={
                "decision_date": "2026-06-27",
                "destination_type": dtype,
                "status": "planned",
                "details": {},
                "reasoning": "...",
                "confidence": 3,
            },
        )
    resp = client.get("/api/decisions/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["employment"] == 2
    assert data["postgrad"] == 1
    assert data["abroad"] == 1


def test_decision_unauthorized(client):
    resp = client.get("/api/decisions")
    assert resp.status_code == 401
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /workspace/backend && python -m pytest tests/test_decisions.py -v`
Expected: FAIL

- [ ] **Step 3: 创建模型**

```python
# app/models/destination_decision.py
import enum
from datetime import date
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampMixin, UUIDMixin


class DestinationType(str, enum.Enum):
    employment = "employment"
    postgrad = "postgrad"
    civil_service = "civil_service"
    abroad = "abroad"
    phd = "phd"
    startup = "startup"
    gap_year = "gap_year"


class DecisionStatus(str, enum.Enum):
    planned = "planned"
    confirmed = "confirmed"
    executed = "executed"
    changed = "changed"


class DestinationDecision(UUIDMixin, TimestampMixin):
    __tablename__ = "destination_decisions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    decision_date: Mapped[date] = mapped_column(Date, nullable=False)
    destination_type: Mapped[DestinationType] = mapped_column(Enum(DestinationType), nullable=False)
    status: Mapped[DecisionStatus] = mapped_column(Enum(DecisionStatus), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_snapshot_id: Mapped[UUID | None] = mapped_column(nullable=True)
```

- [ ] **Step 4: 创建 schemas**

```python
# app/schemas/decision.py
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.destination_decision import DecisionStatus, DestinationType


class DecisionCreate(BaseModel):
    decision_date: date
    destination_type: DestinationType
    status: DecisionStatus = DecisionStatus.planned
    details: dict = Field(default_factory=dict)
    reasoning: str | None = None
    confidence: int = Field(ge=1, le=5)


class DecisionUpdate(BaseModel):
    decision_date: date | None = None
    destination_type: DestinationType | None = None
    status: DecisionStatus | None = None
    details: dict | None = None
    reasoning: str | None = None
    confidence: int | None = Field(default=None, ge=1, le=5)


class DecisionResponse(BaseModel):
    id: UUID
    user_id: UUID
    decision_date: date
    destination_type: DestinationType
    status: DecisionStatus
    details: dict
    reasoning: str | None
    confidence: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: 创建 service**

```python
# app/services/decision_service.py
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.destination_decision import DestinationDecision
from app.schemas.decision import DecisionCreate, DecisionUpdate


def create_decision(db: Session, user_id: UUID, data: DecisionCreate) -> DestinationDecision:
    decision = DestinationDecision(user_id=user_id, **data.model_dump())
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


def list_decisions(db: Session, user_id: UUID) -> list[DestinationDecision]:
    return (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.decision_date.desc())
        .all()
    )


def get_decision(db: Session, user_id: UUID, decision_id: UUID) -> DestinationDecision:
    decision = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.id == decision_id, DestinationDecision.user_id == user_id)
        .first()
    )
    if not decision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="决策记录不存在")
    return decision


def update_decision(db: Session, user_id: UUID, decision_id: UUID, data: DecisionUpdate) -> DestinationDecision:
    decision = get_decision(db, user_id, decision_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(decision, key, value)
    db.commit()
    db.refresh(decision)
    return decision


def delete_decision(db: Session, user_id: UUID, decision_id: UUID) -> None:
    decision = get_decision(db, user_id, decision_id)
    db.delete(decision)
    db.commit()


def get_decision_stats(db: Session, user_id: UUID) -> dict[str, int]:
    decisions = db.query(DestinationDecision).filter(DestinationDecision.user_id == user_id).all()
    stats: dict[str, int] = {}
    for d in decisions:
        key = d.destination_type.value
        stats[key] = stats.get(key, 0) + 1
    return stats
```

- [ ] **Step 6: 创建 API 路由**

```python
# app/api/decisions.py
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.decision import DecisionCreate, DecisionResponse, DecisionUpdate
from app.services.decision_service import (
    create_decision,
    delete_decision,
    get_decision,
    get_decision_stats,
    list_decisions,
    update_decision,
)

router = APIRouter(prefix="/api/decisions", tags=["去向决策"])


@router.post("", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
def create(data: DecisionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_decision(db, user.id, data)


@router.get("", response_model=list[DecisionResponse])
def list_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list_decisions(db, user.id)


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_decision_stats(db, user.id)


@router.get("/{decision_id}", response_model=DecisionResponse)
def get_one(decision_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_decision(db, user.id, decision_id)


@router.patch("/{decision_id}", response_model=DecisionResponse)
def update(decision_id: UUID, data: DecisionUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return update_decision(db, user.id, decision_id, data)


@router.delete("/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(decision_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_decision(db, user.id, decision_id)
```

- [ ] **Step 7: 更新 models/__init__.py 和 main.py**

```python
# models/__init__.py 追加
from app.models.destination_decision import (
    DecisionStatus,
    DestinationDecision,
    DestinationType,
)

__all__ = ["User", "UserStage", "DestinationDecision", "DestinationType", "DecisionStatus"]
```

```python
# main.py 追加路由
from app.api.decisions import router as decisions_router
app.include_router(decisions_router)
```

- [ ] **Step 8: 运行测试验证通过**

Run: `cd /workspace/backend && python -m pytest tests/test_decisions.py -v`
Expected: 全部 8 个测试 PASS

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat: add DestinationDecision model and CRUD API with stats"
```

---

## Stage 3: 职业成长事件模块

### Task 5: CareerEvent 模型与 API

**Files:**
- Create: `backend/app/models/career_event.py`
- Create: `backend/app/schemas/event.py`
- Create: `backend/app/services/event_service.py`
- Create: `backend/app/api/events.py`
- Create: `backend/tests/test_events.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 写失败测试 — test_events.py**

```python
from datetime import date


def test_create_event(auth_headers, client):
    resp = client.post(
        "/api/events",
        headers=auth_headers,
        json={
            "event_date": "2026-06-01",
            "event_type": "onboard",
            "title": "入职腾讯",
            "description": "后端开发工程师",
            "situation": "校招拿到offer",
            "task": "熟悉业务代码",
            "action": "参加新人培训+结对编程",
            "result": "两周内完成第一个需求",
            "reflection": "应该更主动地与导师沟通",
            "skills_gained": ["Go", "微服务"],
            "mood": 4,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "入职腾讯"
    assert "Go" in data["skills_gained"]
    assert data["reflection"] is not None


def test_list_events_filtered_by_type(auth_headers, client):
    for etype in ["onboard", "promotion", "onboard"]:
        client.post(
            "/api/events",
            headers=auth_headers,
            json={
                "event_date": "2026-06-01",
                "event_type": etype,
                "title": f"事件-{etype}",
                "description": "...",
            },
        )
    resp = client.get("/api/events?event_type=onboard", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_events_filtered_by_date_range(auth_headers, client):
    for d in ["2026-01-15", "2026-03-20", "2026-06-10"]:
        client.post(
            "/api/events",
            headers=auth_headers,
            json={
                "event_date": d,
                "event_type": "other",
                "title": f"事件-{d}",
                "description": "...",
            },
        )
    resp = client.get(
        "/api/events?start_date=2026-02-01&end_date=2026-05-01",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_update_event(auth_headers, client):
    create = client.post(
        "/api/events",
        headers=auth_headers,
        json={
            "event_date": "2026-06-01",
            "event_type": "skill_acquired",
            "title": "学习Docker",
            "description": "...",
        },
    )
    eid = create.json()["id"]
    resp = client.patch(
        f"/api/events/{eid}",
        headers=auth_headers,
        json={"title": "掌握Docker", "skills_gained": ["Docker", "K8s"]},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "掌握Docker"
    assert "K8s" in resp.json()["skills_gained"]


def test_delete_event(auth_headers, client):
    create = client.post(
        "/api/events",
        headers=auth_headers,
        json={
            "event_date": "2026-06-01",
            "event_type": "other",
            "title": "待删除",
            "description": "...",
        },
    )
    eid = create.json()["id"]
    resp = client.delete(f"/api/events/{eid}", headers=auth_headers)
    assert resp.status_code == 204
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /workspace/backend && python -m pytest tests/test_events.py -v`
Expected: FAIL

- [ ] **Step 3: 创建模型**

```python
# app/models/career_event.py
import enum
from datetime import date
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampMixin, UUIDMixin


class EventType(str, enum.Enum):
    onboard = "onboard"
    leave = "leave"
    promotion = "promotion"
    transfer = "transfer"
    skill_acquired = "skill_acquired"
    project_done = "project_done"
    certification = "certification"
    other = "other"


class CareerEvent(UUIDMixin, TimestampMixin):
    __tablename__ = "career_events"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    situation: Mapped[str | None] = mapped_column(Text, nullable=True)
    task: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    reflection: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills_gained: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    impact_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mood: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 4: 创建 schemas**

```python
# app/schemas/event.py
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.career_event import EventType


class EventCreate(BaseModel):
    event_date: date
    event_type: EventType
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None
    reflection: str | None = None
    skills_gained: list[str] = Field(default_factory=list)
    impact_metrics: dict | None = None
    mood: int | None = Field(default=None, ge=1, le=5)


class EventUpdate(BaseModel):
    event_date: date | None = None
    event_type: EventType | None = None
    title: str | None = None
    description: str | None = None
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None
    reflection: str | None = None
    skills_gained: list[str] | None = None
    impact_metrics: dict | None = None
    mood: int | None = Field(default=None, ge=1, le=5)


class EventResponse(BaseModel):
    id: UUID
    user_id: UUID
    event_date: date
    event_type: EventType
    title: str
    description: str | None
    situation: str | None
    task: str | None
    action: str | None
    result: str | None
    reflection: str | None
    skills_gained: list[str]
    impact_metrics: dict | None
    mood: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: 创建 service**

```python
# app/services/event_service.py
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent, EventType
from app.schemas.event import EventCreate, EventUpdate


def create_event(db: Session, user_id: UUID, data: EventCreate) -> CareerEvent:
    event = CareerEvent(user_id=user_id, **data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(
    db: Session,
    user_id: UUID,
    event_type: EventType | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[CareerEvent]:
    query = db.query(CareerEvent).filter(CareerEvent.user_id == user_id)
    if event_type:
        query = query.filter(CareerEvent.event_type == event_type)
    if start_date:
        query = query.filter(CareerEvent.event_date >= start_date)
    if end_date:
        query = query.filter(CareerEvent.event_date <= end_date)
    return query.order_by(CareerEvent.event_date.desc()).all()


def get_event(db: Session, user_id: UUID, event_id: UUID) -> CareerEvent:
    event = (
        db.query(CareerEvent)
        .filter(CareerEvent.id == event_id, CareerEvent.user_id == user_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="事件不存在")
    return event


def update_event(db: Session, user_id: UUID, event_id: UUID, data: EventUpdate) -> CareerEvent:
    event = get_event(db, user_id, event_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, user_id: UUID, event_id: UUID) -> None:
    event = get_event(db, user_id, event_id)
    db.delete(event)
    db.commit()
```

- [ ] **Step 6: 创建 API 路由**

```python
# app/api/events.py
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.career_event import EventType
from app.models.user import User
from app.schemas.event import EventCreate, EventResponse, EventUpdate
from app.services.event_service import (
    create_event,
    delete_event,
    get_event,
    list_events,
    update_event,
)

router = APIRouter(prefix="/api/events", tags=["职业事件"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create(data: EventCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_event(db, user.id, data)


@router.get("", response_model=list[EventResponse])
def list_all(
    event_type: EventType | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list_events(db, user.id, event_type, start_date, end_date)


@router.get("/{event_id}", response_model=EventResponse)
def get_one(event_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_event(db, user.id, event_id)


@router.patch("/{event_id}", response_model=EventResponse)
def update(event_id: UUID, data: EventUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return update_event(db, user.id, event_id, data)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(event_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_event(db, user.id, event_id)
```

- [ ] **Step 7: 更新 __init__.py 和 main.py，运行测试，Commit**

Run: `cd /workspace/backend && python -m pytest tests/test_events.py -v`
Expected: 全部 5 个测试 PASS

```bash
git add backend/
git commit -m "feat: add CareerEvent model with STAR+R fields and filtered CRUD API"
```

---

## Stage 4: 技能树模块

### Task 6: SkillNode 模型与 API

**Files:**
- Create: `backend/app/models/skill_node.py`
- Create: `backend/app/schemas/skill.py`
- Create: `backend/app/services/skill_service.py`
- Create: `backend/app/api/skills.py`
- Create: `backend/tests/test_skills.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 写失败测试 — test_skills.py**

```python
def test_create_skill(auth_headers, client):
    resp = client.post(
        "/api/skills",
        headers=auth_headers,
        json={
            "name": "Python",
            "category": "后端",
            "level": 4,
            "acquired_date": "2024-09-01",
            "notes": "主力语言",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Python"
    assert resp.json()["level"] == 4


def test_skill_tree_with_parent(auth_headers, client):
    parent = client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "后端开发", "category": "后端", "level": 4},
    )
    pid = parent.json()["id"]
    child = client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "FastAPI", "category": "后端", "level": 3, "parent_id": pid},
    )
    assert child.status_code == 201
    assert child.json()["parent_id"] == pid


def test_get_skill_tree(auth_headers, client):
    root = client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "前端", "category": "前端", "level": 3},
    )
    rid = root.json()["id"]
    client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "React", "category": "前端", "level": 4, "parent_id": rid},
    )
    client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "Vue", "category": "前端", "level": 3, "parent_id": rid},
    )
    resp = client.get("/api/skills", headers=auth_headers)
    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) == 1  # 只有一个根节点
    assert len(tree[0]["children"]) == 2


def test_skill_stats(auth_headers, client):
    for cat in ["后端", "后端", "前端", "软技能"]:
        client.post(
            "/api/skills",
            headers=auth_headers,
            json={"name": f"技能-{cat}", "category": cat, "level": 3},
        )
    resp = client.get("/api/skills/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["后端"] == 2
    assert data["前端"] == 1
    assert data["软技能"] == 1


def test_delete_skill(auth_headers, client):
    create = client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "待删", "category": "其他", "level": 1},
    )
    sid = create.json()["id"]
    resp = client.delete(f"/api/skills/{sid}", headers=auth_headers)
    assert resp.status_code == 204
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /workspace/backend && python -m pytest tests/test_skills.py -v`
Expected: FAIL

- [ ] **Step 3: 创建模型**

```python
# app/models/skill_node.py
from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin, UUIDMixin


class SkillNode(UUIDMixin, TimestampMixin):
    __tablename__ = "skill_nodes"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("skill_nodes.id"), nullable=True)
    acquired_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    children: Mapped[list["SkillNode"]] = relationship(
        "SkillNode",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    parent: Mapped["SkillNode | None"] = relationship(
        "SkillNode",
        back_populates="children",
        remote_side="SkillNode.id",
    )
```

- [ ] **Step 4: 创建 schemas**

```python
# app/schemas/skill.py
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.skill_node import SkillNode


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    level: int = Field(ge=1, le=5)
    parent_id: UUID | None = None
    acquired_date: date | None = None
    notes: str | None = None


class SkillUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    level: int | None = Field(default=None, ge=1, le=5)
    parent_id: UUID | None = None
    acquired_date: date | None = None
    notes: str | None = None


class SkillResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    category: str
    level: int
    parent_id: UUID | None
    acquired_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    children: list["SkillResponse"] = []

    model_config = {"from_attributes": True}


SkillResponse.model_rebuild()
```

- [ ] **Step 5: 创建 service**

```python
# app/services/skill_service.py
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.skill_node import SkillNode
from app.schemas.skill import SkillCreate, SkillUpdate


def create_skill(db: Session, user_id: UUID, data: SkillCreate) -> SkillNode:
    if data.parent_id:
        parent = (
            db.query(SkillNode)
            .filter(SkillNode.id == data.parent_id, SkillNode.user_id == user_id)
            .first()
        )
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="父技能不存在")
        if data.parent_id == parent.id:
            pass  # OK
    skill = SkillNode(user_id=user_id, **data.model_dump())
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def get_skill_tree(db: Session, user_id: UUID) -> list[SkillNode]:
    roots = (
        db.query(SkillNode)
        .filter(SkillNode.user_id == user_id, SkillNode.parent_id.is_(None))
        .all()
    )
    return roots


def get_skill(db: Session, user_id: UUID, skill_id: UUID) -> SkillNode:
    skill = (
        db.query(SkillNode)
        .filter(SkillNode.id == skill_id, SkillNode.user_id == user_id)
        .first()
    )
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="技能不存在")
    return skill


def update_skill(db: Session, user_id: UUID, skill_id: UUID, data: SkillUpdate) -> SkillNode:
    skill = get_skill(db, user_id, skill_id)
    update_data = data.model_dump(exclude_unset=True)
    if "parent_id" in update_data and update_data["parent_id"] == skill_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能将自己设为父技能")
    for key, value in update_data.items():
        setattr(skill, key, value)
    db.commit()
    db.refresh(skill)
    return skill


def delete_skill(db: Session, user_id: UUID, skill_id: UUID) -> None:
    skill = get_skill(db, user_id, skill_id)
    db.delete(skill)
    db.commit()


def get_skill_stats(db: Session, user_id: UUID) -> dict[str, int]:
    skills = db.query(SkillNode).filter(SkillNode.user_id == user_id).all()
    stats: dict[str, int] = {}
    for s in skills:
        stats[s.category] = stats.get(s.category, 0) + 1
    return stats
```

- [ ] **Step 6: 创建 API 路由**

```python
# app/api/skills.py
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.skill import SkillCreate, SkillResponse, SkillUpdate
from app.services.skill_service import (
    create_skill,
    delete_skill,
    get_skill,
    get_skill_stats,
    get_skill_tree,
    update_skill,
)

router = APIRouter(prefix="/api/skills", tags=["技能树"])


@router.post("", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def create(data: SkillCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_skill(db, user.id, data)


@router.get("", response_model=list[SkillResponse])
def list_tree(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_skill_tree(db, user.id)


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_skill_stats(db, user.id)


@router.get("/{skill_id}", response_model=SkillResponse)
def get_one(skill_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_skill(db, user.id, skill_id)


@router.patch("/{skill_id}", response_model=SkillResponse)
def update(skill_id: UUID, data: SkillUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return update_skill(db, user.id, skill_id, data)


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(skill_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_skill(db, user.id, skill_id)
```

- [ ] **Step 7: 更新 __init__.py 和 main.py，运行测试，Commit**

Run: `cd /workspace/backend && python -m pytest tests/test_skills.py -v`
Expected: 全部 5 个测试 PASS

```bash
git add backend/
git commit -m "feat: add SkillNode tree model with CRUD and category stats"
```

---

## Stage 5: 复盘模块

### Task 7: Retrospective 模型与 API（含草稿生成）

**Files:**
- Create: `backend/app/models/retrospective.py`
- Create: `backend/app/schemas/retrospective.py`
- Create: `backend/app/services/retrospective_service.py`
- Create: `backend/app/api/retrospectives.py`
- Create: `backend/tests/test_retrospectives.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 写失败测试 — test_retrospectives.py**

```python
def test_create_retrospective(auth_headers, client):
    resp = client.post(
        "/api/retrospectives",
        headers=auth_headers,
        json={
            "period_type": "annual",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "title": "2025年度复盘",
            "achievements": ["晋升P6", "主导核心项目"],
            "challenges": "跨团队协作困难",
            "lessons_learned": "沟通需要更前置",
            "next_steps": ["提升架构能力", "拓展技术视野"],
            "satisfaction": 4,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "2025年度复盘"
    assert len(data["achievements"]) == 2
    assert data["satisfaction"] == 4


def test_list_retrospectives(auth_headers, client):
    for i in range(3):
        client.post(
            "/api/retrospectives",
            headers=auth_headers,
            json={
                "period_type": "quarterly",
                "period_start": "2025-01-01",
                "period_end": "2025-03-31",
                "title": f"Q{i+1}复盘",
                "achievements": [],
                "challenges": "...",
                "lessons_learned": "...",
                "next_steps": [],
                "satisfaction": 3,
            },
        )
    resp = client.get("/api/retrospectives", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_retrospective_draft(auth_headers, client):
    # 创建几个事件
    for title in ["完成A项目", "获得PMP证书", "晋升"]:
        client.post(
            "/api/events",
            headers=auth_headers,
            json={
                "event_date": "2025-06-15",
                "event_type": "project_done",
                "title": title,
                "description": "...",
            },
        )
    resp = client.get(
        "/api/retrospectives/draft?period_start=2025-01-01&period_end=2025-12-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["event_summaries"]) == 3
    assert "完成A项目" in [e["title"] for e in data["event_summaries"]]


def test_update_retrospective(auth_headers, client):
    create = client.post(
        "/api/retrospectives",
        headers=auth_headers,
        json={
            "period_type": "custom",
            "period_start": "2025-01-01",
            "period_end": "2025-06-30",
            "title": "半年复盘",
            "achievements": [],
            "challenges": "",
            "lessons_learned": "",
            "next_steps": [],
            "satisfaction": 3,
        },
    )
    rid = create.json()["id"]
    resp = client.patch(
        f"/api/retrospectives/{rid}",
        headers=auth_headers,
        json={"satisfaction": 5, "achievements": ["新成就"]},
    )
    assert resp.status_code == 200
    assert resp.json()["satisfaction"] == 5
    assert resp.json()["achievements"] == ["新成就"]
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /workspace/backend && python -m pytest tests/test_retrospectives.py -v`
Expected: FAIL

- [ ] **Step 3: 创建模型**

```python
# app/models/retrospective.py
import enum
from datetime import date
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampMixin, UUIDMixin


class PeriodType(str, enum.Enum):
    annual = "annual"
    quarterly = "quarterly"
    project = "project"
    custom = "custom"


class Retrospective(UUIDMixin, TimestampMixin):
    __tablename__ = "retrospectives"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    period_type: Mapped[PeriodType] = mapped_column(Enum(PeriodType), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    achievements: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    challenges: Mapped[str | None] = mapped_column(Text, nullable=True)
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    satisfaction: Mapped[int] = mapped_column(Integer, nullable=False)
```

- [ ] **Step 4: 创建 schemas**

```python
# app/schemas/retrospective.py
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.retrospective import PeriodType


class RetroCreate(BaseModel):
    period_type: PeriodType
    period_start: date
    period_end: date
    title: str = Field(min_length=1, max_length=255)
    achievements: list[str] = Field(default_factory=list)
    challenges: str | None = None
    lessons_learned: str | None = None
    next_steps: list[str] = Field(default_factory=list)
    satisfaction: int = Field(ge=1, le=5)


class RetroUpdate(BaseModel):
    period_type: PeriodType | None = None
    period_start: date | None = None
    period_end: date | None = None
    title: str | None = None
    achievements: list[str] | None = None
    challenges: str | None = None
    lessons_learned: str | None = None
    next_steps: list[str] | None = None
    satisfaction: int | None = Field(default=None, ge=1, le=5)


class RetroResponse(BaseModel):
    id: UUID
    user_id: UUID
    period_type: PeriodType
    period_start: date
    period_end: date
    title: str
    achievements: list[str]
    challenges: str | None
    lessons_learned: str | None
    next_steps: list[str]
    satisfaction: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventSummary(BaseModel):
    id: UUID
    event_date: date
    event_type: str
    title: str


class RetroDraft(BaseModel):
    period_start: date
    period_end: date
    event_summaries: list[EventSummary]
    suggested_achievements: list[str]
```

- [ ] **Step 5: 创建 service**

```python
# app/services/retrospective_service.py
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent
from app.models.retrospective import Retrospective
from app.schemas.retrospective import RetroCreate, RetroUpdate


def create_retrospective(db: Session, user_id: UUID, data: RetroCreate) -> Retrospective:
    retro = Retrospective(user_id=user_id, **data.model_dump())
    db.add(retro)
    db.commit()
    db.refresh(retro)
    return retro


def list_retrospectives(db: Session, user_id: UUID) -> list[Retrospective]:
    return (
        db.query(Retrospective)
        .filter(Retrospective.user_id == user_id)
        .order_by(Retrospective.period_end.desc())
        .all()
    )


def get_retrospective(db: Session, user_id: UUID, retro_id: UUID) -> Retrospective:
    retro = (
        db.query(Retrospective)
        .filter(Retrospective.id == retro_id, Retrospective.user_id == user_id)
        .first()
    )
    if not retro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="复盘不存在")
    return retro


def update_retrospective(db: Session, user_id: UUID, retro_id: UUID, data: RetroUpdate) -> Retrospective:
    retro = get_retrospective(db, user_id, retro_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(retro, key, value)
    db.commit()
    db.refresh(retro)
    return retro


def delete_retrospective(db: Session, user_id: UUID, retro_id: UUID) -> None:
    retro = get_retrospective(db, user_id, retro_id)
    db.delete(retro)
    db.commit()


def generate_draft(
    db: Session, user_id: UUID, period_start: date, period_end: date
) -> dict:
    events = (
        db.query(CareerEvent)
        .filter(
            CareerEvent.user_id == user_id,
            CareerEvent.event_date >= period_start,
            CareerEvent.event_date <= period_end,
        )
        .order_by(CareerEvent.event_date.desc())
        .all()
    )
    event_summaries = [
        {"id": str(e.id), "event_date": e.event_date.isoformat(), "event_type": e.event_type.value, "title": e.title}
        for e in events
    ]
    suggested_achievements = [e.title for e in events if e.event_type.value in ("promotion", "project_done", "certification")]
    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "event_summaries": event_summaries,
        "suggested_achievements": suggested_achievements,
    }
```

- [ ] **Step 6: 创建 API 路由**

```python
# app/api/retrospectives.py
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.retrospective import RetroCreate, RetroResponse, RetroUpdate
from app.services.retrospective_service import (
    create_retrospective,
    delete_retrospective,
    generate_draft,
    get_retrospective,
    list_retrospectives,
    update_retrospective,
)

router = APIRouter(prefix="/api/retrospectives", tags=["阶段复盘"])


@router.post("", response_model=RetroResponse, status_code=status.HTTP_201_CREATED)
def create(data: RetroCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_retrospective(db, user.id, data)


@router.get("", response_model=list[RetroResponse])
def list_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list_retrospectives(db, user.id)


@router.get("/draft")
def draft(
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return generate_draft(db, user.id, period_start, period_end)


@router.get("/{retro_id}", response_model=RetroResponse)
def get_one(retro_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_retrospective(db, user.id, retro_id)


@router.patch("/{retro_id}", response_model=RetroResponse)
def update(retro_id: UUID, data: RetroUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return update_retrospective(db, user.id, retro_id, data)


@router.delete("/{retro_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(retro_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_retrospective(db, user.id, retro_id)
```

- [ ] **Step 7: 更新 __init__.py 和 main.py，运行测试，Commit**

Run: `cd /workspace/backend && python -m pytest tests/test_retrospectives.py -v`
Expected: 全部 4 个测试 PASS

```bash
git add backend/
git commit -m "feat: add Retrospective model with CRUD and draft generation"
```

---

## Stage 6: 看板聚合与 ReferenceSnapshot

### Task 8: Dashboard 聚合 API + ReferenceSnapshot 模型

**Files:**
- Create: `backend/app/models/reference_snapshot.py`
- Create: `backend/app/schemas/dashboard.py`
- Create: `backend/app/services/dashboard_service.py`
- Create: `backend/app/api/dashboard.py`
- Create: `backend/tests/test_dashboard.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 写失败测试 — test_dashboard.py**

```python
def test_dashboard_empty(auth_headers, client):
    resp = client.get("/api/dashboard/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["decisions_count"] == 0
    assert data["events_count"] == 0
    assert data["skills_count"] == 0
    assert data["retrospectives_count"] == 0
    assert data["latest_decision"] is None
    assert data["recent_events"] == []
    assert data["timeline"] == []


def test_dashboard_with_data(auth_headers, client):
    # 创建决策
    client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-06-01",
            "destination_type": "employment",
            "status": "confirmed",
            "details": {"company": "腾讯"},
            "reasoning": "...",
            "confidence": 4,
        },
    )
    # 创建事件
    for title in ["入职", "完成项目", "晋升"]:
        client.post(
            "/api/events",
            headers=auth_headers,
            json={
                "event_date": "2026-06-15",
                "event_type": "onboard",
                "title": title,
                "description": "...",
            },
        )
    # 创建技能
    client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "Python", "category": "后端", "level": 4},
    )

    resp = client.get("/api/dashboard/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["decisions_count"] == 1
    assert data["events_count"] == 3
    assert data["skills_count"] == 1
    assert data["latest_decision"] is not None
    assert len(data["recent_events"]) == 3
    # timeline 合并了决策和事件
    assert len(data["timeline"]) == 4


def test_dashboard_skill_categories(auth_headers, client):
    for cat in ["后端", "后端", "前端"]:
        client.post(
            "/api/skills",
            headers=auth_headers,
            json={"name": f"技能-{cat}", "category": cat, "level": 3},
        )
    resp = client.get("/api/dashboard/overview", headers=auth_headers)
    data = resp.json()
    assert data["skill_categories"]["后端"] == 2
    assert data["skill_categories"]["前端"] == 1
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /workspace/backend && python -m pytest tests/test_dashboard.py -v`
Expected: FAIL

- [ ] **Step 3: 创建 ReferenceSnapshot 模型（预留）**

```python
# app/models/reference_snapshot.py
import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDMixin


class SnapshotSource(str, enum.Enum):
    report = "report"
    community = "community"


class ReferenceSnapshot(UUIDMixin):
    __tablename__ = "reference_snapshots"

    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_type: Mapped[SnapshotSource] = mapped_column(Enum(SnapshotSource), nullable=False)
    query_params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 4: 创建 dashboard schemas**

```python
# app/schemas/dashboard.py
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class TimelineItem(BaseModel):
    id: UUID
    date: date
    type: str  # "decision" 或 "event"
    title: str
    subtitle: str | None = None


class DashboardOverview(BaseModel):
    decisions_count: int
    events_count: int
    skills_count: int
    retrospectives_count: int
    latest_decision: dict | None = None
    recent_events: list[dict] = []
    skill_categories: dict[str, int] = {}
    latest_retrospective: dict | None = None
    timeline: list[TimelineItem] = []
```

- [ ] **Step 5: 创建 dashboard service**

```python
# app/services/dashboard_service.py
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent
from app.models.destination_decision import DestinationDecision
from app.models.retrospective import Retrospective
from app.models.skill_node import SkillNode


def get_overview(db: Session, user_id: UUID) -> dict:
    decisions = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.decision_date.desc())
        .all()
    )
    events = (
        db.query(CareerEvent)
        .filter(CareerEvent.user_id == user_id)
        .order_by(CareerEvent.event_date.desc())
        .all()
    )
    skills = db.query(SkillNode).filter(SkillNode.user_id == user_id).all()
    retros = (
        db.query(Retrospective)
        .filter(Retrospective.user_id == user_id)
        .order_by(Retrospective.period_end.desc())
        .all()
    )

    skill_categories: dict[str, int] = {}
    for s in skills:
        skill_categories[s.category] = skill_categories.get(s.category, 0) + 1

    latest_decision = None
    if decisions:
        d = decisions[0]
        latest_decision = {
            "id": str(d.id),
            "destination_type": d.destination_type.value,
            "status": d.status.value,
            "decision_date": d.decision_date.isoformat(),
        }

    recent_events = [
        {
            "id": str(e.id),
            "title": e.title,
            "event_type": e.event_type.value,
            "event_date": e.event_date.isoformat(),
        }
        for e in events[:5]
    ]

    latest_retro = None
    if retros:
        r = retros[0]
        latest_retro = {
            "id": str(r.id),
            "title": r.title,
            "period_end": r.period_end.isoformat(),
        }

    # 合并 timeline
    timeline = []
    for d in decisions:
        detail = d.details or {}
        timeline.append({
            "id": str(d.id),
            "date": d.decision_date.isoformat(),
            "type": "decision",
            "title": f"去向决策: {d.destination_type.value}",
            "subtitle": detail.get("company") or detail.get("target_school") or "",
        })
    for e in events:
        timeline.append({
            "id": str(e.id),
            "date": e.event_date.isoformat(),
            "type": "event",
            "title": e.title,
            "subtitle": e.event_type.value,
        })
    timeline.sort(key=lambda x: x["date"], reverse=True)

    return {
        "decisions_count": len(decisions),
        "events_count": len(events),
        "skills_count": len(skills),
        "retrospectives_count": len(retros),
        "latest_decision": latest_decision,
        "recent_events": recent_events,
        "skill_categories": skill_categories,
        "latest_retrospective": latest_retro,
        "timeline": timeline,
    }
```

- [ ] **Step 6: 创建 API 路由**

```python
# app/api/dashboard.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.dashboard_service import get_overview

router = APIRouter(prefix="/api/dashboard", tags=["个人看板"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_overview(db, user.id)
```

- [ ] **Step 7: 更新 __init__.py 和 main.py，运行全部测试，Commit**

```python
# models/__init__.py 最终版
from app.models.career_event import CareerEvent, EventType
from app.models.destination_decision import DecisionStatus, DestinationDecision, DestinationType
from app.models.reference_snapshot import ReferenceSnapshot, SnapshotSource
from app.models.retrospective import PeriodType, Retrospective
from app.models.skill_node import SkillNode
from app.models.user import User, UserStage

__all__ = [
    "User", "UserStage",
    "DestinationDecision", "DestinationType", "DecisionStatus",
    "CareerEvent", "EventType",
    "SkillNode",
    "Retrospective", "PeriodType",
    "ReferenceSnapshot", "SnapshotSource",
]
```

```python
# main.py 最终版
from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.decisions import router as decisions_router
from app.api.events import router as events_router
from app.api.retrospectives import router as retrospectives_router
from app.api.skills import router as skills_router

app = FastAPI(title="GradPath API", version="0.1.0")

app.include_router(auth_router)
app.include_router(decisions_router)
app.include_router(events_router)
app.include_router(skills_router)
app.include_router(retrospectives_router)
app.include_router(dashboard_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

Run: `cd /workspace/backend && python -m pytest tests/ -v`
Expected: 全部测试 PASS

```bash
git add backend/
git commit -m "feat: add dashboard overview API and ReferenceSnapshot model (reserved)"
```

---

## Self-Review 计划检查

**1. Spec coverage:**
- 认证模块 → Task 3 ✓
- 去向决策模块 → Task 4 ✓
- 职业成长时间线模块 → Task 5 ✓
- 技能树模块 → Task 6 ✓
- 阶段复盘模块 → Task 7 ✓
- 个人看板模块 → Task 8 ✓
- ReferenceSnapshot 预留 → Task 8 ✓

**2. Placeholder scan:** 无 TBD/TODO，所有代码完整 ✓

**3. Type consistency:**
- `DestinationType` / `DecisionStatus` 在 model/schema/service/api 中一致 ✓
- `EventType` 在 model/schema/service/api 中一致 ✓
- `SkillResponse.children` 自引用已用 `model_rebuild()` 处理 ✓
- `get_current_user` 依赖注入在所有 API 中一致 ✓

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-27-gradpath-backend.md`. 

**Execution approach: Inline Execution** — 按任务顺序执行，每个任务完成后验证测试通过再进入下一个。
