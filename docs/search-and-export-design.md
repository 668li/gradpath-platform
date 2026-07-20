# GradPath 全文搜索 + 数据导出 架构设计

> **日期**: 2026-07-13
> **状态**: Design Proposal

---

## 一、技术选型：搜索引擎对比

### 1.1 三选一对比

| 维度 | PostgreSQL FTS | Meilisearch | Elasticsearch |
|------|---------------|-------------|---------------|
| **架构** | 数据库内置 | 独立引擎(Rust) | 独立引擎(Java) |
| **额外基础设施** | 无 | 需加1个容器 | 需加1-2个容器 |
| **中文分词** | pg_jieba / zhparser | 内置(一般) | IK插件(好) |
| **拼写纠错** | pg_trgm(有限) | 开箱即用(优秀) | 需配置(可配) |
| **搜索延迟** | 5-50ms | 1-10ms | 10-100ms |
| **数据量上限** | 百万级 | 千万级 | 无限 |
| **运维成本** | 零 | 低(单二进制) | 高(JVM调优) |
| **相关性排序** | ts_rank(基础) | ranking rules(好) | BM25/custom(最强) |
| **聚合分析** | SQL GROUP BY | facets(基本) | aggregations(最强) |
| **学习曲线** | 低(SQL即可) | 低(REST API) | 高(Query DSL) |

### 1.2 选型结论：推荐 PostgreSQL FTS

**理由：**

1. **已有基础设施** — GradPath 已用 PostgreSQL 16 + pgvector，不引入新服务
2. **数据规模匹配** — 考研数据（院校情报/问答/经验帖）百万级以内，PG FTS 足够
3. **运维零成本** — 不增加 Docker 容器、不增加运维负担
4. **中文支持成熟** — pg_jieba 扩展（2026年主流方案）提供专业中文分词
5. **与现有代码兼容** — SQLAlchemy ORM 直接操作，无需引入新 SDK
6. **已有 pgvector** — DB 已承载向量搜索负载，FTS 负载可复用

**如果未来需要升级的路径：**
- Phase 1: PostgreSQL FTS（当前推荐）
- Phase 2: Meilisearch（若需拼写纠错 + 即时搜索 UX）
- Phase 3: Elasticsearch（若数据量过亿或需复杂聚合）

---

## 二、全文搜索架构设计

### 2.1 中文分词方案

**使用 pg_jieba 扩展**（基于 jieba 分词库，2026年 PostgreSQL 中文 FTS 标准方案）。

```sql
-- Docker 镜像需要安装 pg_jieba
-- postgres:16-alpine 需要换为支持扩展的镜像或自定义构建

-- 安装扩展
CREATE EXTENSION IF NOT EXISTS pg_jieba;

-- 创建中文全文搜索配置
CREATE TEXT SEARCH CONFIGURATION gradpath_chinese (PARSER = jieba);
ALTER TEXT SEARCH CONFIGURATION gradpath_chinese
    ADD MAPPING FOR n,v,a,i,e,l WITH simple;
```

**Docker 改动：** 需要将 `postgres:16-alpine` 替换为自定义镜像或使用支持 pg_jieba 的 PostgreSQL 发行版。

```dockerfile
# Dockerfile.db
FROM postgres:16-alpine

# 安装 pg_jieba（编译安装）
RUN apk add --no-cache git build-essential postgresql-dev cmake && \
    git clone https://github.com/jaiminpan/pg_jieba.git /tmp/pg_jieba && \
    cd /tmp/pg_jieba && \
    make && make install && \
    apk del git build-essential cmake && \
    rm -rf /tmp/pg_jieba

# 复制初始化脚本
COPY init.sql /docker-entrypoint-initdb.d/
```

### 2.2 数据库层：tsvector 列 + GIN 索引

为每个可搜索表添加 `search_vector` 生成列 + GIN 索引。

#### 2.2.1 院校情报 (grad_school_intel)

