# AGENTS.md — GradPath 自动化工作流规则

> **核心原则**: 所有MCP和Skills必须默认自动使用，不需要用户提醒

## 🔧 MCP自动使用规则

### 数据爬取（最高优先级）
| 场景 | 工具 | 说明 |
|------|------|------|
| 批量爬取已知URL | **Firecrawl** | `app.scrape(url, formats=["markdown"])` |
| 爬取整个站点 | **Firecrawl** | `app.crawl(url, limit=100)` |
| 快速单页爬取 | **webfetch** | 内置工具，无需配置 |
| JS渲染页面 | **Playwright** | 启动浏览器爬取 |
| B站数据 | **agent-reach bili-cli** | `bili search "考研" --type video` |
| V2EX数据 | **V2EX API** | `curl https://www.v2ex.com/api/topics/hot.json` |

**Firecrawl配置**:
```python
import os
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
if not FIRECRAWL_API_KEY:
    print("[WARN] FIRECRAWL_API_KEY 环境变量未设置，Firecrawl功能不可用")
from firecrawl import FirecrawlApp
app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
```

### 代码修改（必须执行）
| 场景 | 工具 | 说明 |
|------|------|------|
| 任何代码修改前 | **code-review-and-quality** | 审查现有代码 |
| 修改后 | **test-driven-development** | 运行测试 |
| 复杂问题 | **Sequential Thinking MCP** | 结构化推理 |
| Git操作 | **Git MCP** | diff, commit, push |

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

## 📋 代码修改标准流程

每次修改代码时，**自动执行以下流程**：

```
1. Sequential Thinking → 分析问题（如复杂）
2. code-review → 审查现有代码
3. 编写代码 → following existing patterns
4. test-driven-development → 运行测试
5. performance-optimization → 检查性能
6. security-and-hardening → 检查安全
7. git-workflow → 提交代码
```

## 🎯 默认行为

### 爬取数据时
- 自动使用Firecrawl（有API key）
- 自动使用Playwright处理JS渲染页面
- 自动使用webfetch作为备用
- 自动保存到 `backend/app/crawlers/real_data/`
- 自动导入数据库

### 修改代码时
- 自动应用code-review-and-quality
- 自动应用performance-optimization
- 自动应用security-and-hardening
- 自动运行测试
- 自动检查Docker容器状态

### 调试问题时
- 自动使用Sequential Thinking（复杂问题）
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

| 表名 | 说明 | 当前数据量 |
|------|------|-----------|
| experience_posts | 经验帖 | 588 |
| knowledge_articles | 知识文章 | 82 |
| schools | 院校 | 206 |
| qas | 问答 | 290 |
| qa_answers | 回答 | 646 |
| dark_knowledge | 暗知识 | 1020 |
| grad_school_intel | 院校情报 | 498 |
| grad_scoreline_records | 分数线 | 408 |
| companies | 公司 | 466 |
| salary_benchmarks | 薪资基准 | 2880 |

## 🔑 关键配置

| 配置 | 值 |
|------|-----|
| 后端端口 | 8001 |
| 前端端口 | 3000 |
| Docker项目名 | gradpath |
| 测试账号 | 测试账号凭据请参考 .env.example 或联系管理员 |
| Firecrawl API Key | 通过环境变量 FIRECRAWL_API_KEY 配置 |
| Python版本 | 3.11 |
| Node版本 | v24.15.0 |

## ⚠️ 已知问题

1. 端口 8000 被 ai-goofish 占用，后端宿主端口用 8001（容器内仍监听 8000，宿主映射 `127.0.0.1:8001:8000`）；前端通过 `next.config.js` rewrites 走 `/api/*` 同源代理访问后端，客户端无需也禁止硬编码后端地址
2. Firecrawl免费额度有限，每次约75页
3. seed_kaoyan_community.py需要重建（之前被损坏）
4. web-vitals包需要在容器中安装

## 📝 用户指令

1. **"碰到难题用Sequential Thinking MCP思考"** — 必须遵守
2. **"所有skill和mcp默认接入"** — 本文件定义规则
3. **"打破信息差，数据要真实"** — 使用Firecrawl爬取真实数据
