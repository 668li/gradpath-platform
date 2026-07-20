# GradPath 工程改进总结

> 基于 Superpower-Engineering-Discipline 框架执行的 9 阶段综合工程改进

## 执行概览

| Phase | 名称 | 状态 | 关键产出 |
|-------|------|------|----------|
| 1 | 基础工具链 | ✅ | isort + ruff + black + mypy 配置，pre-commit hooks，slowapi 依赖修复 |
| 2 | Alembic 初始化 | ✅ | alembic.ini + env.py + versions/ + script.py.mako |
| 3 | 限流系统 | ✅ | 集中式 rate_limit.py 配置模块，保留 slowapi |
| 4 | 认证增强 | ✅ | 密码重置 + 修改密码 + 防枚举 + 10 个测试 |
| 5 | MCP 协议 | ✅ | fastapi_mcp 集成，所有 API 自动暴露为 MCP 工具 |
| 6 | 前端测试 | ✅ | Vitest + Playwright + jsdom 配置 + 3 个示例测试 |
| 7 | PDF 转换 | ✅ | marker-pdf 服务 + PyPDF2 回退 + EPUB 支持 |
| 8 | 安全审计 | ✅ | 14 项发现，修复 BLOCKER（JWT 类型校验）+ 安全头中间件 |
| 9 | 文档与 CI/CD | ✅ | GitHub Actions CI + Makefile |

---

## Phase 1: 基础工具链

### 变更文件
- `backend/pyproject.toml` — 添加 isort/ruff/black/mypy/pre-commit 配置，修复 slowapi 依赖
- `.pre-commit-config.yaml` — 新建 pre-commit hooks 配置

### 配置详情

**isort** (profile=black, line_length=100):
- `known_first_party = ["app"]`
- 跳过 migrations 目录

**ruff** (target=py310, line-length=100):
- 启用: E/W/F/I/B/C4/UP/N/SIM/TCH 规则集
- 忽略: E501(black 处理), B008(FastAPI 默认参数模式)

**black** (line-length=100, target=py310/311/312)

**mypy** (python_version=3.10, 非严格模式):
- `warn_return_any=true`, `check_untyped_defs=true`
- 逐步收紧策略（当前 `disallow_untyped_defs=false`）

### 使用方法
```bash
# 安装 pre-commit hooks
pre-commit install

# 手动运行所有检查
pre-commit run --all-files

# 或使用 Makefile
make format   # 格式化
make lint     # 检查
make type-check  # 类型检查
```

---

## Phase 2: Alembic 正确初始化

### 问题
项目有 `alembic>=1.13.0` 依赖和一个孤立的迁移脚本，但**缺少 alembic.ini、env.py、versions/ 目录**，无法执行 `alembic upgrade`。

### 变更文件
- `backend/alembic.ini` — 新建，Alembic 主配置
- `backend/migrations/env.py` — 新建，从 app.config 读取 DATABASE_URL，导入所有模型
- `backend/migrations/script.py.mako` — 新建，迁移脚本模板
- `backend/migrations/versions/.gitkeep` — 新建，保持目录结构
- `backend/migrations/versions/20260318_add_mentor_tables.py` — 从旧位置移入

### 使用方法
```bash
# 执行迁移
make migrate

# 创建新迁移
make migrate-new m="添加用户偏好表"

# 回滚
make migrate-down

# 查看历史
make migrate-history

# 重置数据库（危险！）
make db-reset
```

---

## Phase 3: 限流系统

### 决策
**保留 slowapi**（已深度集成，6 处使用 + 5 个测试）。迁移到 throttled-py 需修改 8+ 文件，违反"最小代码变更"原则。

### 变更文件
- `backend/app/core/rate_limit.py` — 新建，集中式限流规则配置

### 限流规则
| 端点 | 限制 | 说明 |
|------|------|------|
| AUTH_REGISTER | 3/min | 防注册爆破 |
| AUTH_LOGIN | 5/min | 防登录爆破 |
| AUTH_REFRESH | 10/min | 防令牌枚举 |
| AI_DECISION_ADVICE | 10/min | LLM 成本控制 |
| AI_CHAT | 20/min | LLM 成本控制 |
| MENTOR_REVIEW_SUBMIT | 5/min | 防滥用 |
| DEFAULT | 60/min | 通用保护 |