```sql
ALTER TABLE grad_school_intel ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('gradpath_chinese', coalesce(school_name, '')), 'A') ||
        setweight(to_tsvector('gradpath_chinese', coalesce(major_name, '')), 'A') ||
        setweight(to_tsvector('gradpath_chinese', coalesce(ai_summary, '')), 'B') ||
        setweight(to_tsvector('gradpath_chinese', coalesce(insider_notes, '')), 'C')
    ) STORED;

CREATE INDEX idx_grad_school_intel_search
    ON grad_school_intel USING gin(search_vector);
```

**权重说明：** A=学校名+专业名(最高), B=AI摘要, C=内部备注

#### 2.2.2 暗知识 (dark_knowledge)

```sql
ALTER TABLE dark_knowledge ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('gradpath_chinese', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('gradpath_chinese', coalesce(content, '')), 'B') ||
        setweight(to_tsvector('gradpath_chinese', coalesce(common_misconception, '')), 'C') ||
        setweight(to_tsvector('gradpath_chinese', coalesce(actionable_advice, '')), 'C')
    ) STORED;

CREATE INDEX idx_dark_knowledge_search
    ON dark_knowledge USING gin(search_vector);
```

#### 2.2.3 问答 (qas)

```sql
ALTER TABLE qas ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('gradpath_chinese', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('gradpath_chinese', coalesce(content, '')), 'B')
    ) STORED;

CREATE INDEX idx_qas_search ON qas USING gin(search_vector);
```

#### 2.2.4 经验帖 (experience_posts)

```sql
ALTER TABLE experience_posts ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('gradpath_chinese', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('gradpath_chinese', coalesce(summary, '')), 'B') ||
        setweight(to_tsvector('gradpath_chinese', coalesce(content, '')), 'B')
    ) STORED;

CREATE INDEX idx_experience_posts_search
    ON experience_posts USING gin(search_vector);
```

#### 2.2.5 知识库 (knowledge_articles)

```sql
ALTER TABLE knowledge_articles ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('gradpath_chinese', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('gradpath_chinese', coalesce(content, '')), 'B')
    ) STORED;

CREATE INDEX idx_knowledge_articles_search
    ON knowledge_articles USING gin(search_vector);
```

#### 2.2.6 导师 (mentors)

```sql
ALTER TABLE mentors ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('gradpath_chinese', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('gradpath_chinese', coalesce(research_directions, '')), 'B') ||
        setweight(to_tsvector('gradpath_chinese', coalesce(information_source, '')), 'C')
    ) STORED;

CREATE INDEX idx_mentors_search ON mentors USING gin(search_vector);
```

### 2.3 搜索 Service 设计

```
backend/app/services/search_service.py
```

