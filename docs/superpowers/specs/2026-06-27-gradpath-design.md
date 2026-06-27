# GradPath（职径）— 个人职业轨迹一体化平台设计文档

> **项目代号**：GradPath / 职径
> **创建日期**：2026-06-27
> **阶段**：Phase 1 MVP 设计
> **状态**：待实现

---

## 1. 项目概述

### 1.1 一句话定义

GradPath 是一个面向大学生/研究生的**个人职业轨迹记录与复盘平台**，将"毕业去向决策"与"职业成长记录"串联在同一条时间线上，帮助用户回答三个核心问题：**我走到哪了、我学到了什么、下一步往哪走**。

### 1.2 为什么做这个（基于调研发现的空白）

深度调研 GitHub 上 6 个优先级项目后，发现两个方向存在共同的核心空白：

| 现有项目 | 覆盖的切面 | 缺失的能力 |
|---------|-----------|-----------|
| `6.eta_system` | 群体定量分流统计（城市/单位/专业/回归预测） | 无个人成长记录、无现代前端、去向类型枚举不全 |
| `classmate-map` | 毕业去向地图可视化（社交蹭饭） | 无任何分流统计、无职业记录 |
| `ic-guide` | 科研方向毕业去向定性导览 | 无结构化数据、无定量分析 |
| `developer-roadmap` | 公共技能图谱（355K stars） | 无个人成长记录、无阶段链 |
| `Career_planning_path` | 1000+ 他人职业案例 | 完全无结构化数据、无路径建模 |
| `career-ops` | 单次 offer 评估+面试准备 | 无长期成长记录、无职业路径规划 |

**没有任何项目实现"个人化、持续性的职业成长记录与阶段性复盘"**，也没有项目把毕业去向决策与职业发展总结整合成一体化平台。这正是 GradPath 的价值锚点。

### 1.3 核心设计原则

1. **个人优先**：数据归属用户，隐私至上；群体参考数据通过接口预留，Phase 2-3 接入
2. **时间线串联**：去向决策是时间线的起点事件，职业成长是持续事件，复盘是阶段节点
3. **结构化优先**：所有数据字段化、可聚合、可可视化（吸取 `6.eta_system` 的教训 vs `Career_planning_path` 的纯文本）
4. **接口预留**：数据模型从一开始为"参考数据对比"留好接口，后续子系统无缝插入
5. **YAGNI**：Phase 1 不做报告抓取、不做社区聚合、不做 AI，专注个人轨迹核心价值

---

## 2. 目标用户与核心场景

### 2.1 目标用户

**主要**：大学生/研究生（毕业前做去向决策）与应届/初入职场者（记录早期职业成长）

**用户画像**：
- 即将毕业的学生，面临"考研/就业/考公/出国/读博"的分流决策，希望记录决策过程与理由
- 已毕业 1-3 年的职场新人，希望系统化记录成长轨迹、做阶段性复盘

### 2.2 核心场景（用户旅程）

```
毕业前夕                      毕业后持续
    │                            │
    ▼                            ▼
[去向决策记录] ──时间线──▶ [职业成长事件] ──阶段节点──▶ [复盘总结]
    │                            │                        │
    │                            │                        │
    ▼                            ▼                        ▼
记录决策类型/理由/          记录入职/晋升/技能/         年度/季度复盘：
信心度，预留参考数据         项目/考证等事件，附          成就/挑战/教训/
对比接口                   反思（STAR+R 范式）          下一步规划
```

**场景 1：毕业去向决策记录**
用户小李，研三，正在纠结考研 vs 就业。在平台上创建一条"去向决策"记录，选择类型（就业），填写目标公司/城市/岗位，写下决策理由与信心度。系统预留"参考数据快照"字段，Phase 2 接入后可对比"同专业同校的人去了哪"。

**场景 2：职业成长时间线**
用户小王，毕业 2 年。入职后持续记录职业事件：第一次晋升、完成的核心项目、习得的新技能、考到的证书。每个事件可附反思（参考 career-ops 的 STAR+R 范式）。

**场景 3：阶段性复盘**
年底，用户做年度复盘：回顾本年成就与挑战、提炼教训、规划明年方向。系统聚合该时间段内的所有事件，辅助生成复盘。

---

## 3. 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Next.js 14)                      │
│  ┌──────────┬──────────┬──────────┬──────────┬────────┐ │
│  │ 去向决策  │ 成长时间线│ 技能树   │ 阶段复盘 │ 个人看板│ │
│  │ 模块     │ 模块     │ 模块     │ 模块     │ 模块   │ │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴───┬────┘ │
│       └──────────┴──────────┴──────────┴─────────┘      │
│                      Zustand State                       │
└────────────────────────────┬────────────────────────────┘
                             │ REST API (JSON)
