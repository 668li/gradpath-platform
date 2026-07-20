# GradPath 生产就绪与性能彻底修复设计

**日期**：2026-07-20
**目标**：从当前 48/100 成熟度，一次性提升到 85+/100 可上线状态
**驱动**：用户反馈"前端来回滑很卡" + 担心"人数多了会卡" + 要求"成熟产品"

## 1. 问题根因（第一性原理）

### 1.1 卡顿三大链路

| 链路 | 表现 | 根因 |
|------|------|------|
| DOM 雪崩 | 滑动卡顿 | war-room 一次拉 300+200 条全量渲染，无虚拟滚动 |
| 重渲染雪崩 | 操作卡顿 | 100 个 "use client" 文件 + 0 处 React.memo + recharts 内联对象 |
| 同步阻塞 | 并发卡顿 | ASGI worker=4 + 同步 httpx.post(AI 5-15s) → 4 个并发即打满 |

### 1.2 用户量增加后会卡死的 5 个根因

1. **进程内状态**：WebSocket/限流/缓存/Scheduler/Metrics 全是内存字典，4 worker 各一份不一致
2. **同步阻塞调用**：AI + 爬虫 + 导出全同步阻塞 worker
3. **全表 LIKE 扫描**：search/rag/ai_agent/employment 8 处全表扫描
4. **缓存缺失**：get_current_user/build_user_context/公开数据全打 DB
5. **长任务无队列**：爬虫/AI 报告/导出同步执行

### 1.3 对抗式审查致命问题（10 项）

1. `.env.testbak` 泄漏真实 LLM API Key
2. AuthGuard 是空壳 `return <>{children}</>`
3. 无隐私政策/用户协议/Cookie 合规（违反 PIPL）
4. Docker 端口 NEXT_PUBLIC_API_URL 配错
5. 无 Sentry/错误监控
6. 无数据库备份策略
7. 无 CI/CD 自动化部署
8. 前端单测覆盖率几乎为 0
9. AI 服务无熔断/降级
10. 无 sitemap/robots/og:image

## 2. 修复方案（38 个任务，3 个并行工作流）

### 工作流 A：性能与扩展性（A1-A15）

#### A1 前端虚拟滚动 + 服务端分页
- 修改 `app/(app)/war-room/page.tsx`：limit 从 300 改为 20
- 引入 `@tanstack/react-virtual` 对暗知识列表虚拟化
- 添加"加载更多"按钮或无限滚动

#### A2 kaoyan/schools 批量接口
- 后端新增 `GET /api/grad-intel/schools/batch?names=...`
- 前端 `app/(app)/kaoyan/schools/page.tsx` 改单次批量调用，去掉 60 个并发请求

#### A3 React.memo + 提取内联对象
- `components/charts/{Bar,Pie,Radar,Line}Chart.tsx` 提取 `tickStyle`/`axisLineStyle` 到模块顶层
- `IntelCard`/`InsightCard`/`PostCard`/`SkillNodeItem` 用 `React.memo` 包装
- `components/ui/markdown.tsx` 用 `React.memo` 包装

#### A4 添加 loading.tsx + 修复 layout
- 在 `app/(app)/` 下加全局 `loading.tsx` 渲染骨架屏
- 关键路由（dashboard/war-room/kaoyan）单独加 `loading.tsx`
- `AppLayout` 中 auth 逻辑下沉到 `middleware.ts`

#### A5 引入 SWR 替换自实现缓存
- 安装 `swr`
- `lib/api/query-cache.ts` 改为 SWR fetcher
- 所有 GET 请求改 `useSWR`，配置 `revalidateOnFocus` + `dedupingInterval: 5000`

#### A6 修复 90+ 处 key={i}
- 全局替换为 `key={item.id}` 或稳定 key

#### A7 后端 AI 调用全部改 async
- `app/services/ai_service.py`：`httpx.post` → `httpx.AsyncClient`
- `app/services/ai_orchestrator.py`：`def chat` → `async def chat`
- 所有 AI 路由改 `async def` + `await`