```python
"""
统一全文搜索服务
搜索范围：院校情报、暗知识、问答、经验帖、知识库、导师
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import text, func, union_all, literal_column
from app.models import (
    GradSchoolIntel, DarkKnowledge, QA,
    ExperiencePost, KnowledgeArticle, Mentor
)


class SearchType(str, Enum):
    ALL = "all"
    GRAD_INTEL = "院校"
    DARK_KNOWLEDGE = "暗知识"
    QA = "问答"
    EXPERIENCE = "经验"
    KNOWLEDGE = "知识"
    MENTOR = "导师"


class SortBy(str, Enum):
    RELEVANCE = "relevance"  # 按相关性（默认）
    TIME_DESC = "time_desc"  # 最新
    TIME_ASC = "time_asc"    # 最早
    VIEWS = "views"          # 最多浏览


@dataclass
class SearchResult:
    id: str
    type: str           # "院校" / "暗知识" / "问答" / "经验" / "知识" / "导师"
    title: str
    snippet: str        # 摘要片段（含高亮标签）
    score: float        # 相关性分数
    url: str            # 前端路由
    metadata: dict      # 附加信息（标签、浏览量等）


@dataclass
class SearchResponse:
    query: str
    results: list[SearchResult]
    total: int
    page: int
    page_size: int
    facets: dict        # 各类型的数量统计


class SearchService:
    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        query: str,
        search_type: SearchType = SearchType.ALL,
        sort_by: SortBy = SortBy.RELEVANCE,
        tags: Optional[list[str]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SearchResponse:
        """
        统一搜索入口
        - query: 搜索关键词
        - search_type: 搜索范围（全部/院校/暗知识/问答/经验/知识/导师）
        - sort_by: 排序方式
        - tags: 标签过滤
        - page/page_size: 分页
        """
        ...

    def _build_tsquery(self, query: str) -> str:
        """将用户输入转换为 tsquery（支持多词 AND/OR）"""
        # 使用 plainto_tsquery：自动分词，词之间 AND 连接
        return query

    def _search_grad_intel(self, tsquery, tags, limit, offset):
        """搜索院校情报"""
        sql = text("""
            SELECT
                g.id::text as id,
                '院校' as type,
                g.school_name || ' - ' || g.major_name as title,
                ts_headline('gradpath_chinese',
                    coalesce(g.ai_summary, g.insider_notes, ''),
                    :query,
                    'StartSel=<mark>, StopSel=</mark>, MaxFragments=2, MaxWords=30'
                ) as snippet,
                ts_rank(g.search_vector, :query) as score,
                '/grad-war-room/intel?school=' || g.school_name as url,
                jsonb_build_object(
                    'school_tier', g.school_tier,
                    'year', g.year,
                    'score_line', g.score_line
                ) as metadata
            FROM grad_school_intel g
            WHERE g.search_vector @@ plainto_tsquery('gradpath_chinese', :query)
            ORDER BY ts_rank(g.search_vector, :query) DESC
            LIMIT :limit OFFSET :offset
        """)
        ...

    def _search_dark_knowledge(self, tsquery, tags, limit, offset):
        """搜索暗知识"""
        sql = text("""
            SELECT
                dk.id::text as id,
                '暗知识' as type,
                dk.title as title,
                ts_headline('gradpath_chinese',
                    dk.content,
                    :query,
                    'StartSel=<mark>, StopSel=</mark>, MaxFragments=2, MaxWords=30'
                ) as snippet,
                ts_rank(dk.search_vector, :query) as score,
                '/grad-war-room/dark-knowledge?id=' || dk.id as url,
                jsonb_build_object(
                    'stage', dk.stage,
                    'importance', dk.importance,
                    'category', dk.category
                ) as metadata
            FROM dark_knowledge dk
            WHERE dk.search_vector @@ plainto_tsquery('gradpath_chinese', :query)
            ORDER BY ts_rank(dk.search_vector, :query) DESC
            LIMIT :limit OFFSET :offset
        """)
        ...

    def _search_qa(self, tsquery, tags, limit, offset):
        """搜索问答"""
        sql = text("""
            SELECT
                q.id::text as id,
                '问答' as type,
                q.title as title,
                ts_headline('gradpath_chinese',
                    q.content,
                    :query,
                    'StartSel=<mark>, StopSel=</mark>, MaxFragments=2, MaxWords=30'
                ) as snippet,
                ts_rank(q.search_vector, :query) as score,
                '/kaoyan/qa/' || q.id as url,
                jsonb_build_object(
                    'tags', q.tags,
                    'view_count', q.view_count,
                    'answer_count', q.answer_count,
                    'is_resolved', q.is_resolved
                ) as metadata
            FROM qas q
            WHERE q.status = 'approved'
              AND q.search_vector @@ plainto_tsquery('gradpath_chinese', :query)
            ORDER BY ts_rank(q.search_vector, :query) DESC
            LIMIT :limit OFFSET :offset
        """)
        ...

    def _search_experience(self, tsquery, tags, limit, offset):
        """搜索经验帖"""
        ...

    def _search_knowledge(self, tsquery, tags, limit, offset):
        """搜索知识库"""
        ...

    def _search_mentor(self, tsquery, tags, limit, offset):
        """搜索导师"""
        ...

    def _get_facets(self, query: str) -> dict:
        """获取各类型的结果数量（用于搜索结果统计）"""
        tsquery = f"plainto_tsquery('gradpath_chinese', '{query}')"
        sql = text(f"""
            SELECT '院校' as type, COUNT(*) as count
            FROM grad_school_intel
            WHERE search_vector @@ {tsquery}
            UNION ALL
            SELECT '暗知识', COUNT(*)
            FROM dark_knowledge
            WHERE search_vector @@ {tsquery}
            UNION ALL
            SELECT '问答', COUNT(*)
            FROM qas WHERE status='approved' AND search_vector @@ {tsquery}
            UNION ALL
            SELECT '经验', COUNT(*)
            FROM experience_posts
            WHERE status='approved' AND search_vector @@ {tsquery}
            UNION ALL
            SELECT '知识', COUNT(*)
            FROM knowledge_articles WHERE search_vector @@ {tsquery}
            UNION ALL
            SELECT '导师', COUNT(*)
            FROM mentors WHERE search_vector @@ {tsquery}
        """)
        rows = self.db.execute(sql).fetchall()
        return {r.type: r.count for r in rows}

    def suggest(self, query: str, limit: int = 8) -> list[str]:
        """
        搜索建议 / 自动补全
        基于 pg_trgm 的模糊匹配 + 历史搜索记录
        """
        sql = text("""
            SELECT DISTINCT school_name as suggestion
            FROM grad_school_intel
            WHERE school_name % :query
            ORDER BY similarity(school_name, :query) DESC
            LIMIT :limit
        """)
        ...
```

