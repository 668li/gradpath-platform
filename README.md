# GradPath 职业规划平台

> 考研 / 考公 / 就业一体化决策辅助平台 — 帮助中国大学生从"迷茫"到"上岸"的全流程智能助手。

GradPath 整合考研情报、考公数据、就业市场、AI 决策助手、社区经验与个人成长管理，
基于 FastAPI + Next.js 14 + PostgreSQL + Redis 构建，面向生产级部署。

---

## 目录

- [核心能力](#核心能力)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [环境变量](#环境变量)
- [数据库迁移](#数据库迁移)
- [测试](#测试)
- [代码质量](#代码质量)
- [部署](#部署)
- [备份与恢复](#备份与恢复)
- [监控与告警](#监控与告警)
- [安全合规](#安全合规)
- [许可协议](#许可协议)

---

## 核心能力

| 模块 | 说明 |
|------|------|
| 5 分钟职业诊断 | 新用户引导式诊断，输出三阶段去向建议 |
| 决策助手 | AI 驱动的去向决策（考研 / 考公 / 就业 / 留学），含决策飞轮回顾 |
| 考研情报 | 院校分数线趋势、报录比、调剂成功率、导师评价、经验帖 |
| 考公情报 | 国考 / 省考岗位、报录比、薪资数据 |
| 就业市场 | 公司评价、薪资基准、面试经验、岗位爬虫 |
| AI 长期记忆 | 跨会话用户画像，AI 个性化建议 |
| 暗知识推送 | 决策相关冷门信息主动推送 |
| 社区 | 帖子、评论、问答、导师评价、社区评分 |
| 成长系统 | 里程碑、技能图谱、复盘、上岸报告、徽章 |
| 通知 | WebSocket 实时推送 + 归档 + 自动清理 |

---

## 技术栈

### 后端

- **FastAPI** 0.111+ — 异步 Web 框架
- **SQLAlchemy** 2.0 — ORM（声明式映射）
- **Alembic** — 数据库迁移
- **PostgreSQL** 16 — 主数据库（生产）
- **Redis** 7 — 缓存、限流、WebSocket Pub/Sub
- **Pydantic** v2 — 数据校验
- **slowapi** — 限流（注册 / 登录 / AI 端点）
- **Celery** + **APScheduler** — 异步任务与定时调度
- **prometheus_client** — 多进程指标采集
- **sentry-sdk** — 错误监控（敏感字段过滤）
- **fastapi-mcp** — MCP 协议工具暴露
- **RAG** — 混合检索增强生成（关键词 + 语义搜索）

### 前端

- **Next.js** 14.2 App Router — SSR / RSC
- **TypeScript** 5.5+ — 类型安全
- **Tailwind CSS** 3.4 — 原子化样式
- **SWR** 2.4 — 数据请求与缓存
- **Zustand** 4.5 — 客户端状态管理
- **@sentry/nextjs** 8.30 — 前端错误监控
- **web-vitals** 5.3 — 性能指标采集
- **@axe-core/playwright** — 无障碍测试
- **Vitest** 2.0 + **Playwright** 1.45 — 单测 + E2E

### 基础设施

- **Docker Compose** — 多容器编排（db / redis / backend / frontend / n8n / backup）
- **GitHub Actions** — CI / CD（ci.yml / deploy.yml / codeql.yml）
- **Dependabot** — 依赖自动更新
- **GHCR** — 镜像仓库

---

## 项目结构

```
职业规划/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/                # API 路由（70+ 模块，自动发现注册）
│   │   ├── core/               # 认证 / 缓存 / 异常 / 限流 / 安全头 / WebSocket
│   │   ├── models/             # SQLAlchemy 模型（60+ 表）
│   │   ├── schemas/            # Pydantic Schema
│   │   ├── services/           # 业务服务层（40+ 服务）
│   │   ├── crawlers/           # 爬虫（考研 / 考公 / 就业）
│   │   ├── skills/             # AI Skill（简历优化 / 面试模拟 / 薪资谈判 等）
│   │   ├── metrics.py          # Prometheus 指标
│   │   ├── main.py             # FastAPI 入口
│   │   └── error_handlers.py   # BusinessError 全局处理
│   ├── migrations/             # Alembic 迁移
│   ├── scripts/                # 备份 / 恢复 / 校验脚本
│   ├── tests/                  # pytest 测试（60+ 测试文件）
│   ├── pyproject.toml          # 依赖与工具配置
│   └── Dockerfile
├── frontend/                   # Next.js 14 前端
│   ├── app/                    # App Router 页面
│   │   ├── (app)/              # 受保护路由（需登录）
│   │   │   ├── dashboard/      # 仪表盘
│   │   │   ├── onboarding/     # 5 分钟诊断
│   │   │   ├── decisions/      # 决策实验室
│   │   │   ├── kaoyan/         # 考研情报
│   │   │   ├── civil-service/  # 考公情报
│   │   │   ├── employment/     # 就业市场
│   │   │   ├── community/      # 社区
│   │   │   ├── legal/          # 隐私政策 / 用户协议 / Cookie 声明
│   │   │   └── ...
│   │   ├── login/
│   │   ├── register/           # 注册页含 agree_terms 复选框
│   │   └── layout.tsx
│   ├── components/             # React 组件
│   ├── lib/                    # API client / tracker / web-vitals / validations
│   ├── stores/                 # Zustand stores
│   ├── middleware.ts           # Edge 路由守卫
│   ├── sentry.client.config.ts # Sentry 浏览器配置
│   ├── sentry.server.config.ts # Sentry SSR 配置
│   ├── sentry.edge.config.ts   # Sentry Edge 配置
│   ├── vitest.config.ts
│   ├── next.config.js          # withSentryConfig 包装
│   └── package.json
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # 后端 lint/test + 前端 tsc/vitest/build + docker build
│   │   ├── deploy.yml          # GHCR push + SSH 部署 + 健康检查
│   │   ├── codeql.yml          # 代码安全扫描（Python + JavaScript）
│   │   ├── performance.yml
│   │   └── security.yml
│   ├── codeql-config.yml
│   └── dependabot.yml          # pip / npm / github-actions / docker
├── docs/
│   ├── adr/                    # 架构决策记录
│   ├── SECURITY.md
│   └── ENGINEERING_IMPROVEMENTS.md
├── docker-compose.yml          # 开发环境
├── docker-compose.prod.yml     # 生产环境
├── Makefile                    # 常用命令封装
└── README.md
```

---

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 20+
- PostgreSQL 16+（或使用 Docker）
- Redis 7+（或使用 Docker）
- Docker 24+ 与 Docker Compose v2（推荐）

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆仓库
git clone <repo-url> gradpath
cd gradpath

# 2. 生成强密码并写入 .env
python -c "import secrets; print(secrets.token_urlsafe(32))"  # 用于 POSTGRES_PASSWORD
python -c "import secrets; print(secrets.token_urlsafe(32))"  # 用于 REDIS_PASSWORD
python -c "import secrets; print(secrets.token_urlsafe(64))"  # 用于 SECRET_KEY

# 复制 backend/.env.example 到 backend/.env 并填入上述值

# 3. 启动所有服务
docker-compose up -d

# 4. 执行数据库迁移
docker-compose exec backend alembic upgrade head

# 5. 访问
# 前端: http://localhost:4001
# 后端 API: http://localhost:8001/docs
```

### 方式二：本地开发

```bash
# 1. 安装依赖
make install
# 或分别安装
cd backend && pip install -e ".[dev]"
cd frontend && npm ci

# 2. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env 填入数据库 / Redis / SECRET_KEY / LLM_API_KEY

# 3. 启动 PostgreSQL 与 Redis（本地安装或 Docker）
docker run -d --name gradpath-db -e POSTGRES_PASSWORD=<strong-password> \
  -e POSTGRES_DB=gradpath -e POSTGRES_USER=gradpath -p 5432:5432 postgres:16-alpine
docker run -d --name gradpath-redis -p 6379:6379 redis:7-alpine

# 4. 执行迁移
cd backend && alembic upgrade head

# 5. 启动后端（终端 1）
make dev-backend
# 或: cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. 启动前端（终端 2）
make dev-frontend
# 或: cd frontend && npm run dev
```

---

## 环境变量

后端环境变量在 `backend/.env` 配置，参考 `backend/.env.example`：

| 变量 | 必填 | 说明 |
|------|------|------|
| `POSTGRES_PASSWORD` | 是 | PostgreSQL 强密码 |
| `POSTGRES_USER` | 否 | PostgreSQL 用户名（默认 `gradpath`） |
| `POSTGRES_DB` | 否 | 数据库名（默认 `gradpath`） |
| `DATABASE_URL` | 是 | PostgreSQL 连接字符串 |
| `REDIS_PASSWORD` | 是 | Redis 强密码 |
| `REDIS_URL` | 是 | Redis 连接字符串（含密码） |
| `SECRET_KEY` | 是 | JWT 签名密钥（至少 64 字符） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 否 | Access Token 有效期（默认 30 分钟） |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 否 | Refresh Token 有效期（默认 7 天） |
| `ENVIRONMENT` | 否 | `development` / `staging` / `production` |
| `LOG_LEVEL` | 否 | 日志级别（默认 `INFO`） |
| `CORS_ORIGINS` | 是 | 允许的前端源（逗号分隔，不可为 `*`） |
| `LLM_API_KEY` | 是 | LLM API 密钥 |
| `LLM_MODEL` | 否 | LLM 模型名（默认 `glm-4`） |
| `LLM_BASE_URL` | 否 | LLM API 基础 URL |
| `SENTRY_DSN` | 否 | Sentry 错误监控 DSN |
| `FIRECRAWL_API_KEY` | 否 | Firecrawl 爬虫 API Key |

前端环境变量：

| 变量 | 说明 |
|------|------|
| `NEXT_PUBLIC_SENTRY_DSN` | 前端 Sentry DSN |
| `NEXT_PUBLIC_API_URL` | 后端 API URL（生产留空走同源代理） |
| `BACKEND_URL` | SSR 时访问后端的 URL（容器内通信） |
| `NEXT_PUBLIC_TEST_MODE` | 测试模式标志 |

---

## 数据库迁移

```bash
# 执行迁移
make migrate
# 或: cd backend && alembic upgrade head

# 创建新迁移
make migrate-new m="add_user_avatar"
# 或: cd backend && alembic revision --autogenerate -m "add_user_avatar"

# 回滚一个迁移
make migrate-down
# 或: cd backend && alembic downgrade -1

# 查看迁移历史
make migrate-history

# 重置数据库（危险！仅开发环境）
make db-reset
```

迁移文件位于 `backend/migrations/versions/`，按日期前缀命名。

---

## 测试

### 后端测试

```bash
make test-backend
# 或: cd backend && pytest tests/ -v

# 单个测试文件
cd backend && pytest tests/test_web_vitals.py -v

# 带覆盖率
cd backend && pytest tests/ --cov=app --cov-report=html
```

测试使用 SQLite 内存数据库 + pytest fixtures（`db_session` / `client` / `auth_headers`），
无需外部依赖。所有测试均在 conftest.py 中自动重置限流器与缓存。

### 前端测试

```bash
# 单元测试（Vitest）
make test-frontend
# 或: cd frontend && npm run test

# 监听模式
cd frontend && npm run test:watch

# 带覆盖率
cd frontend && npm run test:coverage

# E2E 测试（Playwright，需后端运行）
make test-e2e
# 或: cd frontend && npm run test:e2e

# E2E UI 模式
cd frontend && npm run test:e2e:ui
```

测试覆盖：
- `lib/api/__tests__/client.test.ts` — API client（token / refresh / 重试 / 错误处理）
- `lib/api/__tests__/swr-config.test.ts` — SWR 配置与 401 跳转
- `lib/validations.test.ts` — Zod Schema 边界测试
- `components/__tests__/auth-guard.test.tsx` — AuthGuard 组件
- `components/__tests__/error-boundary.test.tsx` — ErrorBoundary 组件
- `middleware.test.ts` — Edge 路由守卫
- `tests/e2e/a11y.spec.ts` — 无障碍扫描（axe-core）

### 全量测试

```bash
make test
# 包含 test-backend + test-frontend
```

---

## 代码质量

### Lint 与格式化

```bash
# 所有 linter
make lint

# 后端
make lint-backend
# ruff check + isort --check-only

# 前端
make lint-frontend
# next lint

# 自动格式化
make format
# black + isort + ruff --fix + next lint --fix
```

### 类型检查

```bash
make type-check
# 后端: mypy app/（strict 模式）
# 前端: npx tsc --noEmit
```

**mypy strict 模式**（B14）：核心代码严格类型检查；测试 / 迁移 / pipeline 模块通过
per-module override 放宽。

### Pre-commit

```bash
# 安装 git hooks
make pre-commit-install

# 运行所有 pre-commit 检查
make pre-commit-run
```

---

## 部署

### 生产部署（GitHub Actions 自动）

推送到 `main` 分支会触发 `deploy.yml`：

1. **verify-ci** — 等待 ci.yml 通过
2. **build-and-push** — 构建 Docker 镜像并推送到 GHCR（tag: `sha-<short>` + `latest`）
3. **deploy** — SSH 到生产服务器执行：
   - git fetch / reset
   - docker login GHCR
   - docker-compose pull
   - 预部署 pg_dump 备份
   - alembic upgrade head
   - 滚动重启服务
   - 健康检查
4. **notify** — 部署结果通知

### 手动部署

```bash
# 构建镜像
docker-compose -f docker-compose.prod.yml build

# 启动
docker-compose -f docker-compose.prod.yml up -d

# 执行迁移
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 健康检查

- `GET /health` — Liveness probe（数据库 + 磁盘空间）
- `GET /ready` — Readiness probe（数据库 + Redis）
- `GET /metrics` — Prometheus 指标（需登录）
- `GET /api/metrics` — 自定义格式指标

---

## 备份与恢复

### 自动备份

Docker Compose 中的 `backup` 服务通过 cron 自动执行：

| 时间 | 任务 | 说明 |
|------|------|------|
| 每天 02:00 | `backup_db.sh` | PostgreSQL 全量备份（pg_dump -Fc） |
| 每天 02:30 | `backup_redis.sh` | Redis RDB 持久化（BGSAVE + 复制 dump.rdb） |
| 每周日 03:00 | `backup_verify.sh` | 备份完整性校验（5 项检查） |

备份文件存储在 `backup_data` volume，默认保留 14 天。

### 手动备份

```bash
# 备份数据库
docker-compose exec backup /backup-scripts/backup_db.sh

# 备份 Redis
docker-compose exec backup /backup-scripts/backup_redis.sh

# 校验备份
docker-compose exec backup /backup-scripts/backup_verify.sh
```

### 恢复

```bash
# 恢复数据库（需手动确认）
docker-compose exec backup /backup-scripts/restore_db.sh /var/backups/gradpath/gradpath_YYYYMMDD_HHMMSS.dump

# 强制恢复模式（DROP + CREATE，危险）
docker-compose exec backup FORCE_DROP=1 /backup-scripts/restore_db.sh /var/backups/gradpath/gradpath_YYYYMMDD_HHMMSS.dump
```

恢复脚本支持：
- `pg_restore --clean --if-exists --no-owner --exit-on-error` 安全恢复
- `FORCE_DROP=1` 模式：DROP DATABASE + CREATE DATABASE（需手动输入 YES 确认）
- `pg_restore -l` 预校验备份文件完整性

---

## 监控与告警

### Prometheus 指标

- `gradpath_http_requests_total` — HTTP 请求计数（method / path / status）
- `gradpath_http_request_duration_seconds` — HTTP 请求延迟直方图
- `gradpath_llm_calls_total` — LLM 调用计数（model / status）
- `gradpath_llm_call_duration_seconds` — LLM 调用延迟直方图
- `gradpath_active_websockets` — 活跃 WebSocket 连接数
- `gradpath_web_vitals_lcp` / `cls` / `inp` / `ttfb` / `fcp` — 前端性能指标 Gauge
- `gradpath_web_vitals_reports_total` — web-vitals 上报计数

### Sentry 错误监控

后端通过 `sentry-sdk` 自动捕获异常，`before_send` 钩子过滤敏感字段：
- Authorization / Cookie / X-Api-Key headers
- password / token / secret / api_key 等字段名

前端通过 `@sentry/nextjs` 自动捕获前端异常，`beforeSend` 过滤敏感 headers。

### web-vitals 上报

前端 `lib/web-vitals.ts` 监听 LCP / CLS / INP / TTFB / FCP 五个核心指标，
通过 `sendBeacon` 上报到 `/api/metrics/web-vitals`（失败降级 `fetch keepalive`）。

后端 `/api/metrics/web-vitals` 端点：
- 持久化到 `events` 表（`event_type=web_vital`）
- 同步更新 Prometheus Gauge 与 Counter
- 支持按 page / session_id 过滤查询聚合统计（`GET /api/metrics/web-vitals/summary`）

### 备份校验告警

`backup_verify.sh` 检查失败时可配置 `ALERT_WEBHOOK` 发送告警：
- 备份目录存在
- 24h 内有 DB 备份
- DB 备份完整性（pg_restore -l）
- 备份大小合理
- Redis 备份（可选）

---

## 安全合规

### 认证与授权

- JWT 双 Token：access_token（30 分钟）+ refresh_token（7 天）
- Cookie `gradpath_token` 供 Edge Middleware 路由守卫读取
- WebSocket 通过 Sec-WebSocket-Protocol 子协议传递 Token（避免 URL 泄漏）
- MCP 端点强制 Bearer 认证
- 管理员端点（爬虫 / 监控 / metrics）需 `is_admin=True`

### 数据安全

- 密码 bcrypt 哈希
- SQL 参数化查询（禁止 f-string 拼接）
- 输入字段 max_length 约束（防 DoS）
- 错误消息不暴露内部异常细节
- Sentry before_send 过滤敏感字段

### 基础设施安全

- PostgreSQL / Redis 不暴露端口到宿主（仅 docker network 内通信）
- Backend 绑定 127.0.0.1（通过反向代理访问）
- Docker Compose 强制强密码（POSTGRES_PASSWORD / REDIS_PASSWORD）
- SECRET_KEY 不允许默认值，必须配置
- CORS 不允许 `*`（必须显式列出允许的源）

### 安全响应头

`SecurityHeadersMiddleware` 注入：
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security`（HSTS）
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy`

### 合规

- **隐私政策**：`/legal/privacy`
- **用户协议**：`/legal/terms`
- **Cookie 声明**：`/legal/cookie`
- 注册页强制 `agree_terms` 复选框（前后端双重校验）

### 依赖安全

- **Dependabot**：自动检查 pip / npm / github-actions / docker 依赖更新
- **CodeQL**：每周全量代码安全扫描（Python + JavaScript）
- **pip-audit / npm audit**：依赖漏洞扫描

---

## 许可协议

私有项目，未授权不得复制、分发或商用。

---

## 相关文档

- [Docker 部署指南](./DOCKER_README.md)
- [安全策略](./docs/SECURITY.md)
- [工程改进记录](./docs/ENGINEERING_IMPROVEMENTS.md)
- [架构决策记录](./docs/adr/)
- [自动化工作流规则](./AGENTS.md)