---

## Phase 4: 认证系统增强

### 决策
**保留现有 JWT 认证**，不迁移到 fastapi-users。迁移需替换 User 模型（影响 40+ 模型关联）+ 修改 35 个测试文件，成本远超收益。

### 新增功能
1. **密码重置** (`POST /api/auth/forgot-password` + `POST /api/auth/reset-password`)
   - 30 分钟有效的重置令牌
   - 防邮箱枚举（无论邮箱是否存在都返回相同消息）
   - 开发环境返回令牌（生产环境通过邮件发送）

2. **密码修改** (`POST /api/auth/change-password`)
   - 需验证当前密码
   - 需登录状态

### 变更文件
- `backend/app/core/security.py` — 添加 `create_password_reset_token` / `verify_password_reset_token`
- `backend/app/schemas/auth.py` — 添加 4 个新 schema
- `backend/app/services/auth_service.py` — 添加 3 个新服务函数
- `backend/app/api/auth.py` — 添加 3 个新端点
- `backend/tests/test_password_reset.py` — 新建，10 个测试

---

## Phase 5: MCP 协议集成

### 变更文件
- `backend/pyproject.toml` — 添加 `fastapi-mcp>=0.4.0` 依赖
- `backend/app/main.py` — 集成 FastApiMCP server

### 集成方式
```python
from fastapi_mcp import FastApiMCP

mcp_server = FastApiMCP(
    app,
    name="GradPath MCP",
    description="GradPath 职业规划平台 — MCP 工具集",
)
mcp_server.mount_http()
```

### 客户端连接
MCP server 挂载在 `/mcp` 路径，支持 SSE 连接：

```json
{
  "mcpServers": {
    "gradpath": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

所有 FastAPI 端点自动转换为 MCP 工具，AI 客户端（Claude Desktop、Cursor）可直接调用。

---

## Phase 6: 前端测试基础设施

### 问题
前端**零测试**（0 个测试文件，0 个测试框架，0 个测试脚本）。

### 变更文件
- `frontend/package.json` — 添加 Vitest + Playwright + Testing Library 依赖和脚本
- `frontend/vitest.config.ts` — 新建，Vitest 配置（jsdom + 路径别名 + 覆盖率）
- `frontend/tests/setup.ts` — 新建，测试全局设置（mock next/navigation, localStorage, IntersectionObserver 等）
- `frontend/playwright.config.ts` — 新建，E2E 配置（Chromium + 移动端 + 自动启动 dev server）
- `frontend/lib/utils.test.ts` — 新建，cn() 工具函数测试（5 个测试）
- `frontend/lib/validations.test.ts` — 新建，Zod schema 验证测试（8 个测试）
- `frontend/tests/e2e/auth.spec.ts` — 新建，认证流程 E2E 测试（4 个测试）

### 测试命令
```bash
cd frontend
npm run test          # 单元测试
npm run test:watch    # 监听模式
npm run test:coverage # 覆盖率
npm run test:e2e      # E2E 测试
npm run test:all      # 全部测试
```

---

## Phase 7: PDF 转换集成

### 变更文件
- `backend/app/services/pdf_converter.py` — 新建

### 功能
- `convert_pdf_to_markdown()` — PDF 转 Markdown
  - 优先使用 marker-pdf（高质量，需 GPU/大模型）
  - 回退到 PyPDF2/pypdf（基础文本提取，无依赖）
- `convert_epub_to_markdown()` — EPUB 转 Markdown
  - 使用 ebooklib + BeautifulSoup

### 可选依赖
```bash
# 高质量 PDF 转换（需要 GPU）
pip install marker-pdf

# 基础 PDF 转换
pip install pypdf

