# GradPath Phase 9: 后端代码健壮性

## 概述

Phase 9 聚焦后端代码健壮性，将 GradPath 从「功能完备的原型」提升为「生产可信赖的服务」。基于对 15 个 service、14 个 API router、261 个测试的系统性审查，识别出两类差距：

- **P0 安全/崩溃风险**：无全局异常处理、SECRET_KEY 默认值不安全、无限流、AI 输入无长度限制
- **P1 运营稳定性**：无结构化日志、数据库无连接池、列表端点无分页、健康检查过于简陋、CORS 硬编码

采用方案 A（按风险优先级分批），先消除 P0 安全风险，再补全 P1 运营稳定性。每批修复伴随测试验证。

---

## P0: 安全与崩溃风险修复

### 1. 全局异常处理器

**文件创建：** `backend/app/core/exceptions.py`

定义自定义异常基类，供 service 层使用（替代直接 raise HTTPException）：

```python
class BusinessError(Exception):
    """业务逻辑异常，默认 400。"""
    status_code: int = 400
    detail: str = "业务错误"

class NotFoundError(BusinessError):
    status_code = 404
    detail = "资源不存在"

class ForbiddenError(BusinessError):
    status_code = 403
    detail = "无权访问"
```

**文件修改：** `backend/app/main.py`

注册全局异常处理器：

```python
@app.exception_handler(BusinessError)
async def business_error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logger.exception("Unhandled exception", extra={"path": request.url.path})
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})
```

- `BusinessError` 子类返回具体 detail 和对应状态码
- 未捕获的 `Exception` 记录完整堆栈到日志，但只返回 `{"detail": "服务器内部错误"}` 给客户端
- 现有 service 层的 `raise HTTPException(...)` 逐步迁移为 `raise NotFoundError(...)` 等（本阶段先改核心 service：decision/skill/retrospective/community，其余保持 HTTPException 不影响功能）

### 2. SECRET_KEY 生产校验

**文件修改：** `backend/app/config.py`

```python
class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    # ... 其他字段 ...

    @model_validator(mode="after")
    def validate_production_config(self):
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "change-me-in-production":
                raise ValueError("生产环境必须设置非默认 SECRET_KEY")
        return self
```

- 新增 `ENVIRONMENT` 字段（development / staging / production）
- 生产环境下 SECRET_KEY 为默认值时阻止启动
- `.env.example` 更新添加 `ENVIRONMENT` 和 `LLM_*` 配置项

### 3. 限流（slowapi）

**依赖安装：** `slowapi`

