"""RAG Engine - Hybrid search across GradPath's 200K+ records.

Combines keyword search (LOWER() + LIKE across content tables, cross-DB compatible)
with semantic search (document_embeddings vector search) for maximum recall.

修复 bug: 原先使用 PostgreSQL 专有的 ILIKE 语法，SQLite 不支持，
导致 keyword search 抛 OperationalError -> 整个 RAG 流程失败 -> LLM 超时。
改用 LOWER() + LIKE 实现跨数据库大小写不敏感匹配。
"""
import logging
from dataclasses import dataclass, field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

_MAX_QUERY_LEN = 200


def _escape_like(s: str) -> str:
    """Escape SQL LIKE special characters (%, _) so they are treated as literals."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _is_sqlite() -> bool:
    """检测当前数据库是否为 SQLite（开发环境兼容性判断）。"""
    return settings.DATABASE_URL.startswith("sqlite")

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    content: str
    source_type: str  # experience/knowledge/qa/dark/intel
    source_id: str
    title: str = ""
    score: float = 0.0
    metadata: dict = field(default_factory=dict)


class RAGEngine:
    """Hybrid search: keyword (ILIKE) + semantic (embeddings vector cosine)."""

    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        query: str,
        top_k: int = 10,
        source_types: list[str] | None = None,
        use_semantic: bool = True,
    ) -> list[RAGResult]:
        """Search across all content tables using hybrid keyword + semantic matching.

        Args:
            query: user search query
            top_k: max results to return
            source_types: filter to specific source types (None = all)
            use_semantic: if True, also run vector search when embeddings exist
        """
        if not query or not query.strip():
            return []

        if len(query) > _MAX_QUERY_LEN:
            query = query[:_MAX_QUERY_LEN]

        if not source_types:
            source_types = ["experience", "knowledge", "qa", "dark"]

        results: list[RAGResult] = []

        # --- keyword search across content tables ---
        keywords = [k.strip() for k in query.split() if len(k.strip()) >= 2]
        if not keywords:
            keywords = [query]

        # 修复 bug: 使用 LOWER() + LIKE 替代 ILIKE，兼容 SQLite 和 PostgreSQL
        # SQLite 不支持 ILIKE，会抛 OperationalError；LOWER() + LIKE 在两者下都能工作
        keyword_cond = " OR ".join(
            [f"(LOWER(title) LIKE '%' || LOWER(:kw{i}) || '%' OR LOWER(content) LIKE '%' || LOWER(:kw{i}) || '%')"
             for i in range(len(keywords))]
        )
        keyword_params = {f"kw{i}": _escape_like(k) for i, k in enumerate(keywords)}

        if "experience" in source_types:
            results.extend(self._search_experience(keyword_cond, keyword_params, top_k))

        if "knowledge" in source_types:
            results.extend(self._search_knowledge(keyword_cond, keyword_params, top_k))

        if "qa" in source_types:
            results.extend(self._search_qa(keyword_cond, keyword_params, top_k))

        if "dark" in source_types:
            results.extend(self._search_dark(keyword_cond, keyword_params, top_k))

        # --- semantic search (optional, when embeddings table exists) ---
        if use_semantic:
            results.extend(self._search_semantic(query, top_k, source_types))

        # deduplicate by (source_type, source_id), keeping higher score
        seen: dict[tuple[str, str], RAGResult] = {}
        for r in results:
            key = (r.source_type, r.source_id)
            if key not in seen or r.score > seen[key].score:
                seen[key] = r

        deduped = list(seen.values())
        deduped.sort(key=lambda x: x.score, reverse=True)
        return deduped[:top_k]

    # ------------------------------------------------------------------
    # Keyword search per table
    # ------------------------------------------------------------------

    def _search_experience(self, keyword_cond: str, keyword_params: dict, limit: int) -> list[RAGResult]:
        sql = text(
            f"SELECT id, title, content, source_platform FROM experience_posts "
            f"WHERE ({keyword_cond}) LIMIT :limit"
        )
        try:
            params = {"limit": limit, **keyword_params}
            return [
                RAGResult(
                    content=row[2][:2000] if row[2] else "",
                    source_type="experience",
                    source_id=str(row[0]),
                    title=row[1] or "",
                    score=1.0,
                    metadata={"source_platform": row[3] or ""},
                )
                for row in self.db.execute(sql, params).fetchall()
            ]
        except Exception as e:
            logger.warning("experience keyword search failed: %s", e)
            return []

    def _search_knowledge(self, keyword_cond: str, keyword_params: dict, limit: int) -> list[RAGResult]:
        sql = text(
            f"SELECT id, title, content, category FROM knowledge_articles "
            f"WHERE ({keyword_cond}) LIMIT :limit"
        )
        try:
            params = {"limit": limit, **keyword_params}
            return [
                RAGResult(
                    content=row[2][:2000] if row[2] else "",
                    source_type="knowledge",
                    source_id=str(row[0]),
                    title=row[1] or "",
                    score=1.0,
                    metadata={"category": row[3] or ""},
                )
                for row in self.db.execute(sql, params).fetchall()
            ]
        except Exception as e:
            logger.warning("knowledge keyword search failed: %s", e)
            return []

    def _search_qa(self, keyword_cond: str, keyword_params: dict, limit: int) -> list[RAGResult]:
        sql = text(
            f"SELECT id, title, content FROM qas "
            f"WHERE ({keyword_cond}) LIMIT :limit"
        )
        try:
            params = {"limit": limit, **keyword_params}
            return [
                RAGResult(
                    content=row[2][:2000] if row[2] else "",
                    source_type="qa",
                    source_id=str(row[0]),
                    title=row[1] or "",
                    score=0.8,
                )
                for row in self.db.execute(sql, params).fetchall()
            ]
        except Exception as e:
            logger.warning("qa keyword search failed: %s", e)
            return []

    def _search_dark(self, keyword_cond: str, keyword_params: dict, limit: int) -> list[RAGResult]:
        sql = text(
            f"SELECT id, title, content, stage FROM dark_knowledge "
            f"WHERE ({keyword_cond}) LIMIT :limit"
        )
        try:
            params = {"limit": limit, **keyword_params}
            return [
                RAGResult(
                    content=row[2][:2000] if row[2] else "",
                    source_type="dark",
                    source_id=str(row[0]),
                    title=row[1] or "",
                    score=1.2,
                    metadata={"stage": row[3] or ""},
                )
                for row in self.db.execute(sql, params).fetchall()
            ]
        except Exception as e:
            logger.warning("dark keyword search failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Semantic search (vector cosine via pgvector)
    # ------------------------------------------------------------------

    def _search_semantic(
        self, query: str, top_k: int, source_types: list[str]
    ) -> list[RAGResult]:
        """Run vector search over document_embeddings table."""
        try:
            from app.services.rag_service import RAGService

            rag_svc = RAGService(self.db)
            vec_results = rag_svc.search(query, top_k=top_k)
        except Exception as e:
            logger.debug("semantic search unavailable: %s", e)
            return []

        results: list[RAGResult] = []
        source_type_map = {
            "experience_posts": "experience",
            "knowledge_articles": "knowledge",
            "qas": "qa",
            "dark_knowledge": "dark",
        }
        for r in vec_results:
            mapped_type = source_type_map.get(r["source_table"], r["source_table"])
            if mapped_type not in source_types:
                continue
            meta = r.get("metadata") or {}
            results.append(
                RAGResult(
                    content=r["content"][:2000],
                    source_type=mapped_type,
                    source_id=r["id"],
                    title=meta.get("title", ""),
                    score=0.7 + float(r.get("similarity", 0)) * 0.3,
                    metadata=meta,
                )
            )
        return results