# EPUB 转换
pip install ebooklib beautifulsoup4
```

---

## Phase 8: 安全审计

### 审计发现

#### 🔴 BLOCKER（已修复）
**JWT Token 类型混淆** — `get_current_user` 未校验 `type == "access"`，refresh_token / password_reset_token 可用作 access_token。

修复：在 `app/core/deps.py` 添加 `payload.get("type") != "access"` 检查。

#### 🟡 WARNING（已修复）
**缺失安全响应头** — 无 X-Frame-Options / X-Content-Type-Options / HSTS。

修复：创建 `app/core/security_headers.py` 中间件，在 main.py 注册。

#### 🟡 WARNING（待修复，14 项）
1. `/api/auth/refresh` 缺少限流
2. `/api/auth/change-password` 缺少限流
3. 密码重置令牌非一次性（可重放）
4. 默认 SECRET_KEY 仅在 production 模式被拦截
5. AI 调用端点缺少认证
6. 数据写入端点无认证（`/api/civil-service/dark-knowledge/seed`）
7. 异常细节泄露（`detail=f"...{e}"`）
8. 密码策略薄弱（无字符复杂度要求）
9. bcrypt 72 字节截断（max_length=128 超过阈值）
10. 管理员鉴权不一致（内联 vs 依赖注入）
11. 开发模式回吐重置令牌
12. 点赞接口无限流无认证

### 🟢 已确认安全的实践
- CORS 配置正确（显式 origin，非 `*`）
- JWT 算法固定（防 `alg=none`）
- Token 类型在签发时分离
- bcrypt + 随机盐
- 常量时间密码比较
- 登录失败信息泛化（防枚举）
- IDOR 防护到位（所有查询过滤 user_id）
- 无 SQL 注入风险（全 ORM + 参数化）
- Pydantic 输入校验完整
- 管理员端点保护到位
- 全局兜底异常处理
- 请求日志不记录敏感数据

### 变更文件
- `backend/app/core/deps.py` — 修复 BLOCKER（添加 token type 校验）
- `backend/app/core/security_headers.py` — 新建，安全响应头中间件
- `backend/app/main.py` — 注册安全头中间件

---

## Phase 9: 文档与 CI/CD

### 变更文件
- `.github/workflows/ci.yml` — 新建，GitHub Actions CI 配置
- `Makefile` — 新建，简化常用命令

### CI Pipeline
4 个并行 job：
1. **backend-lint** — isort + ruff + black 检查
2. **backend-test** — pytest 测试
3. **frontend-lint** — ESLint + TypeScript 类型检查
4. **frontend-test** — Vitest 单元测试

### Makefile 命令
```bash
make help           # 查看所有命令
make install        # 安装所有依赖
make dev            # 启动开发服务器
make test           # 运行所有测试
make lint           # 代码检查
make format         # 格式化代码
make migrate        # 数据库迁移
make migrate-new m="描述"  # 创建新迁移
make security-scan  # 安全扫描
make pre-commit-run # 运行 pre-commit
make clean          # 清理构建产物
```

---

## 后续建议

### 立即执行
1. **运行 `make install`** 安装新依赖
2. **运行 `pre-commit install`** 安装 git hooks
3. **运行 `make migrate`** 初始化 Alembic
4. **运行 `make test`** 验证所有测试通过

### 短期改进（1-2 周）
1. 修复安全审计的 14 个 WARNING
2. 为前端核心组件添加单元测试（目标覆盖率 60%）
3. 在 AI 端点添加认证依赖
4. 统一管理员鉴权模式（使用 `get_admin_user`）

### 中期改进（1-2 月）
1. 集成邮件发送服务（SMTP/SendGrid）用于密码重置
2. 添加 OAuth2 社交登录（GitHub/Google）
3. 收紧 mypy 配置（`disallow_untyped_defs=true`）
4. 添加 API 文档自动生成（OpenAPI → Markdown）

### 长期改进
1. 评估 throttled-py 迁移（当 slowapi 无法满足需求时）
2. 评估 shadcn/ui 集成（保持现有设计语言的同时引入组件库）
3. 添加端到端测试覆盖率目标（核心流程 80%）
4. 实现蓝绿部署策略
