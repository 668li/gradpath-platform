"""全文搜索 API — 兼容 PostgreSQL（pg_trgm GIN 索引加速）与 SQLite（LIKE 回退）。

支持对经验帖、知识文章、问答、暗知识的全文检索，
提供高亮、分页、类型过滤功能。
"""
import json
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import engine, get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["搜索"])


def is_postgresql() -> bool:
    """检测当前数据库是否为 PostgreSQL。"""
    return "postgresql" in str(engine.url)


# ======================================================================
# Schema 定义
# ======================================================================


class SearchResultItem(BaseModel):
    """搜索结果项。"""
    id: str
    type: str  # experience / knowledge / qa / dark
    title: str
    content: str  # 截断后的内容
    highlight: str  # 高亮片段
    score: float  # 相关度评分
    metadata: dict  # 附加信息


class SearchResponse(BaseModel):
    """搜索响应。"""
    query: str
    type: str
    total: int
    page: int
    page_size: int
    results: list[SearchResultItem]


# ======================================================================
# 搜索 SQL 模板
# ======================================================================


def _build_search_sql(type_filter: str) -> tuple[str, str]:
    """构建搜索 SQL，根据数据库类型分发到 PostgreSQL 或 SQLite 实现。"""
    if is_postgresql():
        return _build_pg_search_sql(type_filter)
    return _build_sqlite_search_sql(type_filter)


# ------------------------------------------------------------------
# PostgreSQL 版本：ILIKE + pg_trgm GIN 索引加速
# ------------------------------------------------------------------