#### A8 WebSocket 改 Redis Pub/Sub
- `app/core/websocket_manager.py`：连接表保留进程内，广播走 Redis Pub/Sub
- 每个 worker 订阅 `ws:broadcast` channel，收到消息后向本进程连接推送

#### A9 slowapi + APScheduler 改 Redis 后端
- `app/main.py`：`Limiter(storage_uri="redis://...")`
- `app/api/crawlers.py`：`RedisJobStore(host=..., port=...)` 替换 `MemoryJobStore`

#### A10 crawlers.py 改 Celery 任务队列
- 引入 `celery[asyncio]` + `redis` 作为 broker
- 爬虫任务移到 `app/tasks/crawler_tasks.py`
- API 端点改为提交任务 + 轮询状态

#### A11 get_current_user + build_user_context 加 Redis 缓存
- `app/core/deps.py`：`get_current_user` 加 Redis 缓存，TTL=60s
- `app/services/chat_service.py`：`build_user_context` 加 Redis 缓存，TTL=300s
- 用户数据更新时 invalidate

#### A12 公开数据接口加缓存
- `app/services/external_data_service.py`：`@cached(ttl=3600)` 装饰器
- `app/services/employment_service.py`：`search_employment` 加 5 分钟缓存

#### A13 search/rag/ai_agent 建 pg_trgm GIN 索引
- 新增 Alembic 迁移：`CREATE EXTENSION pg_trgm` + `CREATE INDEX ... USING gin (... gin_trgm_ops)`
- search.py 的 ILIKE 自动走索引

#### A14 替换 prometheus_client
- 删除 `app/api/metrics.py` 内存字典
- 引入 `prometheus_client` 库，配置 `multiprocess.MultiProcessCollector`
- `/api/metrics` 端点返回标准 Prometheus 格式

#### A15 强制 PostgreSQL + Redis 生产配置
- `app/config.py`：`ENVIRONMENT=production` 时拒绝 SQLite
- `docker-compose.prod.yml`：移除 SQLite fallback
- 启动时校验 Redis 可达

### 工作流 B：上线就绪度（B1-B14）

#### B1 吊销泄漏的 LLM Key
- 在云厂商控制台吊销 `.env.testbak` 中的 Key
- 加入 `.gitignore`，从 git history 清除（`git filter-repo`）
- 添加 `pre-commit` hook 用 `trufflehog` 扫描

#### B2 AuthGuard 加真实守卫
- `components/auth-guard.tsx`：未登录时 redirect 到 `/login`
- 新建 `middleware.ts`：服务端检查 token，未登录直接 redirect
- 关键写操作按钮在 user 为 null 时禁用

#### B3 隐私政策/用户协议/Cookie 合规
- 新建 `app/(legal)/terms/page.tsx` 和 `app/(legal)/privacy/page.tsx`
- 注册流程加必勾同意 checkbox
- User 模型加 `consented_at` + `privacy_version` 字段
- 加 Cookie 同意横幅组件
- 加"导出我的数据"和"注销账号"功能

#### B4 修复 Docker 端口配置
- `docker-compose.yml`：删除 `NEXT_PUBLIC_API_URL` 硬编码
- 客户端全部走 `/api/*` 同源代理
- 更新 `AGENTS.md` 和 `DOCKER_README.md`

#### B5 接入 Sentry
- 后端：`sentry-sdk[fastapi]`，在 `main.py` 初始化
- 前端：`@sentry/nextjs`，`next.config.js` 配置
- `error-boundary.tsx` 的 `componentDidCatch` 加 `Sentry.captureException`
- 后端全局异常处理器加 `sentry_sdk.capture_exception`

#### B6 数据库备份脚本
- 新建 `scripts/backup-db.sh`：`pg_dump --format=custom` + 上传 OSS
- cron 任务：日备 7 + 周备 4 + 月备 3
- 新建 `scripts/restore-db.sh` 恢复脚本
- 文档化恢复演练流程