### 2.4 搜索 API 设计

```
backend/app/api/search.py
```

#### 2.4.1 统一搜索接口

```
GET /api/search?q=关键词&type=院校|暗知识|问答|经验|知识|导师|all&sort=relevance|time_desc|views&page=1&page_size=20&tags=调剂,二战
```

**Query Parameters：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `q` | string | 是 | - | 搜索关键词 |
| `type` | string | 否 | `all` | 搜索范围：all/院校/暗知识/问答/经验/知识/导师 |
| `sort` | string | 否 | `relevance` | 排序：relevance/time_desc/time_asc/views |
| `tags` | string | 否 | - | 标签过滤（逗号分隔） |
| `page` | int | 否 | 1 | 页码 |
| `page_size` | int | 否 | 20 | 每页数量（max 100） |

**Response：**

```json
{
  "query": "清华大学 计算机",
  "total": 42,
  "page": 1,
  "page_size": 20,
  "facets": {
    "院校": 15,
    "暗知识": 8,
    "问答": 10,
    "经验": 6,
    "知识": 2,
    "导师": 1
  },
  "results": [
    {
      "id": "xxx-uuid",
      "type": "院校",
      "title": "清华大学 - 计算机科学与技术",
      "snippet": "清华计算机是<mark>全国顶尖</mark>的学科，<mark>报录比</mark>约15:1...",
      "score": 0.92,
      "url": "/grad-war-room/intel?school=清华大学",
      "metadata": {
        "school_tier": "985/211/双一流",
        "year": 2026,
        "score_line": 380
      }
    },
    {
      "id": "yyy-uuid",
      "type": "经验",
      "title": "清华计算机考研经验：从双非到top2",
      "snippet": "作为一个双非学生考上<mark>清华大学</mark><mark>计算机</mark>研究生...",
      "score": 0.85,
      "url": "/kaoyan/community/experience/yyy-uuid",
      "metadata": {
        "view_count": 5420,
        "like_count": 230,
        "category": "初试"
      }
    }
  ]
}
```

#### 2.4.2 搜索建议接口

```
GET /api/search/suggest?q=清华
```

**Response：**

```json
{
  "suggestions": [
    "清华大学",
    "清华大学 - 计算机科学与技术",
    "清华大学 - 软件工程",
    "清华大学 - 人工智能"
  ]
}
```

#### 2.4.3 搜索高亮说明

- 使用 PostgreSQL 的 `ts_headline()` 函数生成高亮片段
- 高亮标签：`<mark>...</mark>`
- 片段控制：`MaxFragments=2, MaxWords=30`
- 前端使用 `dangerouslySetInnerHTML` 渲染高亮（需 XSS 过滤）

### 2.5 pg_trgm 模糊搜索（拼写纠错补充）

```sql
-- 安装 pg_trgm 扩展（PostgreSQL 自带）
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 用于搜索建议的模糊匹配
CREATE INDEX idx_grad_school_intel_name_trgm
    ON grad_school_intel USING gin(school_name gin_trgm_ops);

CREATE INDEX idx_mentors_name_trgm
    ON mentors USING gin(name gin_trgm_ops);
```