def _build_pg_search_sql(type_filter: str) -> tuple[str, str]:
    """构建 PostgreSQL 搜索 SQL（ILIKE + unnest 关键词评分）。"""

    if type_filter == "experience":
        search_sql = """
WITH keywords AS (
    SELECT unnest(string_to_array(:query, ' ')) AS kw
),
results AS (
    SELECT
        e.id::text AS id,
        'experience' AS type,
        e.title,
        COALESCE(e.summary, LEFT(e.content, 200)) AS content,
        e.title AS highlight,
        (SELECT COUNT(*) FROM keywords k WHERE e.title ILIKE '%' || k.kw || '%' OR e.content ILIKE '%' || k.kw || '%')::float /
            (SELECT COUNT(*) FROM keywords) AS score,
        jsonb_build_object(
            'category', e.category,
            'tags', e.tags,
            'status', e.status,
            'source_platform', e.source_platform
        ) AS metadata
    FROM experience_posts e
    WHERE e.status = 'approved'
        AND (
            e.title ILIKE '%' || :query || '%'
            OR e.content ILIKE '%' || :query || '%'
        )
)
SELECT * FROM results ORDER BY score DESC LIMIT :page_size OFFSET :offset;
"""
        count_sql = """
SELECT COUNT(*) FROM experience_posts e
WHERE e.status = 'approved'
    AND (e.title ILIKE '%' || :query || '%' OR e.content ILIKE '%' || :query || '%');
"""

    elif type_filter == "knowledge":
        search_sql = """
WITH keywords AS (
    SELECT unnest(string_to_array(:query, ' ')) AS kw
),
results AS (
    SELECT
        k.id::text AS id,
        'knowledge' AS type,
        k.title,
        LEFT(k.content, 200) AS content,
        k.title AS highlight,
        (SELECT COUNT(*) FROM keywords kw WHERE k.title ILIKE '%' || kw.kw || '%' OR k.content ILIKE '%' || kw.kw || '%')::float /
            (SELECT COUNT(*) FROM keywords) AS score,
        jsonb_build_object(
            'category', k.category,
            'tags', k.tags,
            'source', k.source
        ) AS metadata
    FROM knowledge_articles k
    WHERE k.is_published = true
        AND (
            k.title ILIKE '%' || :query || '%'
            OR k.content ILIKE '%' || :query || '%'
        )
)
SELECT * FROM results ORDER BY score DESC LIMIT :page_size OFFSET :offset;
"""
        count_sql = """
SELECT COUNT(*) FROM knowledge_articles k
WHERE k.is_published = true
    AND (k.title ILIKE '%' || :query || '%' OR k.content ILIKE '%' || :query || '%');
"""

    elif type_filter == "qa":
        search_sql = """
WITH keywords AS (
    SELECT unnest(string_to_array(:query, ' ')) AS kw
),
results AS (
    SELECT
        q.id::text AS id,
        'qa' AS type,
        q.title,
        LEFT(q.content, 200) AS content,
        q.title AS highlight,
        (SELECT COUNT(*) FROM keywords kw WHERE q.title ILIKE '%' || kw.kw || '%' OR q.content ILIKE '%' || kw.kw || '%')::float /
            (SELECT COUNT(*) FROM keywords) AS score,
        jsonb_build_object(
            'tags', q.tags,
            'status', q.status,
            'view_count', q.view_count,
            'answer_count', q.answer_count,
            'is_resolved', q.is_resolved
        ) AS metadata
    FROM qas q
    WHERE q.status = 'approved'
        AND (
            q.title ILIKE '%' || :query || '%'
            OR q.content ILIKE '%' || :query || '%'
        )
)
SELECT * FROM results ORDER BY score DESC LIMIT :page_size OFFSET :offset;
"""
        count_sql = """
SELECT COUNT(*) FROM qas q
WHERE q.status = 'approved'
    AND (q.title ILIKE '%' || :query || '%' OR q.content ILIKE '%' || :query || '%');
"""

    elif type_filter == "dark":
        search_sql = """
WITH keywords AS (
    SELECT unnest(string_to_array(:query, ' ')) AS kw
),
results AS (
    SELECT
        d.id::text AS id,
        'dark' AS type,
        d.title,
        LEFT(d.content, 200) AS content,
        d.title AS highlight,
        (SELECT COUNT(*) FROM keywords kw WHERE d.title ILIKE '%' || kw.kw || '%' OR d.content ILIKE '%' || kw.kw || '%')::float /
            (SELECT COUNT(*) FROM keywords) AS score,
        jsonb_build_object(
            'stage', d.stage,
            'category', d.category,
            'importance', d.importance,
            'tags', d.tags
        ) AS metadata
    FROM dark_knowledge d
    WHERE (
        d.title ILIKE '%' || :query || '%'
        OR d.content ILIKE '%' || :query || '%'
    )
)
SELECT * FROM results ORDER BY score DESC LIMIT :page_size OFFSET :offset;
"""
        count_sql = """
SELECT COUNT(*) FROM dark_knowledge d
WHERE (d.title ILIKE '%' || :query || '%' OR d.content ILIKE '%' || :query || '%');
"""

    else:  # all
        search_sql = """
WITH keywords AS (
    SELECT unnest(string_to_array(:query, ' ')) AS kw
),
experience_results AS (
    SELECT
        e.id::text AS id,
        'experience' AS type,
        e.title,
        COALESCE(e.summary, LEFT(e.content, 200)) AS content,
        e.title AS highlight,
        (SELECT COUNT(*) FROM keywords kw WHERE e.title ILIKE '%' || kw.kw || '%' OR e.content ILIKE '%' || kw.kw || '%')::float /
            (SELECT COUNT(*) FROM keywords) AS score,
        jsonb_build_object(
            'category', e.category,
            'tags', e.tags,
            'status', e.status,
            'source_platform', e.source_platform
        ) AS metadata
    FROM experience_posts e
    WHERE e.status = 'approved'
        AND (e.title ILIKE '%' || :query || '%' OR e.content ILIKE '%' || :query || '%')
),
knowledge_results AS (
    SELECT
        k.id::text AS id,
        'knowledge' AS type,
        k.title,
        LEFT(k.content, 200) AS content,
        k.title AS highlight,
        (SELECT COUNT(*) FROM keywords kw WHERE k.title ILIKE '%' || kw.kw || '%' OR k.content ILIKE '%' || kw.kw || '%')::float /
            (SELECT COUNT(*) FROM keywords) AS score,
        jsonb_build_object(
            'category', k.category,
            'tags', k.tags,
            'source', k.source
        ) AS metadata
    FROM knowledge_articles k
    WHERE k.is_published = true
        AND (k.title ILIKE '%' || :query || '%' OR k.content ILIKE '%' || :query || '%')
),
qa_results AS (
    SELECT
        q.id::text AS id,
        'qa' AS type,
        q.title,
        LEFT(q.content, 200) AS content,
        q.title AS highlight,
        (SELECT COUNT(*) FROM keywords kw WHERE q.title ILIKE '%' || kw.kw || '%' OR q.content ILIKE '%' || kw.kw || '%')::float /
            (SELECT COUNT(*) FROM keywords) AS score,
        jsonb_build_object(
            'tags', q.tags,
            'status', q.status,
            'view_count', q.view_count,
            'answer_count', q.answer_count,
            'is_resolved', q.is_resolved
        ) AS metadata
    FROM qas q
    WHERE q.status = 'approved'
        AND (q.title ILIKE '%' || :query || '%' OR q.content ILIKE '%' || :query || '%')
),
dark_results AS (
    SELECT
        d.id::text AS id,
        'dark' AS type,
        d.title,
        LEFT(d.content, 200) AS content,
        d.title AS highlight,
        (SELECT COUNT(*) FROM keywords kw WHERE d.title ILIKE '%' || kw.kw || '%' OR d.content ILIKE '%' || kw.kw || '%')::float /
            (SELECT COUNT(*) FROM keywords) AS score,
        jsonb_build_object(
            'stage', d.stage,
            'category', d.category,
            'importance', d.importance,
            'tags', d.tags
        ) AS metadata
    FROM dark_knowledge d
    WHERE (d.title ILIKE '%' || :query || '%' OR d.content ILIKE '%' || :query || '%')
),
combined_results AS (
    SELECT * FROM experience_results
    UNION ALL
    SELECT * FROM knowledge_results
    UNION ALL
    SELECT * FROM qa_results
    UNION ALL
    SELECT * FROM dark_results
)
SELECT * FROM combined_results
ORDER BY score DESC
LIMIT :page_size OFFSET :offset;
"""
        count_sql = """
SELECT COUNT(*) FROM (
    SELECT 1 FROM experience_posts e
    WHERE e.status = 'approved'
        AND (e.title ILIKE '%' || :query || '%' OR e.content ILIKE '%' || :query || '%')
    UNION ALL
    SELECT 1 FROM knowledge_articles k
    WHERE k.is_published = true
        AND (k.title ILIKE '%' || :query || '%' OR k.content ILIKE '%' || :query || '%')
    UNION ALL
    SELECT 1 FROM qas q
    WHERE q.status = 'approved'
        AND (q.title ILIKE '%' || :query || '%' OR q.content ILIKE '%' || :query || '%')
    UNION ALL
    SELECT 1 FROM dark_knowledge d
    WHERE (d.title ILIKE '%' || :query || '%' OR d.content ILIKE '%' || :query || '%')
) t;
"""

    return search_sql, count_sql