┌────────────────────────────┴────────────────────────────┐
│                  后端 (FastAPI + Python)                  │
│  ┌──────────┬──────────┬──────────┬──────────┬────────┐ │
│  │ Auth     │ Decision │ Event    │ Skill    │ Retro   │ │
│  │ Service  │ Service  │ Service  │ Service  │ Service │ │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴───┬────┘ │
│       └──────────┴──────────┴──────────┴─────────┘      │
│                    SQLAlchemy ORM                        │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────┐
│                   PostgreSQL 数据库                       │
│  users │ destination_decisions │ career_events │         │
│  skill_nodes │ retrospectives │ reference_snapshots     │
└─────────────────────────────────────────────────────────┘
```

### 3.2 技术栈选型

| 层 | 技术 | 选型理由 |
|----|------|---------|
| 前端框架 | Next.js 14 (App Router) | 现代 SSG/SSR、生态丰富、适合数据可视化（借鉴 `careerpath_plat` 选型） |
| 前端语言 | TypeScript | 类型安全，借鉴 `developer-roadmap`（84.5% TS） |
| UI 组件 | Tailwind CSS + shadcn/ui | 现代、一致、开发效率高（借鉴 `developer-roadmap` Tailwind 4 迁移） |
| 图表库 | Recharts | React 原生、灵活、适合分流统计图表 |
| 地图库 | react-simple-maps | 轻量，为后续地域可视化预留 |
| 状态管理 | Zustand | 轻量，避免 Redux 样板代码 |
| 后端框架 | FastAPI (Python) | 异步、自动文档、擅长数据处理（为 Phase 2 报告抓取预留） |
| ORM | SQLAlchemy 2.0 + Alembic | 成熟、类型提示、迁移管理 |
| 数据库 | PostgreSQL | 关系型+JSONB，适合结构化轨迹+半结构化详情 |
| 认证 | JWT (python-jose) | 无状态、简单，适合个人应用 |
| 测试（后端） | pytest | Python 标准 |
| 测试（前端） | Vitest + Playwright | 单元+E2E |
| 包管理 | pnpm (前端) + uv/pip (后端) | 现代包管理 |

### 3.3 目录结构

```
gradpath/
├── docs/                          # 文档
│   └── superpowers/
│       ├── specs/                 # 设计文档
│       └── plans/                 # 实现计划
├── backend/                       # FastAPI 后端
│   ├── app/
│   │   ├── main.py                # 应用入口
│   │   ├── config.py              # 配置
│   │   ├── database.py            # 数据库连接
│   │   ├── models/                # SQLAlchemy 模型
│   │   │   ├── user.py
│   │   │   ├── destination_decision.py
│   │   │   ├── career_event.py
│   │   │   ├── skill_node.py
│   │   │   ├── retrospective.py
│   │   │   └── reference_snapshot.py
│   │   ├── schemas/               # Pydantic 请求/响应模型
│   │   ├── api/                   # 路由
│   │   │   ├── auth.py
│   │   │   ├── decisions.py
│   │   │   ├── events.py
│   │   │   ├── skills.py
│   │   │   ├── retrospectives.py
│   │   │   └── dashboard.py
│   │   ├── services/              # 业务逻辑
│   │   └── core/                  # 安全、依赖注入
│   ├── alembic/                   # 数据库迁移
│   ├── tests/                     # pytest 测试
│   └── pyproject.toml
├── frontend/                      # Next.js 前端
│   ├── src/
│   │   ├── app/                   # App Router 页面
│   │   │   ├── (auth)/            # 登录注册
│   │   │   ├── dashboard/         # 个人看板
│   │   │   ├── decisions/         # 去向决策
│   │   │   ├── timeline/          # 成长时间线
│   │   │   ├── skills/            # 技能树
│   │   │   └── retrospectives/    # 阶段复盘
│   │   ├── components/            # 组件
│   │   ├── lib/                   # API 客户端、工具
│   │   ├── stores/                # Zustand stores
│   │   └── types/                 # TS 类型
│   ├── package.json
│   └── tsconfig.json
└── docker-compose.yml             # 本地开发环境
```

---

## 4. 数据模型

### 4.1 设计依据

数据模型综合借鉴三个项目：
- `6.eta_system` 的 `WorkRegister`：字段化、字典枚举、多维度——但扩展去向类型枚举（补齐考公/出国/读博）
- `career-ops` 的 STAR+R 故事库：在职业事件中加入 Reflection 列
- `developer-roadmap` 的技能 DAG：技能节点支持父子关系，形成个人技能树

### 4.2 核心实体

#### 4.2.1 User（用户）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| email | String unique | 登录邮箱 |
| password_hash | String | bcrypt 哈希 |
| name | String | 昵称 |
| current_stage | Enum | 当前阶段：student / graduating / early_career / experienced |
| school | String nullable | 学校 |
| major | String nullable | 专业 |
| graduation_year | Int nullable | 毕业年份 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### 4.2.2 DestinationDecision（去向决策记录）— 核心

借鉴 `6.eta_system` 的 WorkRegister，扩展去向类型枚举。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| user_id | UUID FK | 关联用户 |
| decision_date | Date | 决策日期 |
| destination_type | Enum | **去向类型**：employment / postgrad / civil_service / abroad / phd / startup / gap_year |
| status | Enum | planned / confirmed / executed / changed |
| details | JSONB | **按类型存储详情**（见 4.2.3） |
| reasoning | Text | 决策理由 |
| confidence | Int (1-5) | 决策信心度 |
| reference_snapshot_id | UUID FK nullable | **预留**：关联参考数据快照（Phase 2-3） |
| created_at | DateTime | |
| updated_at | DateTime | |

#### 4.2.3 DestinationDecision.details（JSONB 按类型结构）

```jsonc
// employment（就业）
{
  "company": "腾讯",
  "position": "后端开发工程师",
  "city": "深圳",
  "salary_range": "25-30k",
  "company_nature": "民企"  // 国企/民企/外企/事业单位
}