---

## 三、数据导出架构设计

### 3.1 现有导出系统分析

**已有端点（7个）：**

| 端点 | 格式 | 状态 |
|------|------|------|
| `GET /api/export/timeline.pdf` | PDF | ✅ 前端已接入 |
| `GET /api/export/profile.json` | JSON | ✅ 前端已接入 |
| `GET /api/export/grad-intel` | JSON | ❌ 前端未接入 |
| `GET /api/export/grad-intel/csv` | CSV | ❌ 前端未接入 |
| `GET /api/export/grad-intel/pdf` | PDF | ❌ 前端未接入 |
| `GET /api/export/dark-knowledge/pdf` | PDF | ❌ 前端未接入 |
| `GET /api/share/skills/{token}` | JSON | 公开分享 |

### 3.2 新增导出功能

#### 3.2.1 问答导出

```
GET /api/export/qa/pdf          # 问答汇编PDF
GET /api/export/qa/csv          # 问答表格CSV
```

**PDF 内容：**
- 按标签分组的问答列表
- 每个问题：标题、内容、标签、回答数、最佳答案
- 统计摘要：总数、已解决比例、热门标签

**CSV 列：**
```
ID, 标题, 内容摘要, 标签, 回答数, 已解决, 最佳答案摘要, 创建时间
```

#### 3.2.2 经验帖导出

```
GET /api/export/experience/pdf  # 经验帖汇编PDF
GET /api/export/experience/csv  # 经验帖表格CSV
```

**PDF 内容：**
- 按分类分组（初试/复试/调剂/择校/复习）
- 每篇：标题、摘要、正文精选、标签、互动数据
- 作者信息（匿名帖标注）

#### 3.2.3 搜索结果导出

```
POST /api/export/search/pdf     # 搜索结果导出PDF
POST /api/export/search/csv     # 搜索结果导出CSV
```

**Request Body：**
```json
{
  "query": "清华大学",
  "type": "院校",
  "filters": {
    "year": 2026,
    "school_tier": "985"
  }
}
```

#### 3.2.4 批量导出（ZIP 包）

```
GET /api/export/batch?type=院校,暗知识,问答&format=pdf
```

**Response：** 返回 ZIP 文件，包含各类型独立 PDF

**实现方式：**
- 使用 `zipfile` 模块生成内存 ZIP
- 每个文件独立生成后打包
- 流式响应避免内存溢出

### 3.3 Excel 导出增强

利用已有的 `openpyxl` 依赖：

```python
def export_grad_intel_excel(db: Session, user_id: UUID) -> bytes:
    """生成多Sheet的Excel报告"""
    wb = openpyxl.Workbook()

    # Sheet 1: 院校情报汇总
    ws1 = wb.active
    ws1.title = "院校情报"
    headers = ["学校", "专业", "层次", "年份", "报录比", "分数线", "推免占比", "复试占比", "备注"]
    ...

    # Sheet 2: 自我定位
    ws2 = wb.create_sheet("自我定位")
    ...

    # Sheet 3: 暗知识精选
    ws3 = wb.create_sheet("暗知识")
    ...

    # Sheet 4: 研招网数据
    ws4 = wb.create_sheet("研招网数据")
    ...

    # Sheet 5: 分数线汇总
    ws5 = wb.create_sheet("分数线")
    ...

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
```

### 3.4 导出 API 设计

#### 3.4.1 完整端点清单