#### B7 CI/CD 自动化部署
- 新建 `.github/workflows/deploy.yml`：main 分支 push → 构建镜像 → 推到 registry → SSH 部署
- 镜像 tag 用 git short sha
- 新建 `.github/workflows/rollback.yml`：输入版本号回滚
- 数据库迁移加 `alembic downgrade` 回滚脚本

#### B8 AI 熔断 + 降级
- `app/services/ai_service.py` 加 `@tenacity.retry(stop=stop_after_attempt(3), wait=wait_exponential)`
- 引入 `circuitbreaker` 库：连续 5 次失败开熔断，30s 后半开试探
- 所有 AI 端点统一 fallback 到"检索结果摘要"或"AI 暂不可用"
- 每用户 LLM 调用日预算（Redis 计数器），超额 429

#### B9 前端核心单测
- `lib/api/client.ts`：401 刷新、超时重试、JSON 解析失败、网络错误
- `stores/auth.ts`：restore / fetchUser 失败 / logout 清理
- 关键组件：`<Field />`、`<Button loading />`、`<EmptyState />`、`<Pagination />`
- CI 加 `vitest --coverage --coverage-thresholds='{"lines":60}'`

#### B10 补 sitemap/robots/og:image
- 新建 `app/sitemap.ts`：返回主要路由
- 新建 `app/robots.ts`：允许爬虫，禁止 `/api/*`、`/admin/*`
- `app/layout.tsx` 的 metadata 补 `openGraph`、`twitter`、`metadataBase`
- 制作 1200x630 默认 og 图放 `public/og-default.png`

#### B11 补 README.md
- 项目简介、技术栈、本地启动、测试命令、部署流程、目录结构、贡献指南
- 更新 `DOCKER_README.md`：删除弱密码 `gradpath123`，写明强密码生成方式

#### B12 a11y 扫描进 CI
- 安装 `@axe-core/playwright`
- 新建 `tests/e2e/a11y.spec.ts`
- 修复图标按钮 `aria-label`
- 验证 `<Field>` 组件 `htmlFor`/`id` 关联

#### B13 ErrorBoundary 页面级隔离 + 表单 onBlur 校验
- 在 `(app)/layout.tsx` 加 ErrorBoundary
- 关键卡片组件外包 ErrorBoundary
- 登录/注册表单加 `onBlur` 校验
- 改用 `react-hook-form` + zod `mode: "onBlur"`

#### B14 Dependabot + pre-commit mypy
- 新建 `.github/dependabot.yml`：每周检查 npm + pip
- `.pre-commit-config.yaml`：mypy stages 改为 `[commit]`
- CI `backend-lint` job 加 `mypy app/`

### 工作流 C：架构与可维护性（C1-C9）

#### C1 清理 backend/ 根目录临时脚本
- 30+ 个 `_check_*.py`、`_crawl_*.py`、`_test_*.py`、`fix_intel*.py`、`zhihu_*.py` 归档到 `scripts/archive/`

#### C2 auth_service 改用 BusinessError
- `app/services/auth_service.py`：`raise HTTPException` 改为 `raise BusinessError`/`NotFoundError`/`ForbiddenError`
- 全局处理器转 HTTP 响应

#### C3 点赞/计数器改原子 UPDATE
- `app/services/comment_service.py`：`comment.like_count += 1` 改为 `UPDATE ... SET like_count = like_count + 1`
- `post.comment_count += 1` 同上
- 其他计数器字段统一改原子操作

#### C4 notifications 表分区/归档
- 新建 Alembic 迁移：按月分区
- 新建归档脚本 `scripts/archive-notifications.py`：90 天前数据移到 `notifications_archive` 表

#### C5 统一 cursor 分页
- `app/services/chat_service.py`：`list_conversations`/`list_messages` 改 cursor
- `app/api/notifications.py`、`posts.py`、`community.py` 同上
- 使用 `app/core/cursor_pagination.py`（已存在但未用）

#### C6 nginx 配置多 backend + ip_hash
- `nginx.conf`：`upstream backend { ip_hash; server backend:8000; server backend2:8000; }`
- `docker-compose.prod.yml`：backend scale=2+