// postgrad（考研）
{
  "target_school": "清华大学",
  "target_major": "计算机科学与技术",
  "result": "pending"  // pending / admitted / rejected
}

// civil_service（考公）
{
  "agency": "国家税务总局",
  "position": "科员",
  "level": "central"  // central / provincial / municipal
}

// abroad（出国）
{
  "country": "美国",
  "school": "Stanford University",
  "program": "MSCS",
  "degree": "master"  // master / phd
}

// phd（读博）
{
  "school": "北京大学",
  "advisor": "张教授",
  "field": "人工智能"
}

// startup（创业）
{
  "company_name": "...",
  "role": "创始人",
  "field": "..."
}

// gap_year（间隔年）
{
  "plan": "..."  // 自由文本
}
```

#### 4.2.4 CareerEvent（职业成长事件）

借鉴 `career-ops` 的 STAR+R 范式。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| user_id | UUID FK | 关联用户 |
| event_date | Date | 事件日期 |
| event_type | Enum | onboard / leave / promotion / transfer / skill_acquired / project_done / certification / other |
| title | String | 事件标题 |
| description | Text | 事件描述 |
| situation | Text nullable | STAR - 情境 |
| task | Text nullable | STAR - 任务 |
| action | Text nullable | STAR - 行动 |
| result | Text nullable | STAR - 结果 |
| reflection | Text nullable | **R - 反思**（区分资深度，借鉴 career-ops） |
| skills_gained | JSONB (array) | 习得技能名数组 |
| impact_metrics | JSONB nullable | 量化影响（如 {"revenue": "+20%"}） |
| mood | Int (1-5) nullable | 心情 |
| created_at | DateTime | |
| updated_at | DateTime | |

#### 4.2.5 SkillNode（技能节点）

借鉴 `developer-roadmap` 的技能 DAG 概念，个人化。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| user_id | UUID FK | 关联用户 |
| name | String | 技能名 |
| category | String | 分类（如 "后端"、"前端"、"软技能"） |
| level | Int (1-5) | 掌握程度 |
| parent_id | UUID FK nullable | 父技能（形成树） |
| acquired_date | Date nullable | 习得日期 |
| evidence_event_id | UUID FK nullable | 关联的 CareerEvent（证据） |
| notes | Text nullable | 备注 |
| created_at | DateTime | |
| updated_at | DateTime | |

#### 4.2.6 Retrospective（阶段性复盘）

借鉴 `career-ops` 的分层准备理念，用于个人复盘。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| user_id | UUID FK | 关联用户 |
| period_type | Enum | annual / quarterly / project / custom |
| period_start | Date | 复盘开始 |
| period_end | Date | 复盘结束 |
| title | String | 复盘标题 |
| achievements | JSONB (array) | 成就列表 |
| challenges | Text | 挑战 |
| lessons_learned | Text | 教训提炼 |
| next_steps | JSONB (array) | 下一步规划 |
| satisfaction | Int (1-5) | 满意度 |
| created_at | DateTime | |
| updated_at | DateTime | |

#### 4.2.7 ReferenceSnapshot（参考数据快照）— 预留

为 Phase 2-3 预留的接口，Phase 1 表存在但无数据写入。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| user_id | UUID FK nullable | 关联用户（可空，表示公共快照） |
| snapshot_date | DateTime | 快照时间 |
| source_type | Enum | report / community |
| query_params | JSONB | 查询参数（如 {"major": "CS", "school": "THU"}） |
| data | JSONB | 结构化分流统计（如 {"employment": 0.4, "postgrad": 0.3, ...}） |
| created_at | DateTime | |

### 4.3 实体关系

```
User 1───∞ DestinationDecision
User 1───∞ CareerEvent
User 1───∞ SkillNode (self-ref via parent_id)
User 1───∞ Retrospective
User 1───∞ ReferenceSnapshot
DestinationDecision ∞───1 ReferenceSnapshot (optional)
CareerEvent 1───1 SkillNode (via evidence_event_id, optional)
```

---

## 5. 核心功能模块（Phase 1）

### 5.1 用户认证模块

- 注册：email + password
- 登录：JWT 签发（access token + refresh token）
- 当前用户信息：GET /api/auth/me
- 密码 bcrypt 哈希存储

### 5.2 去向决策模块

- 创建决策记录：POST /api/decisions
- 查询我的决策列表：GET /api/decisions（按时间倒序）
- 查询单条：GET /api/decisions/{id}
- 更新：PATCH /api/decisions/{id}
- 删除：DELETE /api/decisions/{id}
- 去向类型分布统计：GET /api/decisions/stats（个人历史决策的类型分布饼图数据）

前端：
- 决策记录表单（按 destination_type 动态渲染详情字段）
- 决策历史列表卡片
- 去向类型分布饼图（Recharts）

### 5.3 职业成长时间线模块

- 创建事件：POST /api/events
- 查询我的事件列表：GET /api/events（支持按时间范围、类型筛选）
- 更新/删除
- 时间线可视化：按时间倒序的卡片流，支持类型筛选

前端：
- 事件创建表单（含 STAR+R 可选字段折叠区）
- 时间线卡片组件（突出 reflection）
- 按事件类型筛选的 Tab

### 5.4 技能树模块

- 创建技能节点：POST /api/skills
- 查询我的技能树：GET /api/skills（返回树形结构）
- 更新/删除
- 技能分类统计：GET /api/skills/stats（按 category 聚合，雷达图数据）

前端：
- 技能树可视化（树形图，节点大小/颜色表示 level）
- 技能雷达图（按 category）
- 技能 CRUD 弹窗

### 5.5 阶段复盘模块

- 创建复盘：POST /api/retrospectives
- 查询复盘列表：GET /api/retrospectives
- 更新/删除
- 自动聚合：GET /api/retrospectives/draft?period_start=&period_end=（返回该时间段内的 CareerEvent 摘要，辅助生成复盘草稿）

前端：
- 复盘表单（achievements/next_steps 为动态列表）
- 复盘列表卡片
- "生成草稿"按钮：基于时间段内事件自动填充 achievements 摘要

### 5.6 个人看板模块

- GET /api/dashboard/overview：聚合数据
  - 去向决策总数、最新决策
  - 事件总数、最近 5 条事件
  - 技能总数、按分类计数
  - 复盘总数、最近一次复盘
  - 职业旅程时间线（决策+事件合并按时间排序）

前端：
- 看板首页：统计卡片 + 时间线总览 + 技能雷达图缩略
- 空状态引导（新用户引导创建第一条决策/事件）

---

## 6. API 设计概要

所有 API 遵循 RESTful，前缀 `/api`，除注册/登录外均需 JWT 认证。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 注册 |
| POST | /api/auth/login | 登录 |
| GET | /api/auth/me | 当前用户 |
| GET/POST | /api/decisions | 决策列表/创建 |
| GET/PATCH/DELETE | /api/decisions/{id} | 决策详情/更新/删除 |
| GET | /api/decisions/stats | 决策类型分布 |
| GET/POST | /api/events | 事件列表/创建 |
| GET/PATCH/DELETE | /api/events/{id} | 事件 CRUD |
| GET/POST | /api/skills | 技能列表/创建 |
| GET/PATCH/DELETE | /api/skills/{id} | 技能 CRUD |
| GET | /api/skills/stats | 技能分类统计 |
| GET/POST | /api/retrospectives | 复盘列表/创建 |
| GET/PATCH/DELETE | /api/retrospectives/{id} | 复盘 CRUD |
| GET | /api/retrospectives/draft | 复盘草稿生成 |
| GET | /api/dashboard/overview | 看板聚合 |

---

## 7. 分阶段路线图

| 阶段 | 名称 | 核心交付 | 依赖 |
|------|------|---------|------|
| **Phase 1** | 个人轨迹记录器（本规格） | 认证 + 去向决策 + 成长时间线 + 技能树 + 复盘 + 看板 | 无 |
| Phase 2 | 公开报告数据管道 | 高校就业质量报告抓取/解析/结构化存储 + 参考数据注入决策模块 | Phase 1 |
| Phase 3 | 社区聚合参考 | 用户脱敏数据聚合 + "同类人去了哪"参考分析 | Phase 1 用户数据 |
| Phase 4 | AI 辅助分析 | AI 复盘助手 + 决策建议 + 成长洞察 | Phase 1 数据 |

---

## 8. 测试策略

### 8.1 测试金字塔

- **80% 单元测试**：Service 层业务逻辑、模型校验、工具函数
- **15% 集成测试**：API 端到端（TestClient + 测试数据库）
- **5% E2E 测试**：关键用户流程（Playwright）

### 8.2 关键测试用例

- 认证：注册、登录、token 过期、未授权访问拒绝
- 去向决策：7 种 destination_type 的详情结构校验、状态流转、统计聚合
- 职业事件：STAR+R 字段可选、时间范围筛选、技能关联
- 技能树：父子关系、循环引用检测、树形序列化
- 复盘：草稿生成的时间范围聚合、动态列表字段
- 看板：空状态、聚合数据正确性

### 8.3 测试纪律

遵循 TDD：RED（写失败测试）→ GREEN（最小实现）→ REFACTOR（重构）→ COMMIT（提交）。

---

## 9. 错误处理

- API 统一错误响应格式：`{"error": {"code": "...", "message": "...", "details": {...}}}`
- HTTP 状态码：400 校验错误、401 未认证、403 无权限、404 不存在、409 冲突、500 服务器错误
- 前端：API 客户端统一拦截错误，Toast 提示
- 数据库：唯一约束冲突、外键约束的事务回滚

---

## 10. 非功能性要求

- **安全**：密码 bcrypt、JWT 过期（access 30min / refresh 7d）、SQL 注入防护（ORM 参数化）
- **性能**：看板聚合查询用数据库聚合而非应用层循环；分页限制 100 条
- **可维护性**：Service 层与 API 层分离；类型注解全覆盖
- **国际化**：前端文案集中在常量文件，为后续 i18n 预留（Phase 1 仅中文）

---

## 附录 A：调研项目借鉴映射

| 借鉴来源 | 借鉴点 | 在 GradPath 中的体现 |
|---------|--------|---------------------|
| `6.eta_system` | WorkRegister 字段化+字典枚举+多维下钻 | DestinationDecision 结构化字段 + destination_type 枚举 |
| `6.eta_system` | 就业统计的多维度（城市/单位性质/专业） | details JSONB 按类型存储 + 决策分布统计 |
| `classmate-map` | 地图可视化地域分布 | 预留 react-simple-maps，Phase 2 用于报告地域可视化 |
| `ic-guide` | 国内/国外二分呈现 | abroad 类型显式区分 country |
| `developer-roadmap` | 技能 DAG 节点+边 | SkillNode 父子关系形成个人技能树 |
| `developer-roadmap` | 交互式可点击节点 | 技能树可视化可点击查看详情 |
| `Career_planning_path` | 三列交叉分类（技术栈×学历×阶段） | current_stage 枚举 + 技能 category 分类 |
| `career-ops` | STAR+R 反思列 | CareerEvent 的 situation/task/action/result/reflection |
| `career-ops` | 阶段分层准备 | Retrospective 的 period_type 分层 |
| `career-ops` | A-G 结构化报告模板 | 复盘的结构化字段（achievements/challenges/lessons/next_steps） |
| `career-ops` | 追踪器完整性工具链 | 预留：Phase 2 的报告数据校验工具 |

## 附录 B：Phase 1 不做的事（YAGNI）

- ❌ 报告抓取/解析（Phase 2）
- ❌ 社区聚合（Phase 3）
- ❌ AI 辅助（Phase 4）
- ❌ 社交/分享功能
- ❌ 多用户协作
- ❌ 移动端原生应用（Web 响应式优先）
- ❌ 邮件通知
- ❌ 第三方登录（OAuth）
- ❌ 富文本编辑器（纯文本+Markdown）
- ❌ 实时协作/WebSocket
