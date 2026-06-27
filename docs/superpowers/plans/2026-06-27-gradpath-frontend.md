# GradPath 前端实现计划（Phase 1）

> **For agentic workers:** 按任务顺序执行，每个任务完成后验证构建通过。

**Goal:** 实现 GradPath 前端 Web 应用，连接后端 API，提供完整的用户交互界面。

**Architecture:** Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + Recharts + Zustand

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Recharts, Zustand, lucide-react

---

## 文件结构

```
frontend/
├── package.json
├── tsconfig.json
├── next.config.js
├── tailwind.config.ts
├── postcss.config.js
├── .env.local
├── src/
│   ├── app/
│   │   ├── layout.tsx              # 根布局
│   │   ├── page.tsx                # 首页（重定向到 dashboard 或 login）
│   │   ├── globals.css
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   ├── dashboard/page.tsx      # 个人看板
│   │   ├── decisions/page.tsx      # 去向决策
│   │   ├── timeline/page.tsx       # 成长时间线
│   │   ├── skills/page.tsx         # 技能树
│   │   └── retrospectives/page.tsx # 阶段复盘
│   ├── components/
│   │   ├── ui/                     # shadcn/ui 组件
│   │   ├── nav.tsx                 # 侧边导航
│   │   ├── stat-card.tsx           # 统计卡片
│   │   ├── decision-form.tsx       # 决策表单
│   │   ├── event-form.tsx          # 事件表单
│   │   ├── skill-form.tsx          # 技能表单
│   │   └── retro-form.tsx          # 复盘表单
│   ├── lib/
│   │   ├── api.ts                  # API 客户端
│   │   └── utils.ts                # 工具函数
│   ├── stores/
│   │   └── auth.ts                 # Zustand auth store
│   └── types/
│       └── index.ts                # TS 类型定义
```

---

## Task 1: 项目初始化

- 创建 Next.js 14 项目（App Router + TypeScript + Tailwind）
- 安装依赖：shadcn/ui, recharts, zustand, lucide-react
- 配置环境变量 API_BASE_URL=http://localhost:8000
- 创建 API 客户端（fetch wrapper with JWT）
- 创建 Zustand auth store
- 创建 TS 类型定义（与后端 schema 对齐）
- 验证 `npm run build` 通过

## Task 2: 布局与导航

- 根布局 + 全局 CSS
- 侧边导航组件（看板/去向决策/成长时间线/技能树/阶段复盘）
- 登录/注册页面
- 认证路由保护（未登录重定向到 /login）
- 首页重定向逻辑

## Task 3: 个人看板页面

- 统计卡片（决策数/事件数/技能数/复盘数）
- 职业旅程时间线（决策+事件合并，按时间倒序）
- 技能分类雷达图（Recharts RadarChart）
- 最近事件列表
- 空状态引导

## Task 4: 去向决策页面

- 决策列表（卡片式，按时间倒序）
- 创建决策表单（按 destination_type 动态渲染详情字段）
- 7 种去向类型的详情字段配置
- 去向类型分布饼图（Recharts PieChart）
- 编辑/删除操作

## Task 5: 成长时间线页面

- 事件列表（时间线卡片流，按时间倒序）
- 按事件类型筛选 Tab
- 创建事件表单（含 STAR+R 可折叠区域）
- 编辑/删除操作

## Task 6: 技能树页面

- 技能树展示（树形/分组列表）
- 技能雷达图（按 category 聚合）
- 创建/编辑技能弹窗
- 删除操作

## Task 7: 阶段复盘页面

- 复盘列表（卡片式）
- 创建复盘表单（achievements/next_steps 动态列表）
- "生成草稿"功能（基于时间段事件自动填充）
- 编辑/删除操作

## 验证

- `npm run build` 通过
- 启动前后端，手动验证关键流程
