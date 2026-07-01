# Phase 9: 后端代码健壮性 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 GradPath 后端从功能原型提升为生产可信赖服务，消除 P0 安全风险并补全 P1 运营稳定性。

**Architecture:** 分两波实施 — P0 先消除安全/崩溃风险（全局异常、SECRET_KEY 校验、限流、输入校验），P1 再补全运营稳定性（结构化日志、DB 连接池、API 分页、健康检查、CORS）。

**Tech Stack:** FastAPI, slowapi, python-json-logger, SQLAlchemy, Pydantic

---

### Task 1: 全局异常处理器 + 自定义异常类

**Files:**
- Create: `backend/app/core/exceptions.py`
- Create: `backend/tests/test_exceptions.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建 `app/core/exceptions.py`**

```python
class BusinessError(Exception):
    status_code: int = 400
    detail: str = "业务错误"

class NotFoundError(BusinessError):
    status_code = 404
    detail = "资源不存在"

class ForbiddenError(BusinessError):
    status_code = 403
    detail = "无权访问"
```

- [ ] **Step 2: 在 `main.py` 注册全局异常处理器**

注册 `BusinessError` handler（返回对应状态码+detail）和 `Exception` handler（记录堆栈到日志，返回 500+通用消息）。

- [ ] **Step 3: 写测试 `tests/test_exceptions.py`** — 6 个测试

- [ ] **Step 4: 运行测试验证通过**

- [ ] **Step 5: Commit**

### Task 2: SECRET_KEY 生产校验 + 环境配置

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Create: `backend/tests/test_config.py`

- [ ] **Step 1: 在 config.py 添加 ENVIRONMENT 字段 + model_validator**
- [ ] **Step 2: 更新 .env.example 补全 LLM_* 配置项**
- [ ] **Step 3: 写测试 — 3 个测试**
- [ ] **Step 4: 运行测试验证**
- [ ] **Step 5: Commit**

### Task 3: 限流（slowapi）

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/auth.py`, `backend/app/api/ai.py`, `backend/app/api/retrospectives.py`, `backend/app/api/pipeline.py`
- Create: `backend/tests/test_rate_limit.py`

- [ ] **Step 1: 安装 slowapi**
- [ ] **Step 2: 在 main.py 注册 Limiter**
- [ ] **Step 3: 在关键端点添加限流装饰器**
- [ ] **Step 4: 写测试 — 5 个测试**
- [ ] **Step 5: 运行测试验证**
- [ ] **Step 6: Commit**

### Task 4: 输入校验加固

**Files:**
- Modify: `backend/app/schemas/ai.py`, `backend/app/schemas/employment.py`, `backend/app/schemas/retrospective.py`
- Create: `backend/tests/test_input_validation.py`

- [ ] **Step 1: 给 DecisionAdviceRequest 加 max_length**
- [ ] **Step 2: 给 GrowthInsightRequest + AIRetroDraftRequest 加 period 校验**
- [ ] **Step 3: 给 employment schemas 加 max_length**
- [ ] **Step 4: 写测试 — 6 个测试**
- [ ] **Step 5: 运行测试验证**
- [ ] **Step 6: Commit**

### Task 5: 结构化日志

**Files:**
- Create: `backend/app/core/logging.py`
- Modify: `backend/app/main.py`, `backend/app/config.py`
- Modify: `backend/app/services/auth_service.py`, `backend/app/services/ai_service.py`
- Create: `backend/tests/test_logging.py`

- [ ] **Step 1: 安装 python-json-logger**
- [ ] **Step 2: 创建 logging.py 配置**
- [ ] **Step 3: 在 main.py 添加请求日志 middleware + request_id**
- [ ] **Step 4: 在关键 service 添加日志**
- [ ] **Step 5: 写测试 — 3 个测试**
- [ ] **Step 6: 运行测试验证**
- [ ] **Step 7: Commit**

### Task 6: 数据库连接池 + 条件建表

**Files:**
- Modify: `backend/app/database.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 在 database.py 添加连接池参数 + get_db rollback**
- [ ] **Step 2: 在 main.py 改为条件建表**
- [ ] **Step 3: 运行全部测试验证无回归**
- [ ] **Step 4: Commit**

### Task 7: API 分页

**Files:**
- Create: `backend/app/schemas/common.py`
- Modify: 5 个 service + 5 个 API router
- Modify: `frontend/lib/api.ts`, `frontend/types/index.ts`
- Create: `frontend/components/ui/pagination.tsx`
- Modify: 5 个前端列表页面
- Create: `backend/tests/test_pagination.py`

- [ ] **Step 1: 创建 PaginatedResponse schema**
- [ ] **Step 2: 在 service 层添加 list_paginated 方法**
- [ ] **Step 3: 在 API 层添加分页参数**
- [ ] **Step 4: 写后端测试 — 8 个测试**
- [ ] **Step 5: 更新前端类型 + API 客户端**
- [ ] **Step 6: 创建分页导航组件 + 适配列表页面**
- [ ] **Step 7: 运行 tsc + build 验证**
- [ ] **Step 8: Commit**

### Task 8: 健康检查增强 + CORS 可配置

**Files:**
- Modify: `backend/app/main.py`, `backend/app/config.py`
- Create: `backend/tests/test_health.py`

- [ ] **Step 1: 添加 /ready 端点**
- [ ] **Step 2: 添加 CORS_ORIGINS 配置 + 收紧 methods/headers**
- [ ] **Step 3: 写测试 — 4 个测试**
- [ ] **Step 4: 运行测试验证**
- [ ] **Step 5: Commit**