# ------------------------------------------------------------------
# SQLite 版本：LIKE 回退（LIKE 在 SQLite 中默认不区分大小写）
# ------------------------------------------------------------------


def _build_sqlite_search_sql(type_filter: str) -> tuple[str, str]:
    """构建 SQLite 搜索 SQL（LIKE + CASE 简单评分 + json_object 元数据）。"""

    if type_filter == "experience":
        search_sql = """
WITH results AS (
    SELECT
        e.id AS id,
        'experience' AS type,
        e.title,
        COALESCE(e.summary, SUBSTR(e.content, 1, 200)) AS content,
        e.title AS highlight,
        CAST(
            (CASE WHEN e.title LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END) +
            (CASE WHEN e.content LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END)
        AS REAL) AS score,
        json_object(
            'category', e.category,
            'tags', COALESCE(e.tags, '[]'),
            'status', e.status,
            'source_platform', e.source_platform
        ) AS metadata
    FROM experience_posts e
    WHERE e.status = 'approved'
        AND (e.title LIKE '%' || :query || '%' OR e.content LIKE '%' || :query || '%')
)
SELECT * FROM results ORDER BY score DESC LIMIT :page_size OFFSET :offset;
"""
        count_sql = """
SELECT COUNT(*) FROM experience_posts e
WHERE e.status = 'approved'
    AND (e.title LIKE '%' || :query || '%' OR e.content LIKE '%' || :query || '%');
"""

    elif type_filter == "knowledge":
        search_sql = """
WITH results AS (
    SELECT
        k.id AS id,
        'knowledge' AS type,
        k.title,
        SUBSTR(k.content, 1, 200) AS content,
        k.title AS highlight,
        CAST(
            (CASE WHEN k.title LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END) +
            (CASE WHEN k.content LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END)
        AS REAL) AS score,
        json_object(
            'category', k.category,
            'tags', COALESCE(k.tags, '[]'),
            'source', k.source
        ) AS metadata
    FROM knowledge_articles k
    WHERE k.is_published = 1
        AND (k.title LIKE '%' || :query || '%' OR k.content LIKE '%' || :query || '%')
)
SELECT * FROM results ORDER BY score DESC LIMIT :page_size OFFSET :offset;
"""
        count_sql = """
SELECT COUNT(*) FROM knowledge_articles k
WHERE k.is_published = 1
    AND (k.title LIKE '%' || :query || '%' OR k.content LIKE '%' || :query || '%');
"""

    elif type_filter == "qa":
        search_sql = """
WITH results AS (
    SELECT
        q.id AS id,
        'qa' AS type,
        q.title,
        SUBSTR(q.content, 1, 200) AS content,
        q.title AS highlight,
        CAST(
            (CASE WHEN q.title LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END) +
            (CASE WHEN q.content LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END)
        AS REAL) AS score,
        json_object(
            'tags', COALESCE(q.tags, '[]'),
            'status', q.status,
            'view_count', q.view_count,
            'answer_count', q.answer_count,
            'is_resolved', CASE WHEN q.is_resolved THEN 1 ELSE 0 END
        ) AS metadata
    FROM qas q
    WHERE q.status = 'approved'
        AND (q.title LIKE '%' || :query || '%' OR q.content LIKE '%' || :query || '%')
)
SELECT * FROM results ORDER BY score DESC LIMIT :page_size OFFSET :offset;
"""
        count_sql = """
SELECT COUNT(*) FROM qas q
WHERE q.status = 'approved'
    AND (q.title LIKE '%' || :query || '%' OR q.content LIKE '%' || :query || '%');
"""

    elif type_filter == "dark":
        search_sql = """
WITH results AS (
    SELECT
        d.id AS id,
        'dark' AS type,
        d.title,
        SUBSTR(d.content, 1, 200) AS content,
        d.title AS highlight,
        CAST(
            (CASE WHEN d.title LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END) +
            (CASE WHEN d.content LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END)
        AS REAL) AS score,
        json_object(
            'stage', d.stage,
            'category', d.category,
            'importance', d.importance,
            'tags', COALESCE(d.tags, '[]')
        ) AS metadata
    FROM dark_knowledge d
    WHERE (d.title LIKE '%' || :query || '%' OR d.content LIKE '%' || :query || '%')
)
SELECT * FROM results ORDER BY score DESC LIMIT :page_size OFFSET :offset;
"""
        count_sql = """
SELECT COUNT(*) FROM dark_knowledge d
WHERE (d.title LIKE '%' || :query || '%' OR d.content LIKE '%' || :query || '%');
"""

    else:  # all
        search_sql = """
WITH
experience_results AS (
    SELECT
        e.id AS id,
        'experience' AS type,
        e.title,
        COALESCE(e.summary, SUBSTR(e.content, 1, 200)) AS content,
        e.title AS highlight,
        CAST(
            (CASE WHEN e.title LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END) +
            (CASE WHEN e.content LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END)
        AS REAL) AS score,
        json_object(
            'category', e.category,
            'tags', COALESCE(e.tags, '[]'),
            'status', e.status,
            'source_platform', e.source_platform
        ) AS metadata
    FROM experience_posts e
    WHERE e.status = 'approved'
        AND (e.title LIKE '%' || :query || '%' OR e.content LIKE '%' || :query || '%')
),
knowledge_results AS (
    SELECT
        k.id AS id,
        'knowledge' AS type,
        k.title,
        SUBSTR(k.content, 1, 200) AS content,
        k.title AS highlight,
        CAST(
            (CASE WHEN k.title LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END) +
            (CASE WHEN k.content LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END)
        AS REAL) AS score,
        json_object(
            'category', k.category,
            'tags', COALESCE(k.tags, '[]'),
            'source', k.source
        ) AS metadata
    FROM knowledge_articles k
    WHERE k.is_published = 1
        AND (k.title LIKE '%' || :query || '%' OR k.content LIKE '%' || :query || '%')
),
qa_results AS (
    SELECT
        q.id AS id,
        'qa' AS type,
        q.title,
        SUBSTR(q.content, 1, 200) AS content,
        q.title AS highlight,
        CAST(
            (CASE WHEN q.title LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END) +
            (CASE WHEN q.content LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END)
        AS REAL) AS score,
        json_object(
            'tags', COALESCE(q.tags, '[]'),
            'status', q.status,
            'view_count', q.view_count,
            'answer_count', q.answer_count,
            'is_resolved', CASE WHEN q.is_resolved THEN 1 ELSE 0 END
        ) AS metadata
    FROM qas q
    WHERE q.status = 'approved'
        AND (q.title LIKE '%' || :query || '%' OR q.content LIKE '%' || :query || '%')
),
dark_results AS (
    SELECT
        d.id AS id,
        'dark' AS type,
        d.title,
        SUBSTR(d.content, 1, 200) AS content,
        d.title AS highlight,
        CAST(
            (CASE WHEN d.title LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END) +
            (CASE WHEN d.content LIKE '%' || :query || '%' THEN 0.5 ELSE 0 END)
        AS REAL) AS score,
        json_object(
            'stage', d.stage,
            'category', d.category,
            'importance', d.importance,
            'tags', COALESCE(d.tags, '[]')
        ) AS metadata
    FROM dark_knowledge d
    WHERE (d.title LIKE '%' || :query || '%' OR d.content LIKE '%' || :query || '%')
),
combined_results AS (
    SELECT * FROM experience_results
    UNION ALL
    SELECT * FROM knowledge_results
    UNION ALL
    SELECT * FROM qa_results
    UNION ALL
    SELECT * FROM dark_results
)
SELECT * FROM combined_results
ORDER BY score DESC
LIMIT :page_size OFFSET :offset;
"""
        count_sql = """
SELECT COUNT(*) FROM (
    SELECT 1 FROM experience_posts e
    WHERE e.status = 'approved'
        AND (e.title LIKE '%' || :query || '%' OR e.content LIKE '%' || :query || '%')
    UNION ALL
    SELECT 1 FROM knowledge_articles k
    WHERE k.is_published = 1
        AND (k.title LIKE '%' || :query || '%' OR k.content LIKE '%' || :query || '%')
    UNION ALL
    SELECT 1 FROM qas q
    WHERE q.status = 'approved'
        AND (q.title LIKE '%' || :query || '%' OR q.content LIKE '%' || :query || '%')
    UNION ALL
    SELECT 1 FROM dark_knowledge d
    WHERE (d.title LIKE '%' || :query || '%' OR d.content LIKE '%' || :query || '%')
) t;
"""

    return search_sql, count_sql


