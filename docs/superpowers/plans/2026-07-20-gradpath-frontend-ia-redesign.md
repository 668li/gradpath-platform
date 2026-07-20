# GradPath 前端信息架构重构 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将前端导航从 9 个入口重组为 7 个入口（决策中心 C位、情报中心合并三大方向、成长档案合并 8 工具），Dashboard 精简，零功能删除

**Architecture:** 导航组件 `nav.tsx` 重构 + 新增 3 个聚合页面（intel/decision-center/growth）+ Dashboard 精简 + 社区合并 + 个人中心增强。所有旧 URL 路径保持不变，仅改变导航入口指向

**Tech Stack:** Next.js 14 App Router, TypeScript, Tailwind CSS, lucide-react

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `components/nav.tsx` | 修改 | 导航入口重组（7 入口 + 新分组 + redirect） |
| `app/(app)/dashboard/page.tsx` | 修改 | 精简组件（保留 4 指标 + 决策副驾驶 + 快速入口） |
| `app/(app)/intel/page.tsx` | 新建 | 情报中心聚合页（5 Tab） |
| `app/(app)/intel/layout.tsx` | 新建 | 情报中心布局 |
| `app/(app)/decision-center/page.tsx` | 新建 | 决策中心聚合页（待决策/记录 Tab） |
| `app/(app)/decision-center/layout.tsx` | 新建 | 决策中心布局 |
| `app/(app)/growth/archive/page.tsx` | 新建 | 成长档案聚合页（6 Tab） |
| `app/(app)/growth/archive/layout.tsx` | 新建 | 成长档案布局 |
| `app/(app)/community/page.tsx` | 修改 | 添加方向专区 Tab |
| `app/(app)/profile/page.tsx` | 修改 | 添加诊断报告 + 成就 Tab |
| `app/(app)/career/page.tsx` | 修改 | 改为 301 redirect 到决策中心 |
| `app/(app)/onboarding/page.tsx` | 修改 | 完成后跳转改为个人中心 |
| `components/decision-copilot/` | 保留 | 现有组件不动，仅入口变 |

---

### Task 1: 导航重构（nav.tsx）

**Files:**
- Modify: `frontend/components/nav.tsx`

**改动内容：**
- 导航项从 9 个变为 7 个
- 分组从"方向/工具/互动/我的"变为"核心/成长/其他"
- 新增 3 个入口：决策中心、情报中心、成长档案
- 移除 4 个入口：考研中心、考公中心、就业中心、职业规划、职业诊断
- 保留 3 个入口：我的看板(改名)、社区、AI 对话(改名)
- 底部保留：通知、搜索、个人中心、退出登录

- [ ] **Step 1: 修改 nav.tsx 导航项定义**

```typescript
interface NavItem {
  href: string;
  label: string;
  icon: typeof GraduationCap;
  section?: string;
}

function getNavItems(): NavItem[] {
  const items: NavItem[] = [
    // 核心
    { href: "/dashboard", label: "我的看板", icon: LayoutDashboard, section: "核心" },
    { href: "/decision-center", label: "决策中心", icon: Target, section: "核心" },
    { href: "/intel", label: "情报中心", icon: Search, section: "核心" },
    // 成长
    { href: "/growth/archive", label: "成长档案", icon: TrendingUp, section: "成长" },
    { href: "/community", label: "社区", icon: Users, section: "成长" },
    { href: "/ai-butler", label: "AI 对话", icon: Bot, section: "成长" },
    // 其他
    { href: "/profile", label: "个人中心", icon: UserCircle, section: "其他" },
  ];
  return items;
}
```

- [ ] **Step 2: 更新 Import（替换/新增图标）**

```typescript
import {
  LayoutDashboard,
  Target,
  Search,
  TrendingUp,
  Users,
  Bot,
  UserCircle,
  Bell,
  LogOut,
  Menu,
  X,
  GraduationCap,
} from "lucide-react";
```

- [ ] **Step 3: 验证导航渲染**

Run: `cd frontend && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add frontend/components/nav.tsx
git commit -m "feat: 导航重构 — 7 入口 + 新分组（决策中心 C位/情报中心/成长档案）"
```

---

### Task 2: Dashboard 精简

**Files:**
- Modify: `frontend/app/(app)/dashboard/page.tsx`

**改动内容：**
- 保留：4 个关键指标卡片（连续打卡、待决策数、待办数、成长等级）
- 保留：决策副驾驶摘要（待决策事项列表 + 快速操作）
- 保留：快速入口（查公司、查薪资、写面经、发帖）
- 移除：技能雷达 → 外部链接到成长档案/技能树
- 移除：游戏化档案 → 外部链接到个人中心/成就
- 移除：每周回顾 → 外部链接到成长档案/回顾
- 移除：每日聚焦 → 外部链接到成长档案
- 移除：生活平衡轮快照 → 外部链接到成长档案/平衡轮
- 移除：暗知识流 → 外部链接到情报中心
- 移除：记忆事实 → 外部链接到个人中心
- 移除：审核队列 → 管理员权限判断后显示

