# GradPath 知识库管理页面设计

## 概述

为 Phase 11 已就绪的知识库后端 API（6 端点）补充管理员 CRUD 前端界面。普通用户通过对话间接使用知识库（RAG 检索），管理员通过此界面管理知识条目。

## 路由与访问控制

三个路由，均位于 `(app)` 路由组内（受 AuthGuard 保护）：

| 路由 | 用途 | 权限 |
|------|------|------|
| `/knowledge` | 列表页：筛选、搜索、分页、删除 | 管理员 |
| `/knowledge/new` | 新建文章 | 管理员 |
| `/knowledge/[id]/edit` | 编辑文章 | 管理员 |

- 页面加载时检查 `useAuthStore` 中的 `user.is_admin`，非管理员重定向到 `/dashboard`
- 后端已有 `get_admin_user` 依赖保护 POST/PUT/DELETE 端点，前端检查仅 UX 层

## 列表页 (`/knowledge`)

### 顶部工具栏

- 分类下拉筛选（全部 / 行业指南 / 岗位要求 / 技能图谱 / 面试攻略 / 薪资参考 / 升学路径）— 传 `category` 参数到后端 `GET /api/knowledge`
- 标题搜索输入框 — 前端对当前页 items 按 `title.includes(query)` 过滤（列表端点不支持文本搜索，搜索端点 `POST /api/knowledge/search` 返回 top 5 不适合分页浏览）
- "新建文章"按钮 → 跳转 `/knowledge/new`

### 数据表格

| 列 | 内容 | 样式 |
|----|------|------|
| 标题 | 文章标题 | 点击跳转编辑页 |
| 分类 | category | Badge 颜色按分类区分 |
| 标签 | tags 数组 | Badge 组，最多显示 3 个 |
| 状态 | is_published | 发布=绿色 Badge，未发布=灰色 |
| 更新时间 | updated_at | formatDate |
| 操作 | 编辑/删除按钮 | 图标按钮 |

- 分页：复用 `Pagination` 组件，每页 20 条
- 删除：`confirm()` 确认 → 调用 `knowledgeApi.delete` → toast 反馈 → 刷新列表
- 空状态：EmptyState 引导新建

### 分类 Badge 颜色映射

| 分类 | 颜色 |
|------|------|
| 行业指南 | blue |
| 岗位要求 | green |
| 技能图谱 | amber |
| 面试攻略 | purple |
| 薪资参考 | red |
| 升学路径 | slate |

## 编辑器页面 (`/knowledge/new` 和 `/knowledge/[id]/edit`)

### 布局

左右分栏（`lg:grid-cols-2`）：
- 左侧：Markdown 编辑区（Textarea）
- 右侧：实时预览区（复用 `Markdown` 组件）
- 移动端：切换按钮在编辑/预览之间切换

### 表单字段

| 字段 | 组件 | 验证 |
|------|------|------|
| 分类 | Select（6 个选项） | 必选 |
| 标题 | Input | 必填，max 200 |
| 内容 | Textarea（min-h 400px） | 必填 |
| 标签 | Input（逗号分隔 → 数组） | 可选 |
| 来源 | Input | 可选，max 200 |
| 发布状态 | Toggle（checkbox 样式） | 默认 true |

### 交互

- 内容输入时右侧预览实时更新（`onChange` 直接渲染）
- 标签输入：逗号分隔的字符串 → `split(",").map(s => s.trim()).filter(Boolean)` → 数组
- 保存按钮：
  - 新建：调用 `knowledgeApi.create` → 201 → toast 成功 → 跳回 `/knowledge`
  - 编辑：调用 `knowledgeApi.update` → 200 → toast 成功 → 跳回 `/knowledge`
  - 失败：toast 错误信息
- 取消按钮：返回 `/knowledge`
- 编辑页加载时调用 `knowledgeApi.get(id)` 填充表单

### Zod 验证

```typescript
const knowledgeSchema = z.object({
  category: z.string().min(1, "请选择分类"),
  title: z.string().min(1, "标题不能为空").max(200, "标题最多200字"),
  content: z.string().min(1, "内容不能为空"),
  tags: z.array(z.string()).default([]),
  source: z.string().max(200).optional().nullable(),
  is_published: z.boolean().default(true),
});
```

## API 客户端补全

当前 `knowledgeApi` 缺少 `create/update/delete`，需补加：

```typescript
export const knowledgeApi = {
  list: (params?) => ...,     // 已有
  get: (id: string) => ...,   // 已有
  search: (query: string) => ..., // 已有
  create: (body: KnowledgeArticleCreate) =>
    request<KnowledgeArticle>("/api/knowledge", {
      method: "POST", body: JSON.stringify(body),
    }),
  update: (id: string, body: KnowledgeArticleUpdate) =>
    request<KnowledgeArticle>(`/api/knowledge/${id}`, {
      method: "PUT", body: JSON.stringify(body),
    }),
  delete: (id: string) =>
    request<void>(`/api/knowledge/${id}`, { method: "DELETE" }),
};
```

新增类型：

```typescript
export interface KnowledgeArticleCreate {
  category: string;
  title: string;
  content: string;
  tags?: string[];
  source?: string | null;
  metadata_?: Record<string, unknown>;
  is_published?: boolean;
}

export interface KnowledgeArticleUpdate {
  category?: string;
  title?: string;
  content?: string;
  tags?: string[];
  source?: string | null;
  metadata_?: Record<string, unknown>;
  is_published?: boolean;
}
```

## 导航栏

在管理员专属区域（`isAdmin` 分支内）添加：
- 标签：知识库
- 图标：`BookOpen`
- 位置：数据管道之前

## 文件清单

| 文件 | 操作 |
|------|------|
| `frontend/app/(app)/knowledge/page.tsx` | 新建：列表页 |
| `frontend/app/(app)/knowledge/new/page.tsx` | 新建：新建文章页 |
| `frontend/app/(app)/knowledge/[id]/edit/page.tsx` | 新建：编辑文章页 |
| `frontend/lib/api.ts` | 修改：补全 knowledgeApi create/update/delete |
| `frontend/types/index.ts` | 修改：添加 KnowledgeArticleCreate/Update 类型 |
| `frontend/components/nav.tsx` | 修改：添加知识库导航项 |
| `frontend/lib/validations.ts` | 修改：添加 knowledgeSchema |

## 测试

- 后端已有 12 个知识库测试（test_knowledge.py），无需新增
- 前端：tsc 编译通过 + next build 成功
- 手动验证：列表筛选/搜索/分页、新建/编辑/删除流程、Markdown 预览、非管理员重定向