#### C7 调整 docker-compose.prod.yml 资源限制
- db: 512M → 2G / 1.0 → 2.0 CPU
- redis: 256M → 512M / maxmemory 128mb → 512mb
- backend: 1G → 2G / 2.0 → 4.0 CPU

#### C8 批量操作接口
- `app/api/notifications.py`：`POST /batch-delete`、`POST /batch-mark-read`
- `app/api/bookmarks.py`：`POST /batch-delete`
- `app/api/posts.py`：`POST /batch-delete`

#### C9 web-vitals 上报 + 商业化埋点
- `lib/web-vitals.ts`：上报到 `/api/metrics/web-vitals`
- 后端新增 `app/api/metrics.py` web-vitals 收集端点
- `lib/tracker.ts`：添加 `trackEvent(name, props)` 函数
- 关键路径埋点：注册、创建决策、AI 对话、分享

## 3. 实施顺序与依赖

```
阶段 1（并行）：
  B1 吊销 Key（安全紧急）
  B4 修复 Docker 端口
  A15 强制 PostgreSQL + Redis
  C1 清理临时脚本

阶段 2（并行，依赖阶段 1）：
  A7 AI 改 async
  A8 WebSocket Redis Pub/Sub
  A9 slowapi + APScheduler Redis
  A11 user/context 缓存
  A12 公开数据缓存
  B8 AI 熔断降级

阶段 3（并行）：
  A1 虚拟滚动
  A2 批量接口
  A3 React.memo
  A4 loading.tsx
  A5 SWR
  A6 修 key={i}
  B2 AuthGuard
  B10 sitemap/robots
  B13 ErrorBoundary

阶段 4（并行）：
  A10 Celery 任务队列
  A13 pg_trgm 索引
  A14 prometheus_client
  C3 原子 UPDATE
  C5 cursor 分页
  C6 nginx 多 backend
  C7 资源限制
  C8 批量接口

阶段 5（并行）：
  B3 隐私政策
  B5 Sentry
  B6 备份脚本
  B7 CI/CD
  B9 前端单测
  B11 README
  B12 a11y
  B14 Dependabot
  C2 BusinessError
  C4 通知分区
  C9 web-vitals 上报
```

## 4. 新增依赖

### 后端
- `celery[asyncio]` - 任务队列
- `redis` (已有，复用)
- `sentry-sdk[fastapi]` - 错误监控
- `prometheus_client` - 指标
- `circuitbreaker` - 熔断
- `tenacity` - 重试

### 前端
- `swr` - 数据请求
- `@tanstack/react-virtual` - 虚拟滚动
- `@sentry/nextjs` - 错误监控
- `@axe-core/playwright` - a11y（dev）

## 5. 验收标准

| 指标 | 当前 | 目标 |
|------|------|------|
| 后端 pytest | 604 passed | 650+ passed，覆盖新模块 |
| 前端单测 | 2 文件 | 20+ 文件，lines coverage ≥60% |
| 前端 tsc | 0 errors | 0 errors |
| 前端 next build | 成功 | 成功 + 0 useSearchParams 警告 + bundle 减少 20% |
| Lighthouse Performance | 未知 | ≥80 |
| 成熟度评分 | 48/100 | ≥85/100 |
| 并发能力 | 10 用户卡 | 1000 用户流畅 |
| 错误监控 | 无 | Sentry 全覆盖 |
| 备份 | 无 | 日备自动 + 恢复演练通过 |

## 6. 风险与回滚

- 每个阶段独立提交，便于回滚
- 数据库迁移提供 downgrade 脚本
- 新依赖先在 dev 环境验证再上 prod
- 关键路径（登录、AI 调用）保留旧实现作为 fallback，灰度切换

## 7. 不在本次范围

- 国际化（i18n）：暂缓，未来需要出海再做
- 商业化（付费/订阅）：暂缓，先验证 PMF
- K8s 部署：暂用 Docker Compose，未来用户量过万再迁移