- [ ] **Step 1: 清理 import，移除未使用的组件和 API**

```typescript
// 移除的 import：
// import { SkillRadar } from "@/components/charts";
// import { LevelProgress } from "@/components/gamification/level-progress";
// import {
//   PulseOverviewSection,
//   ActiveDecisionsSection,
//   ReviewQueueSection,
//   DarkKnowledgeFeedSection,
//   MemoryFactsSection,
// } from "@/components/decision-copilot";
```

- [ ] **Step 2: 精简 JSX，只保留 4 指标卡片 + 决策副驾驶 + 快速入口**

阅读现有 dashboard/page.tsx，找到 4 个 StatCard 块和决策副驾驶组件，保留它们。找到技能雷达、游戏化档案、每周回顾等组件 JSX 块，移除它们。

- [ ] **Step 3: 验证 tsc**

Run: `cd frontend && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 4: 验证 build**

Run: `cd frontend && npx next build`
Expected: 成功

- [ ] **Step 5: Commit**

```bash
git add frontend/app/(app)/dashboard/page.tsx
git commit -m "feat: Dashboard 精简 — 保留 4 指标+决策副驾驶+快速入口，移除 6 冗余组件"
```

---

### Task 3: 情报中心聚合页

**Files:**
- Create: `frontend/app/(app)/intel/layout.tsx`
- Create: `frontend/app/(app)/intel/page.tsx`

**改动内容：**
- 新建情报中心聚合页，5 个 Tab：考研、考公、就业、薪资、面经
- 每个 Tab 显示对应方向的核心信息卡片
- 点击 Tab 不跳转，直接切换内容区域

- [ ] **Step 1: 创建 layout.tsx**

```tsx
export default function IntelLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
```

- [ ] **Step 2: 创建情报中心页面**

```tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { GraduationCap, Landmark, Briefcase, DollarSign, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "kaoyan", label: "考研", icon: GraduationCap, href: "/kaoyan", desc: "院校情报、录取预测、导师评价、暗知识" },
  { id: "civil", label: "考公", icon: Landmark, href: "/civil-service", desc: "岗位情报、考公定位、暗知识" },
  { id: "career", label: "就业", icon: Briefcase, href: "/employment", desc: "公司情报、求职定位、就业数据" },
  { id: "salary", label: "薪资", icon: DollarSign, href: "/employment?tab=salary", desc: "各公司岗位薪资数据查询" },
  { id: "interview", label: "面经", icon: MessageSquare, href: "/interview", desc: "海量面试经验分享" },
];

