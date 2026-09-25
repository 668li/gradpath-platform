# AGENTS.md — GradPath 自动化工作流规则

> **核心原则**: 已接入的 MCP 与 Skills 默认自动使用，无需用户提醒；下表标注〔未接入 MCP〕的条目当前未接入本工作区，按其「替代」列执行即可，不视为缺失

## 🤝 协作准则 — 首席工作伙伴

你是我的首席工作伙伴。主动补全遗漏、发现问题、探索可能性，帮助我形成判断并推进工作。根据任务选择合适的方法与深度，不机械套用固定流程。

1. **独立判断**：不要迎合。不同意时直接说明理由、依据和替代建议；发现目标本身可能有问题时，也应提出讨论。
2. **充分澄清**：目标模糊、关键条件缺失或存在重要取舍时，主动追问，直到足以可靠推进。能自行查证的信息先查证，不重复询问已知内容，也不为了提问而提问。
3. **主动补全**：不局限于字面要求，指出我未考虑的重要需求、风险和机会。区分必要工作与额外建议；改变目标或扩大授权范围前，与我对齐。
4. **灵活探索**：按需要分析、比较、验证或提出新思路。简单问题直接处理，复杂问题深入讨论，不固定问题数量、方案数量或回答长度。
5. **诚实可靠**：区分事实、推测和建议，说明重要的不确定性。不编造信息、能力或完成状态；能验证的关键结论尽量验证。
6. **持续推进**：明确且已授权的工作，推进到完成。未经授权的付款、对外发送、发布或永久删除，先准备可审阅内容再确认；遇到阻塞时说明原因和解决办法。
7. **清晰交付与纠错**：结论先行，提供理解和判断所需的依据，不堆砌形式。发现错误及时修正；历史经验按场景使用，不把一次纠正变成永久规则。

## 🔧 MCP自动使用规则

### 数据爬取（最高优先级）

> 约定：**〔未接入 MCP〕** = 该工具当前未作为 MCP 服务接入本工作区，直接走「替代」列（均已实测可用）；若日后接入，则优先用原始工具。

| 场景 | 优先工具 → 替代（当前生效） | 说明 |
|------|------|------|
| 批量爬取已知URL | 〔未接入〕**Firecrawl** → **WebFetch** / **browser-use MCP** | 单页 `WebFetch(url, query)` 内置；需登录态/交互走 browser-use |
| 爬取整个站点 | 〔未接入〕**Firecrawl** → **agent-reach** / **scrapling** skill | 整站遍历交给已接入的爬取 skill 路由 |
| 快速单页爬取 | **WebFetch**（内置，已接入 ✓） | 无需配置 |
| JS渲染页面 | 〔未接入〕**Playwright MCP** → **browser-use MCP（已接入 ✓）** | 用 browser-use 驱动真实浏览器渲染 |
| B站数据 | **agent-reach bili-cli** skill ✓ | `bili search "考研" --type video` |
| V2EX数据 | **V2EX API**（Bash `curl`，已接入 ✓） | `curl https://www.v2ex.com/api/topics/hot.json` |
| 数据库查询 | 〔未接入〕**SQLite MCP** → **Python `sqlite3` via Bash ✓** | `py -3.13 -c "import sqlite3; ..."`（本机 SQLite 3.50.4，无 sqlite3 CLI）；本地 `gradpath.db` 为 0 字节空库，权威数据以生产库为准（见「数据库表」节） |
| 库API用法不确定 | 〔未接入〕**Context7 MCP** → **WebSearch / WebFetch ✓** | 检索 FastAPI/React/依赖库官方文档与示例，防旧 API 幻觉 |

**Firecrawl 配置（可选，仅在其作为 MCP/API 接入后使用）**:
凭据只走环境变量 `FIRECRAWL_API_KEY`，禁止把明文 Key 写入本文件等被跟踪文件；未设置时自动改用上方替代方案。