# ======================================================================
# API 端点
# ======================================================================


@router.get("/api/search", response_model=SearchResponse)
def full_text_search(
    q: str = Query(..., min_length=1, max_length=200, description="搜索关键词"),
    type: Literal["all", "experience", "knowledge", "qa", "dark"] = Query(
        "all", description="搜索类型过滤"
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """全文搜索 — 兼容 PostgreSQL（pg_trgm GIN 索引加速）与 SQLite（LIKE 回退）。

    支持搜索类型:
    - all: 搜索所有类型（经验帖、知识文章、问答、暗知识）
    - experience: 仅搜索经验帖
    - knowledge: 仅搜索知识文章
    - qa: 仅搜索问答
    - dark: 仅搜索暗知识

    返回结果包含:
    - 搜索结果列表（按相关度排序）
    - 高亮片段
    - 分页信息
    """
    try:
        offset = (page - 1) * page_size

        # 构建 SQL（自动检测 PostgreSQL / SQLite）
        search_sql, count_sql = _build_search_sql(type)

        # 执行计数查询
        total = db.execute(text(count_sql), {"query": q}).scalar() or 0

        # 执行搜索查询
        rows = db.execute(
            text(search_sql),
            {"query": q, "page_size": page_size, "offset": offset}
        ).fetchall()

        # 构建结果
        results = []
        for row in rows:
            # SQLite json_object 返回字符串，需要解析；PostgreSQL 返回 dict
            metadata = row.metadata
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            elif not isinstance(metadata, dict):
                metadata = {}

            results.append(SearchResultItem(
                id=str(row.id),
                type=row.type,
                title=row.title,
                content=row.content,
                highlight=row.highlight,
                score=round(float(row.score), 4),
                metadata=metadata,
            ))

        return SearchResponse(
            query=q,
            type=type,
            total=total,
            page=page,
            page_size=page_size,
            results=results,
        )

    except Exception as e:
        logger.exception("全文搜索失败: %s", e)
        raise HTTPException(
            status_code=500,
            detail="搜索服务异常，请稍后重试",
        )