export default function IntelPage() {
  const [activeTab, setActiveTab] = useState("kaoyan");

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-ink-800">情报中心</h1>
        <p className="text-ink-500 mt-1">查院校、查公司、查薪资、看面经，一站式获取决策所需信息</p>
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-2 mb-6 border-b border-paper-300 pb-2 overflow-x-auto">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 rounded-t-lg text-sm font-medium transition-colors whitespace-nowrap",
                activeTab === tab.id
                  ? "bg-white text-brand-600 border-b-2 border-brand-500"
                  : "text-ink-400 hover:text-ink-600 hover:bg-paper-200",
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab 内容 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {TABS.filter((t) => t.id === activeTab).map((tab) => (
          <Link
            key={tab.id}
            href={tab.href}
            className="col-span-full bg-white rounded-xl border border-paper-200 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2.5 rounded-lg bg-brand-50 text-brand-600">
                <tab.icon className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-semibold text-ink-800">{tab.label}</h2>
                <p className="text-sm text-ink-500">{tab.desc}</p>
              </div>
            </div>
            <p className="text-sm text-brand-600 font-medium mt-2">点击进入 {tab.label} 模块 →</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 验证 tsc**

Run: `cd frontend && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add frontend/app/(app)/intel/
git commit -m "feat: 情报中心聚合页 — 5 Tab（考研/考公/就业/薪资/面经）"
```

---

### Task 4: 决策中心聚合页

**Files:**
- Create: `frontend/app/(app)/decision-center/layout.tsx`
- Create: `frontend/app/(app)/decision-center/page.tsx`

**改动内容：**
- 新建决策中心页面，2 个 Tab：待决策、决策记录
- 待决策 Tab：显示未完成的决策列表，从 `/decisions` API 拉取
- 决策记录 Tab：显示已完成的历史决策
- "创建新决策"按钮跳转到 `/decision-lab`

- [ ] **Step 1: 创建 layout.tsx**

```tsx
export default function DecisionCenterLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
```

- [ ] **Step 2: 创建决策中心页面**

```tsx
"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, Clock, CheckCircle2, ArrowRight, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { decisionsApi } from "@/lib/api";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type { DestinationDecision } from "@/types";

const TABS = [
  { id: "pending", label: "待决策", icon: Clock },
  { id: "history", label: "决策记录", icon: CheckCircle2 },
];

export default function DecisionCenterPage() {
  const router = useRouter();
  const toast = useToast();
  const [activeTab, setActiveTab] = useState("pending");
  const [decisions, setDecisions] = useState<DestinationDecision[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await decisionsApi.list();
        setDecisions(Array.isArray(data) ? data : []);
      } catch (err) {
        toast.push(err instanceof Error ? err.message : "加载决策列表失败", "error");
      } finally {
        setLoading(false);
      }
    })();
  }, [toast]);

  const pendingDecisions = decisions.filter((d) => d.status === "planned" || d.status === "confirmed");
  const historyDecisions = decisions.filter((d) => d.status === "executed" || d.status === "changed");

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-ink-800">决策中心</h1>
          <p className="text-ink-500 mt-1">管理你的关键人生决策，让每个选择都有依据</p>
        </div>
        <Button onClick={() => router.push("/decision-lab")} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          创建新决策
        </Button>
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-2 mb-6 border-b border-paper-300 pb-2">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 rounded-t-lg text-sm font-medium transition-colors",
                activeTab === tab.id
                  ? "bg-white text-brand-600 border-b-2 border-brand-500"
                  : "text-ink-400 hover:text-ink-600 hover:bg-paper-200",
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
              {tab.id === "pending" && pendingDecisions.length > 0 && (
                <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-brand-500 px-1 text-[11px] font-semibold text-white">
                  {pendingDecisions.length}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* 内容区 */}
      {loading ? (
        <LoadingState />
      ) : activeTab === "pending" ? (
        pendingDecisions.length === 0 ? (
          <EmptyState
            title="暂无待决策事项"
            description="创建一个新决策，让 AI 帮你分析"
            action={
              <Button onClick={() => router.push("/decision-lab")}>
                <Plus className="h-4 w-4 mr-1" />
                创建新决策
              </Button>
            }
          />
        ) : (
          <div className="space-y-3">
            {pendingDecisions.map((d) => (
              <div key={d.id} className="bg-white rounded-xl border border-paper-200 p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-ink-800">{d.title || "未命名决策"}</h3>
                    <p className="text-sm text-ink-500 mt-1">
                      {d.destination_type} · {new Date(d.created_at).toLocaleDateString("zh-CN")}
                    </p>
                  </div>
                  <Link
                    href={`/decisions/${d.id}`}
                    className="text-sm text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1"
                  >
                    继续分析 <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        historyDecisions.length === 0 ? (
          <EmptyState title="暂无决策记录" description="完成决策后，记录会出现在这里" />
        ) : (
          <div className="space-y-3">
            {historyDecisions.map((d) => (
              <div key={d.id} className="bg-white rounded-xl border border-paper-200 p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-ink-800">{d.title || "未命名决策"}</h3>
                    <p className="text-sm text-ink-500 mt-1">
                      {d.destination_type} · {d.status === "executed" ? "已执行" : "已变更"}
                    </p>
                  </div>
                  <span className={cn(
                    "text-xs px-2 py-1 rounded-full font-medium",
                    d.status === "executed" ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
                  )}>
                    {d.status === "executed" ? "已执行" : "已变更"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}
```

- [ ] **Step 3: 验证 tsc + build**

Run: `cd frontend && npx tsc --noEmit && npx next build`
Expected: 0 errors, build success

- [ ] **Step 4: Commit**

```bash
git add frontend/app/(app)/decision-center/
git commit -m "feat: 决策中心聚合页 — 待决策/决策记录 Tab + 创建新决策入口"
```

---

### Task 5: 成长档案聚合页

**Files:**
- Create: `frontend/app/(app)/growth/archive/layout.tsx`
- Create: `frontend/app/(app)/growth/archive/page.tsx`

**改动内容：**
- 新建成长档案聚合页，6 个 Tab：概览、技能树、平衡轮、时间线、回顾、成就
- 每个 Tab 显示对应工具的摘要卡片 + 链接到完整页面
- 概览 Tab 显示关键指标（技能雷达图、平衡轮快照浓缩）

- [ ] **Step 1: 创建 layout.tsx**

```tsx
export default function GrowthArchiveLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
```

- [ ] **Step 2: 创建成长档案页面**

```tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { BarChart3, Target, Circle, Calendar, FileText, Award } from "lucide-react";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "overview", label: "概览", icon: BarChart3, href: "/growth" },
  { id: "skills", label: "技能树", icon: Target, href: "/skills" },
  { id: "wheel", label: "平衡轮", icon: Circle, href: "/life-wheel" },
  { id: "timeline", label: "时间线", icon: Calendar, href: "/timeline" },
  { id: "retro", label: "回顾", icon: FileText, href: "/retrospectives" },
  { id: "achievements", label: "成就", icon: Award, href: "/achievements" },
];

export default function GrowthArchivePage() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-ink-800">成长档案</h1>
        <p className="text-ink-500 mt-1">记录你的成长轨迹，追踪技能提升，回顾关键节点</p>
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-2 mb-6 border-b border-paper-300 pb-2 overflow-x-auto">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 rounded-t-lg text-sm font-medium transition-colors whitespace-nowrap",
                activeTab === tab.id
                  ? "bg-white text-brand-600 border-b-2 border-brand-500"
                  : "text-ink-400 hover:text-ink-600 hover:bg-paper-200",
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab 内容 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {TABS.filter((t) => t.id === activeTab).map((tab) => (
          <Link
            key={tab.id}
            href={tab.href}
            className="col-span-full bg-white rounded-xl border border-paper-200 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2.5 rounded-lg bg-brand-50 text-brand-600">
                <tab.icon className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-semibold text-ink-800">{tab.label}</h2>
              </div>
            </div>
            <p className="text-sm text-brand-600 font-medium mt-2">查看完整 {tab.label} →</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 验证 tsc + build**

Run: `cd frontend && npx tsc --noEmit && npx next build`
Expected: 0 errors, build success

- [ ] **Step 4: Commit**

```bash
git add frontend/app/(app)/growth/archive/
git commit -m "feat: 成长档案聚合页 — 6 Tab（概览/技能树/平衡轮/时间线/回顾/成就）"
```

---

### Task 6: 社区合并 + 个人中心增强

**Files:**
- Modify: `frontend/app/(app)/community/page.tsx`
- Modify: `frontend/app/(app)/profile/page.tsx`

**改动内容：**
- 社区页面添加方向专区 Tab（全部/考研专区/考公专区/就业专区/上岸墙）
- 个人中心页面添加"诊断报告"Tab 和"成就"Tab

- [ ] **Step 1: 修改社区页面，添加 Tab 切换**

在社区页面顶部添加 Tab 栏，将现有内容作为"全部"Tab，添加"考研专区"链接到 `/kaoyan/community`，"考公专区"、"就业专区"、"上岸墙"链接到 `/outcome-report/landing-wall`

- [ ] **Step 2: 修改个人中心页面，添加诊断报告 + 成就 Tab**

在个人中心页面添加 Tab 栏：个人资料、诊断报告（链接到 `/onboarding` 结果）、成就（链接到 `/achievements`）、通知设置

- [ ] **Step 3: 验证 tsc + build**

Run: `cd frontend && npx tsc --noEmit && npx next build`
Expected: 0 errors, build success

- [ ] **Step 4: Commit**

```bash
git add frontend/app/(app)/community/page.tsx frontend/app/(app)/profile/page.tsx
git commit -m "feat: 社区合并方向专区 + 个人中心增强诊断报告/成就 Tab"
```

---

### Task 7: 旧入口 redirect + 最终验证

**Files:**
- Modify: `frontend/app/(app)/career/page.tsx`（改为 redirect）
- 验证所有旧 URL 路径仍然可访问

- [ ] **Step 1: career 页面改为 redirect**

```tsx
// app/(app)/career/page.tsx — 改为重定向到决策中心
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CareerRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/decision-center");
  }, [router]);
  return null;
}
```

- [ ] **Step 2: 验证所有旧 URL 路径可访问**

检查以下 URL 返回 200：
- `/dashboard` → 新的精简看板
- `/kaoyan` → 原页面（导航入口移除但页面还在）
- `/civil-service` → 原页面
- `/employment` → 原页面
- `/war-room` → 原页面
- `/decision-lab` → 原页面
- `/decisions` → 原页面
- `/skills` → 原页面
- `/life-wheel` → 原页面
- `/timeline` → 原页面
- `/retrospectives` → 原页面
- `/achievements` → 原页面
- `/onboarding` → 原页面
- `/interview` → 原页面
- `/outcome-report` → 原页面

- [ ] **Step 3: 最终验证**

```bash
cd frontend && npx tsc --noEmit && npx next build
```

Expected: 0 errors, build success

- [ ] **Step 4: 最终 Commit**

```bash
git add frontend/app/(app)/career/page.tsx
git commit -m "feat: career 重定向到决策中心 + 全量验证"
```