| 端点 | 方法 | 格式 | Auth | 说明 |
|------|------|------|------|------|
| `GET /api/export/grad-intel/pdf` | GET | PDF | ✅ | 院校情报PDF报告 |
| `GET /api/export/grad-intel/csv` | GET | CSV | ✅ | 院校情报CSV表格 |
| `GET /api/export/grad-intel/excel` | GET | Excel | ✅ | **新增** 多Sheet Excel |
| `GET /api/export/dark-knowledge/pdf` | GET | PDF | ❌ | 暗知识PDF（公开） |
| `GET /api/export/dark-knowledge/csv` | GET | CSV | ❌ | **新增** 暗知识CSV |
| `GET /api/export/qa/pdf` | GET | PDF | ✅ | **新增** 问答汇编PDF |
| `GET /api/export/qa/csv` | GET | CSV | ✅ | **新增** 问答表格CSV |
| `GET /api/export/experience/pdf` | GET | PDF | ✅ | **新增** 经验帖汇编PDF |
| `GET /api/export/experience/csv` | GET | CSV | ✅ | **新增** 经验帖表格CSV |
| `POST /api/export/search/pdf` | POST | PDF | ✅ | **新增** 搜索结果PDF |
| `POST /api/export/search/csv` | POST | CSV | ✅ | **新增** 搜索结果CSV |
| `GET /api/export/batch` | GET | ZIP | ✅ | **新增** 批量导出ZIP |
| `GET /api/export/timeline.pdf` | GET | PDF | ✅ | 时间线PDF（已有） |
| `GET /api/export/profile.json` | GET | JSON | ✅ | 个人数据JSON（已有） |
| `GET /api/export/profile/pdf` | GET | PDF | ✅ | **新增** 个人档案PDF |

#### 3.4.2 批量导出接口

```
GET /api/export/batch?types=院校情报,暗知识,问答&format=pdf
```

**Query Parameters：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `types` | string | 是 | 逗号分隔的导出类型 |
| `format` | string | 否 | `pdf`(默认) / `csv` / `excel` |

**Response：** `application/zip` 附件

---

## 四、前端设计

### 4.1 全局搜索栏

```
frontend/components/search/
├── GlobalSearchBar.tsx      # 顶部导航栏全局搜索框
├── SearchResults.tsx        # 搜索结果页面
├── SearchFacets.tsx         # 左侧类型过滤器
├── SearchSnippet.tsx        # 搜索结果卡片（含高亮）
├── SearchSuggestions.tsx    # 搜索建议下拉
└── ExportSearchButton.tsx   # 搜索结果导出按钮
```

**GlobalSearchBar.tsx 设计要点：**
- 位于顶部导航栏（Logo 右侧）
- 输入时防抖调用 `/api/search/suggest`（300ms debounce）
- 回车跳转到 `/search?q=关键词`
- 支持快捷键 `Ctrl+K` / `Cmd+K` 唤起

**SearchResults.tsx 设计要点：**
- 路由：`/search?q=关键词&type=院校`
- 左侧：类型 Facets（院校 15 / 暗知识 8 / 问答 10 / ...）
- 右侧：搜索结果列表，每条显示高亮摘要
- 底部：分页 + 导出按钮

### 4.2 导出按钮增强

**现有 ExportButton 改造：**
```tsx
// 扩展现有的 ExportButton 组件
// 当前只暴露 timeline PDF 和 profile JSON
// 新增：grad-intel PDF/CSV/Excel, dark-knowledge PDF, qa PDF/CSV, experience PDF/CSV

interface ExportButtonProps {
  context: 'timeline' | 'grad-intel' | 'dark-knowledge' | 'qa' | 'experience' | 'search';
  searchParams?: Record<string, string>; // 搜索结果导出时使用
}
```

### 4.3 前端 API 层

```typescript
// frontend/lib/api.ts 新增

export const searchApi = {
  search: (params: {
    q: string;
    type?: string;
    sort?: string;
    tags?: string;
    page?: number;
    page_size?: number;
  }) => `/api/search?${new URLSearchParams(params as any)}`,

  suggest: (q: string) => `/api/search/suggest?q=${encodeURIComponent(q)}`,
};

export const exportApiExtended = {
  gradIntelExcel: () => "/api/export/grad-intel/excel",
  darkKnowledgeCsv: () => "/api/export/dark-knowledge/csv",
  qaPdf: () => "/api/export/qa/pdf",
  qaCsv: () => "/api/export/qa/csv",
  experiencePdf: () => "/api/export/experience/pdf",
  experienceCsv: () => "/api/export/experience/csv",
  profilePdf: () => "/api/export/profile/pdf",
  searchPdf: (query: string, type: string) =>
    `/api/export/search/pdf?q=${encodeURIComponent(query)}&type=${type}`,
  searchCsv: (query: string, type: string) =>
    `/api/export/search/csv?q=${encodeURIComponent(query)}&type=${type}`,
  batch: (types: string[], format: string) =>
    `/api/export/batch?types=${types.join(',')}&format=${format}`,
};
```