**文件修改：** `backend/app/main.py`

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
```

**限流规则：**

| 端点 | 限制 | 维度 | 原因 |
|------|------|------|------|
| `POST /api/auth/login` | 5/min | IP | 防暴力破解 |
| `POST /api/auth/register` | 3/min | IP | 防批量注册 |
| `POST /api/ai/decision-advice` | 10/min | user | 防 LLM 配额耗尽 |
| `POST /api/ai/growth-insight` | 10/min | user | 同上 |
| `POST /api/retrospectives/ai-draft` | 10/min | user | 同上 |
| `POST /api/pipeline/ingest/*` | 10/min | user | 防爬虫滥用 |

- 默认使用内存存储（单实例足够），`storage_uri` 可配置 Redis 支持多实例
- 限流命中时返回 429 + `Retry-After` header

### 4. 输入校验加固

**文件修改：** `backend/app/schemas/ai.py`

```python
class DecisionAdviceRequest(BaseModel):
    destination_type: DestinationType
    company: str | None = Field(None, max_length=100)
    position: str | None = Field(None, max_length=100)
    city: str | None = Field(None, max_length=100)
    expected_salary: str | None = Field(None, max_length=50)
    # ...

class GrowthInsightRequest(BaseModel):
    period_start: date
    period_end: date

    @model_validator(mode="after")
    def validate_period(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end 不能早于 period_start")
        return self
```

**文件修改：** `backend/app/schemas/employment.py`

```python
class SearchBody(BaseModel):
    school: str = Field(..., max_length=200)
    # ...

class MajorQuery(BaseModel):
    school: str = Field(..., max_length=200)
    # ...
```

**文件修改：** `backend/app/schemas/retrospective.py`

```python
class AIRetroDraftRequest(BaseModel):
    period_start: date
    period_end: date

    @model_validator(mode="after")
    def validate_period(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end 不能早于 period_start")
        return self
```

---

## P1: 运营稳定性

### 5. 结构化日志

**依赖安装：** `python-json-logger`

**文件创建：** `backend/app/core/logging.py`

```python
import logging
from logging.config import dictConfig

def setup_logging(log_level: str = "INFO"):
    dictConfig({
        "version": 1,
        "handlers": {
            "json": {
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s",
            }
        },
        "root": {"handlers": ["json"], "level": log_level},
    })
```

**文件修改：** `backend/app/main.py`

添加请求日志 middleware：
- 为每个请求生成 `request_id`（UUID4 前 8 位）
- 注入到 `request.state.request_id`
- 记录请求方法、路径、状态码、耗时
- 使用 `contextvars` 将 `request_id` 传递到 service 层日志

**文件修改：** 各 service 文件

在关键操作处添加日志：
- `auth_service`：登录成功/失败、注册
- `decision_service` / `event_service` / `skill_service`：create/update/delete
- `ai_service`：LLM 调用开始/完成/失败
- `pipeline_service`：已有日志，保持一致

**配置：** `app/config.py` 添加 `LOG_LEVEL: str = "INFO"`

### 6. 数据库连接池

**文件修改：** `backend/app/database.py`

```python
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args=connect_args,
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

**文件修改：** `backend/app/main.py`

```python
# 仅开发环境自动建表
if settings.ENVIRONMENT == "development":
    Base.metadata.create_all(bind=engine)
```

### 7. API 分页

**新增 schema：** `backend/app/schemas/common.py`

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
```

**修改端点（返回 `PaginatedResponse`）：**

| 端点 | 原返回 | 新返回 |
|------|--------|--------|
| `GET /api/decisions` | `list[DecisionResponse]` | `PaginatedResponse[DecisionResponse]` |
| `GET /api/events` | `list[EventResponse]` | `PaginatedResponse[EventResponse]` |
| `GET /api/retrospectives` | `list[RetrospectiveResponse]` | `PaginatedResponse[RetrospectiveResponse]` |
| `GET /api/community/my-reports` | `list[CommunityReport]` | `PaginatedResponse[CommunityReport]` |
| `GET /api/interview/my-reports` | `list[InterviewReport]` | `PaginatedResponse[InterviewReport]` |

- `GET /api/skills` 保持不变（技能树需要完整数据）
- service 层新增 `list_paginated(db, user_id, page, page_size) -> tuple[list, int]` 方法
- 前端 `lib/api.ts` 返回类型更新为 `{items, total, page, page_size}`
- 前端列表页面添加分页导航组件（页码 + 上一页/下一页）

**向后兼容：** 前端通过更新 API 客户端类型自动适配，无需保留旧端点。AI 上下文构建（decision_advice_service、growth_insight_service）内部直接查 DB 不走 API，不受影响。

### 8. 健康检查增强

**文件修改：** `backend/app/main.py`

```python
@app.get("/health")
def health():
    """Liveness probe — 进程存活即返回 ok。"""
    return {"status": "ok"}

@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness probe — 检查数据库连通性。"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="数据库不可用")
```

### 9. CORS 可配置

**文件修改：** `backend/app/config.py`

```python
CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
```

**文件修改：** `backend/app/main.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

## 测试计划

### P0 新增测试（~20 个）

**`tests/test_exceptions.py`**（~6 个）：
- 全局异常处理器：未捕获异常返回 500 + `{"detail": "服务器内部错误"}`
- `BusinessError` 返回对应状态码和 detail
- `NotFoundError` 返回 404
- `ForbiddenError` 返回 403
- 异常时记录日志（mock logger 验证调用）
- 现有 HTTPException 仍正常工作

**`tests/test_config.py`**（~3 个）：
- 默认环境为 development
- 生产环境 + 默认 SECRET_KEY → 启动报错
- 生产环境 + 自定义 SECRET_KEY → 正常

**`tests/test_rate_limit.py`**（~5 个）：
- 登录限流：第 6 次请求返回 429
- 注册限流：第 4 次请求返回 429
- AI 端点限流：第 11 次请求返回 429
- 限流响应包含 `Retry-After` header
- 不同 IP/user 独立计数

**`tests/test_input_validation.py`**（~6 个）：
- DecisionAdviceRequest：company 超 100 字符 → 422
- GrowthInsightRequest：period_end < period_start → 422
- AIRetroDraftRequest：period_end < period_start → 422
- SearchBody：school 超 200 字符 → 422
- 正常长度输入通过校验

### P1 新增测试（~15 个）

**`tests/test_logging.py`**（~3 个）：
- 请求 middleware 生成 request_id
- 日志输出 JSON 格式
- service 层日志包含 request_id

**`tests/test_pagination.py`**（~8 个）：
- decisions 分页：返回正确 items/total/page/page_size
- events 分页：第 2 页数据正确
- retrospectives 分页：page_size 边界（1, 100）
- community 分页：空数据返回 total=0
- interview 分页：总数正确
- 前端 API 类型兼容（通过 tsc 验证）

**`tests/test_health.py`**（~4 个）：
- `/health` 始终返回 200
- `/ready` 数据库正常时返回 200 + database: connected
- `/ready` 数据库异常时返回 503
- CORS preflight 返回正确 headers

---

## 文件变更清单

### 新建文件（6 个）
- `backend/app/core/exceptions.py` — 自定义异常类
- `backend/app/core/logging.py` — 结构化日志配置
- `backend/app/schemas/common.py` — PaginatedResponse, PaginationParams
- `backend/tests/test_exceptions.py`
- `backend/tests/test_rate_limit.py`
- `backend/tests/test_health.py`

### 修改文件（~18 个）
- `backend/app/config.py` — ENVIRONMENT, CORS_ORIGINS, LOG_LEVEL, model_validator
- `backend/app/database.py` — 连接池参数, get_db rollback
- `backend/app/main.py` — 异常处理器, 限流, 日志 middleware, CORS, 健康检查, 条件建表
- `backend/app/schemas/ai.py` — max_length, period 校验
- `backend/app/schemas/employment.py` — max_length
- `backend/app/schemas/retrospective.py` — period 校验
- `backend/app/schemas/decision.py` — 可能微调
- `backend/app/services/decision_service.py` — 分页查询, 异常迁移
- `backend/app/services/event_service.py` — 分页查询, 异常迁移
- `backend/app/services/retrospective_service.py` — 分页查询, 异常迁移
- `backend/app/services/community_service.py` — 分页查询, 异常迁移
- `backend/app/services/interview_service.py` — 分页查询, 异常迁移
- `backend/app/services/auth_service.py` — 日志
- `backend/app/services/ai_service.py` — 日志
- `backend/app/api/decisions.py` — 分页参数
- `backend/app/api/events.py` — 分页参数
- `backend/app/api/retrospectives.py` — 分页参数
- `backend/app/api/community.py` — 分页参数
- `backend/app/api/interview.py` — 分页参数
- `backend/.env.example` — 补全配置项
- `frontend/lib/api.ts` — 分页返回类型更新
- `frontend/types/index.ts` — PaginatedResponse 类型
- `frontend/components/ui/pagination.tsx` — 分页导航组件（新建）
- 前端各列表页面 — 分页 UI 适配

---

## 验证步骤

### 后端
1. `cd /workspace/backend && python -m pytest -q` — 全部通过（261 现有 + ~35 新增 = ~296）
2. 手动验证：连续 6 次登录请求 → 第 6 次返回 429
3. 手动验证：`ENVIRONMENT=production SECRET_KEY=change-me-in-production python -c "from app.config import Settings; Settings()"` → 报错
4. 手动验证：`curl /ready` → 200 + database: connected
5. 手动验证：`curl -X POST /api/ai/growth-insight -d '{"period_start":"2025-12-01","period_end":"2025-01-01"}'` → 422

### 前端
1. `cd /workspace/frontend && npx tsc --noEmit` — 无类型错误
2. `cd /workspace/frontend && npm run build` — 构建成功
3. E2E：列表页面显示分页导航，翻页功能正常