### 代码修改（必须执行）
| 场景 | 工具 | 说明 |
|------|------|------|
| 任何代码修改前 | **code-review-and-quality** skill ✓ | 审查现有代码 |
| 修改后 | **test-driven-development** skill ✓ | 运行测试 |
| 复杂问题 | 〔未接入〕**Sequential Thinking MCP** → **原生分步推理** / **planning-and-task-breakdown** skill | 结构化推理 |
| Git操作 | 〔未接入〕**Git MCP** → **`git` CLI via Bash ✓**（本机 v2.53）/ **github(gh)** skill | diff, commit, push |

### 性能和安全（每次修改检查）
| 场景 | 工具 | 说明 |
|------|------|------|
| API端点修改 | **performance-optimization** | 检查N+1、缓存 |
| 敏感数据处理 | **security-and-hardening** | 检查SQL注入、XSS |
| 前端修改 | **frontend-ui-engineering** | UI规范、可访问性 |
| 部署相关 | **shipping-and-launch** | 发布检查清单 |

### 测试（每次修改后必须）
| 场景 | 工具 | 说明 |
|------|------|------|
| 后端修改 | `docker exec gradpath-backend-1 python -m pytest tests/ -q` | 运行后端测试 |
| 前端修改 | Playwright E2E测试 | `tests/test_e2e_full.py` |
| API测试 | curl测试端点 | 验证响应 |
| 后端回归（项目惯例） | `cd backend && py -3.13 -m pytest`（本地实测口径，行数级证据报 passed/failed） | 全绿才交付 |

## 📋 代码修改标准流程

每次修改代码时，**自动执行以下流程**：

```
1. 复杂问题 → 原生分步推理（若已接入 Sequential Thinking MCP 则优先）分析问题
2. code-review → 审查现有代码
3. 编写代码 → following existing patterns
4. test-driven-development → 运行测试
5. performance-optimization → 检查性能
6. security-and-hardening → 检查安全
7. git-workflow → 提交代码
```

## 🎯 默认行为

### 爬取数据时
- Firecrawl / Playwright MCP 若已接入则优先；当前未接入，改用 **browser-use MCP / WebFetch / agent-reach** 等已接入能力
- 快速单页用 **WebFetch**（内置）
- 自动保存到 `backend/app/crawlers/real_data/`
- 自动导入数据库

### 修改代码时
- 自动应用code-review-and-quality
- 自动应用performance-optimization
- 自动应用security-and-hardening
- 自动运行测试
- 自动检查Docker容器状态

### 调试问题时
- 复杂问题做原生分步推理（Sequential Thinking MCP 若已接入则优先）
- 自动使用debugging-and-error-recovery
- 自动检查日志：`docker logs gradpath-backend-1`

## 🏗️ GradPath架构

```
D:\职业规划\职业规划\
├── backend/                    # FastAPI后端 (port 8001)
│   ├── app/
│   │   ├── api/               # API路由
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务逻辑
│   │   ├── crawlers/grad/     # 考研爬虫
│   │   ├── crawlers/real_data/ # 真实数据爬虫
│   │   └── seed/              # 种子数据
│   └── tests/                 # 测试
├── frontend/                   # Next.js前端 (port 3000)
│   ├── app/                   # 页面路由
│   ├── components/            # 组件
│   └── lib/                   # 工具库
├── n8n/                        # n8n工作流模板
└── docker-compose.yml          # Docker配置
```

## 📊 数据库表

> ⚠ 本表为**历史快照（2026-08 前）**，行数已不代表现状：本地 `gradpath.db` 与生产差异大，多数表已随"信息差伴随层"转向清空或下线（如 dark_knowledge 已全链拆除、模型仅作只读底座 0 行；mentors 表 0 行挂 drop 台账）。**权威现役数据以生产库实测为准**，不引用本表数字。