---

## 五、实现计划

### Phase 1: 数据库层 (2-3天)

1. **Docker 改造**
   - 创建 `Dockerfile.db`（postgres:16-alpine + pg_jieba）
   - 修改 `docker-compose.yml` 使用自定义 DB 镜像
   - 添加 `pg_trgm` 和 `pg_jieba` 扩展初始化

2. **Alembic 迁移**
   - 为 6 个表添加 `search_vector` 生成列
   - 创建 GIN 索引
   - 创建 pg_trgm 索引（用于搜索建议）

3. **数据填充**
   - 执行迁移后，已有数据的 tsvector 会自动计算
   - 验证中文分词效果

### Phase 2: 搜索后端 (3-4天)

4. **SearchService 实现**
   - 统一搜索逻辑
   - 各实体搜索方法
   - Facets 统计
   - 搜索建议

5. **搜索 API 实现**
   - `GET /api/search` 端点
   - `GET /api/search/suggest` 端点
   - 请求验证（Pydantic）
   - 限流配置

### Phase 3: 导出增强 (3-4天)

6. **新增导出 Service 方法**
   - `export_qa_pdf()`
   - `export_qa_csv()`
   - `export_experience_pdf()`
   - `export_experience_csv()`
   - `export_grad_intel_excel()`
   - `export_dark_knowledge_csv()`
   - `export_profile_pdf()`

7. **新增导出 API 端点**
   - 注册新路由
   - 添加认证/授权
   - 流式响应（大文件）

### Phase 4: 前端 (3-4天)

8. **全局搜索 UI**
   - GlobalSearchBar 组件
   - SearchResults 页面
   - 搜索建议下拉
   - 快捷键支持

9. **导出 UI 增强**
   - 扩展 ExportButton 支持所有导出类型
   - 搜索结果导出按钮
   - 批量导出对话框

### Phase 5: 测试 + 优化 (2天)

10. **性能测试**
    - 中文搜索延迟测试
    - 大数据量 GIN 索引性能
    - PDF 生成性能

11. **搜索质量测试**
    - 中文分词准确性
    - 相关性排序质量
    - 高亮显示准确性

---

## 六、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| pg_jieba 在 Alpine 上编译困难 | 阻塞 Phase 1 | 备选：改用 `postgres:16` (Debian) 替代 Alpine |
| 中文分词不准确 | 搜索质量差 | 使用 jieba 自定义词典添加考研术语 |
| GIN 索引占用空间 | 磁盘增加 | 监控索引大小，必要时调整权重列 |
| PDF 生成慢（大数据量） | 用户等待 | 改为异步任务 + WebSocket 进度通知 |
| 搜索建议延迟 | UX 差 | pg_trgm 索引 + 缓存热门查询 |

---

## 七、技术依赖

### 新增依赖

| 包 | 用途 | 已有 |
|---|------|------|
| `openpyxl` | Excel 生成 | ✅ 已有 |
| `reportlab` | PDF 生成 | ✅ 已有 |
| `pg_jieba` | 中文分词 | ❌ 新增（DB 扩展） |
| `pg_trgm` | 模糊搜索 | ❌ 新增（DB 扩展） |

### 无新增 Python 包

所有导出功能使用已有依赖（reportlab + openpyxl + pandas），搜索功能使用 PostgreSQL 内置能力。

---

## 八、性能预估

| 操作 | 目标延迟 | 说明 |
|------|----------|------|
| 搜索请求 | < 100ms | GIN 索引 + ts_rank |
| 搜索建议 | < 50ms | pg_trgm + GIN |
| PDF 导出 | < 3s | 单用户报告 |
| Excel 导出 | < 2s | 多 Sheet |
| 批量 ZIP 导出 | < 10s | 5个文件打包 |
| 搜索结果导出 | < 5s | 按搜索条件导出 |
