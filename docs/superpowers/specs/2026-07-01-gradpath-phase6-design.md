# Phase 6：社区讨论功能

## 概述

在现有的社区聚合结果页、面试聚合结果页、就业探索结果页底部嵌入可复用的讨论区组件，让用户围绕"某个学校的就业去向"、"某家公司的面试经验"等主题发帖讨论和回复。讨论帖关联到已有的聚合主题，形成"数据+讨论"的社区模式。

**目标**：让平台从单向数据提交变成真正的交流社区，用户看完聚合数据后可以直接在下方讨论和提问。

## 背景

Phase 3 社区聚合和 Phase 4 面试经验聚合已完成，但用户只能匿名提交数据，无法互相交流。用户看完"清华大学计算机专业的人去了哪"后，自然想在下面讨论和提问。Phase 1 预留了 ReferenceSnapshot 接口但未实现交互层。

## 整体架构

```
┌─────────────────────────────────────────┐
│         现有聚合结果页                     │
│  (community/result, interview/result,   │
│   explore/result)                        │
│                                         │
│  [图表 + 排名 + 统计数据]                 │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │   DiscussionSection 组件         │    │
│  │   (topic_type + topic_key)      │    │
│  │                                 │    │
│  │   ┌───────────────────────┐     │    │
│  │   │  顶层帖卡片             │     │    │
│  │   │  (作者 + 时间 + 内容)   │     │    │
│  │   │  [回复] [编辑] [删除]   │     │    │
│  │   │  ┌─────────────────┐   │     │    │
│  │   │  │  回复帖卡片      │   │     │    │
│  │   │  └─────────────────┘   │     │    │
│  │   └───────────────────────┘     │    │
│  │                                 │    │
│  │   [发帖输入框]                   │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

## 数据模型

### Post 模型（新增）

```python
class PostTopicType(str, enum.Enum):
    school_major = "school_major"
    company_position = "company_position"

class Post(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "posts"

    topic_type: Mapped[PostTopicType]
    topic_key: Mapped[str]                    # "清华大学|计算机科学与技术" 或 "腾讯|后端开发"
    content: Mapped[str]                      # 纯文本，最多 2000 字符
    user_id: Mapped[UUID]                     # ForeignKey → users.id
    parent_id: Mapped[UUID | None]            # None=顶层帖, 有值=回复帖
```

- `topic_key` 格式：`school_major` 用 `"{school}|{major}"`，`company_position` 用 `"{company}|{position}"`
- `content` 限制 2000 字符，纯文本（不做 Markdown 渲染，避免 XSS 风险）
- `parent_id` 为 None 时是顶层帖，有值时是回复帖（仅 1 层嵌套）
- 无唯一约束（用户可多次发帖）
- 删除顶层帖级联删除其所有回复

## API 设计

所有端点前缀 `/api/posts`。

| 端点 | 方法 | 认证 | 用途 |
|------|------|------|------|
| `/api/posts` | GET | 公开 | 按主题查询帖子列表 |
| `/api/posts` | POST | 登录 | 发帖/回复 |
| `/api/posts/{id}` | PUT | 登录(作者) | 编辑帖子内容 |
| `/api/posts/{id}` | DELETE | 登录(作者) | 删除帖子（级联删除回复） |

### GET /api/posts

查询参数：
- `topic_type`（必填）：`school_major` 或 `company_position`
- `topic_key`（必填）：主题标识
- `page`（默认 1）：页码
- `page_size`（默认 20）：每页顶层帖数

响应：
```json
{
  "items": [
    {
      "id": "uuid",
      "topic_type": "school_major",
      "topic_key": "清华大学|计算机科学与技术",
      "content": "请问这个专业去字节的多吗？",
      "author_name": "张三",
      "author_id": "uuid",
      "created_at": "2026-07-01T10:00:00Z",
      "updated_at": "2026-07-01T10:00:00Z",
      "replies": [
        {
          "id": "uuid",
          "content": "挺多的，今年去了好几个",
          "author_name": "李四",
          "author_id": "uuid",
          "created_at": "2026-07-01T10:05:00Z",
          "updated_at": "2026-07-01T10:05:00Z",
          "replies": []
        }
      ]
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

### POST /api/posts

请求体：
```json
{
  "topic_type": "school_major",
  "topic_key": "清华大学|计算机科学与技术",
  "content": "请问这个专业去字节的多吗？",
  "parent_id": null
}
```

- `parent_id` 为 null 时创建顶层帖，有值时创建回复帖
- 回复帖的 `topic_type` 和 `topic_key` 必须与父帖一致

### PUT /api/posts/{id}

请求体：
```json
{
  "content": "修改后的内容"
}
```

### DELETE /api/posts/{id}

- 删除顶层帖时级联删除其所有回复
- 删除回复帖时仅删除该回复
- 204 No Content

## 前端组件

### DiscussionSection 组件

文件：`frontend/components/discussion-section.tsx`

```typescript
interface DiscussionSectionProps {
  topicType: "school_major" | "company_position";
  topicKey: string;
  title?: string;
}
```

功能：
- 帖子列表：顶层帖卡片（作者头像首字 + 用户名 + 相对时间 + 内容 + 回复数），点击展开回复列表
- 发帖框：底部 textarea + 发送按钮（未登录显示"登录后参与讨论"）
- 回复框：每个顶层帖下方可展开回复输入框
- 操作按钮：作者可编辑（inline）、删除（二次确认）
- 空状态："还没有人讨论，来说点什么吧"
- 分页：底部"加载更多"按钮

### 嵌入位置

| 页面 | topic_type | topic_key |
|------|-----------|-----------|
| `community/result/page.tsx` | `school_major` | `{school}\|{major}` |
| `interview/result/page.tsx` | `company_position` | `{company}\|{position}` |
| `explore/result/page.tsx` | `school_major` | `{school}\|{major}` |

### 帖子展示规则

- 内容中的 URL 自动转为链接，换行符保留
- 时间显示相对时间（"3 分钟前"、"昨天"、"2 天前"）
- 作者头像：用户名首字 + 品牌色背景

## 错误处理

| 场景 | 处理 |
|------|------|
| 发帖内容为空/超 2000 字 | 前端校验 + 后端 422 |
| 编辑/删除他人帖子 | 后端 403 |
| 删除有回复的顶层帖 | 级联删除，前端二次确认 |
| 网络错误 | toast 提示，不丢失输入内容 |

## 测试策略

### 后端测试

| 测试文件 | 覆盖范围 | 预估数 |
|----------|---------|--------|
| `test_api_posts.py` | 发帖/回复/编辑/删除/列表/权限校验/级联删除/分页/空内容校验/回复帖 topic 一致性 | ~12 |

### 种子数据

`pipeline/seed_posts.py`：为 3 个主题预置约 15 条帖子和回复：
- "清华大学|计算机科学与技术" — 5 帖 + 5 回复
- "腾讯|后端开发" — 3 帖 + 2 回复
- "字节跳动|算法工程师" — 0 帖（测试空状态）

### 前端验证

E2E 验证讨论区渲染、发帖、回复、删除。

## 不做的事（YAGNI）

- 不做点赞/踩功能
- 不做 @提及通知
- 不做帖子搜索
- 不做用户主页/帖子列表
- 不做 Markdown 渲染（纯文本）
- 不做图片/附件上传
- 不做管理员帖子管理
- 不做多级嵌套（仅 1 层回复）