| 表名 | 说明 | 状态 |
|------|------|------|
| experience_posts / knowledge_articles / schools / qas | 社区与院校基础内容 | 部分保留（以生产实测为准） |
| dark_knowledge | 暗知识 | **已退役**（功能全链删除，模型留只读底座 0 行） |
| grad_school_intel / grad_scoreline_records | 院校情报/分数线 | 保留（溯源纪律；scoreline dev 140 行 / prod 0 行，2026-09-21 实测） |
| company_reviews / mentors | 公司评价/导师评价 | **已退役**（mentors 0 行挂 drop 台账） |

## 🔑 关键配置

| 配置 | 值 |
|------|-----|
| 后端端口 | 8001 |
| 前端端口 | 3000 |
| Docker项目名 | gradpath |
| 测试账号 | 测试账号凭据请参考 .env.example 或联系管理员 |
| Firecrawl API Key | 通过环境变量 FIRECRAWL_API_KEY 配置 |
| Python版本 | 3.13（`py -3.13`；实测口径，勿按 3.11 执行） |
| Node版本 | v24.15.0 |

## ⚠️ 已知问题

1. 端口 8000 被 ai-goofish 占用，后端宿主端口用 8001（容器内仍监听 8000，宿主映射 `127.0.0.1:8001:8000`）；前端通过 `next.config.js` rewrites 走 `/api/*` 同源代理访问后端，客户端无需也禁止硬编码后端地址
2. Firecrawl 若接入，免费额度有限（约 75 页/次）；未接入时走 browser-use / WebFetch / agent-reach
3. seed_kaoyan_community.py需要重建（之前被损坏）
4. web-vitals包需要在容器中安装

## 📝 用户指令

1. **"碰到难题做结构化分步推理"** — 必须遵守（可用则用 Sequential Thinking MCP，否则原生推理 / planning skill）
2. **"已接入的 skill 和 mcp 默认使用"** — 本文件按上表〔未接入 MCP〕约定标注缺失项及其替代
3. **"打破信息差，数据要真实"** — 用已接入的爬取能力（Firecrawl 若接入，否则 WebFetch/browser-use/agent-reach）获取真实数据

## 🏛️ 架构纪律(强制执行)

* 分层必须遵守 `router → service → repository → database`,禁止在 router 中写业务逻辑
* 数据模型变更必须走 Alembic 迁移,禁止手改表结构
* 新增 API 用 Pydantic v2 做输入校验,错误响应统一格式
* 前端组件按 `frontend/components/` 现有模式组织,不重复造轮子

## ✅ 测试纪律

* 新增/修改后端 API 必须配套 pytest 用例,`docker exec gradpath-backend-1 python -m pytest tests/ -q` 全绿才能交付
* 新增/修改前端页面必须跑 Playwright E2E(`tests/test_e2e_full.py`)
* 爬虫→入库→API→页面 的关键数据流,每次修改后做一次端到端冒烟

## 🎯 Git 纪律

* commit message 用 `feat:` / `fix:` / `refactor:` / `chore:` 前缀 + 中文简述
* 单次 commit 不超过 500 行;大改动拆多个 commit
* 禁止把数据库文件、爬取的大 JSON、运行日志 commit 进仓库
* **提交推送前必须 `pre-commit run --all-files` 全树过一遍**(与 CI 同 hook 同版本;只修报错文件会再红)。注意它会重排并行会话的未提交 WIP 文件——只 `git add` 自己的文件,WIP 被重排就 `git checkout -- <file>` 还原
* 并行会话期间:格式化→add→commit→push 在一条命令内原子完成,压缩工作区被覆盖的窗口

## 🌐 爬虫合规红线(不可违反)

* 只爬公开数据,尊重 `robots.txt`,控制请求频率,不绕验证码、不伪造身份、不撞登录
* 研招网/论坛数据遵守平台条款;采集数据仅用于本项目,不对外分发
* 优先用官方 API 或已接入的取数能力（WebFetch / V2EX API / browser-use；Firecrawl 若已接入），减少对目标站点直接压力
