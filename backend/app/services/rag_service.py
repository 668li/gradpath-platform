"""RAG 服务 — 检索增强生成的核心逻辑。

支持:
- 文档向量化（Embedding 生成）
- 向量检索（余弦相似度）
- 元数据过滤
- 上下文构建与 LLM 生成
"""
import logging
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)

# Embedding 模型（延迟加载）
_embedding_model = None


def _get_embedding_model():
    """延迟加载 Embedding 模型。

    修复 bug: 模型未安装/未下载时，原实现直接 raise 导致上层 search() 超时。
    现改为返回 None，让上层走 fallback 路径。
    """
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_name = getattr(settings, "EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
            _embedding_model = SentenceTransformer(model_name)
            logger.info("Embedding 模型加载完成: %s", model_name)
        except ImportError:
            logger.warning(
                "sentence-transformers 未安装，RAG 将降级为关键词搜索。"
                "安装: pip install sentence-transformers"
            )
            return None
        except Exception as e:
            logger.warning(
                "Embedding 模型加载失败（%s），RAG 将降级为关键词搜索: %s",
                type(e).__name__, e
            )
            return None
    return _embedding_model


def _is_sqlite() -> bool:
    """检测当前数据库是否为 SQLite（开发环境常用，不支持 pgvector）。"""
    return settings.DATABASE_URL.startswith("sqlite")


class RAGService:
    """RAG 检索服务。"""

    def __init__(self, db: Session):
        self.db = db

    def embed_text(self, text_content: str) -> list[float] | None:
        """将文本转换为向量。

        修复 bug: 模型不可用时返回 None 而非抛异常，让上层走 fallback。
        """
        model = _get_embedding_model()
        if model is None:
            return None
        embedding = model.encode(text_content, normalize_embeddings=True)
        return embedding.tolist()

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.3,
    ) -> list[dict]:
        """向量检索 — 返回最相关的文档。

        Args:
            query: 用户查询
            top_k: 返回结果数量
            filters: 元数据过滤条件 (school, year, source 等)
            score_threshold: 最低相似度阈值

        Returns:
            检索结果列表，每项包含 content, metadata, similarity
        """
        # 修复 bug: SQLite 不支持 pgvector，sentence-transformers 未安装时也无法向量检索。
        # 直接降级为关键词搜索，避免 30 秒超时让用户以为系统挂了。
        if _is_sqlite():
            logger.info("SQLite 环境，RAG 直接走关键词搜索降级路径")
            return self._fallback_search(query, top_k, filters)

        # 1. 生成查询向量
        query_embedding = self.embed_text(query)
        if query_embedding is None:
            # 模型不可用，降级
            return self._fallback_search(query, top_k, filters)
        embedding_str = str(query_embedding)

        # 修复: FASTAPI-INJECT-001 — 所有用户可控输入（embedding_str / filters）
        # 必须通过 SQLAlchemy 参数绑定传入，禁止字符串拼接。
        # 此处使用 text() + bindparams() 显式声明参数与类型，
        # 防止 SQL 注入（即便 embedding 来自模型输出，filters 来自用户）。
        sql = """
            SELECT id, source_table, source_id, chunk_index, content, doc_metadata,
                   1 - (embedding_vector::vector <=> CAST(:embedding AS vector)) AS similarity
            FROM document_embeddings
            WHERE embedding_vector IS NOT NULL
        """
        params: dict[str, Any] = {"embedding": embedding_str}

        # 3. 添加过滤条件（均使用 :param 绑定，非字符串拼接）
        if filters:
            if filters.get("school"):
                sql += " AND doc_metadata->>'school_name' = :school"
                params["school"] = filters["school"]
            if filters.get("year"):
                sql += " AND doc_metadata->>'year' = :year"
                params["year"] = str(filters["year"])
            if filters.get("source"):
                sql += " AND source_table = :source"
                params["source"] = filters["source"]

        # 4. 排序 + 限制
        sql += " ORDER BY embedding_vector::vector <=> CAST(:embedding AS vector) LIMIT :limit"
        params["limit"] = top_k

        # 5. 执行查询（显式 bindparams，确保所有参数都被正确转义）
        try:
            bindparams_list = [bindparam(k) for k in params.keys()]
            result = self.db.execute(text(sql).bindparams(*bindparams_list), params)
            rows = result.fetchall()
        except Exception as e:
            logger.error("向量检索失败: %s", e)
            # 降级为关键词搜索
            return self._fallback_search(query, top_k, filters)

        # 6. 格式化结果
        results = []
        for row in rows:
            similarity = float(row.similarity) if row.similarity else 0
            if similarity >= score_threshold:
                results.append({
                    "id": str(row.id),
                    "source_table": row.source_table,
                    "content": row.content,
                    "metadata": row.doc_metadata,
                    "similarity": round(similarity, 4),
                })

        return results

    def _fallback_search(
        self, query: str, top_k: int, filters: dict | None
    ) -> list[dict]:
        """降级搜索 — 当向量检索不可用时，使用关键词匹配。"""
        # 修复 bug: ILIKE 是 PostgreSQL 特定语法，SQLite 不支持。
        # SQLite 用 LIKE（默认大小写不敏感对 ASCII，对中文无影响）；
        # PostgreSQL 用 ILIKE 保证大小写不敏感。
        # 修复 bug: doc_metadata->>'key' 是 PostgreSQL JSON 语法，SQLite 用 json_extract。
        if _is_sqlite():
            sql = """
                SELECT id, source_table, content, doc_metadata
                FROM document_embeddings
                WHERE content LIKE :query
            """
        else:
            sql = """
                SELECT id, source_table, content, doc_metadata
                FROM document_embeddings
                WHERE content ILIKE :query
            """
        params = {"query": f"%{query}%"}

        if filters:
            if filters.get("school"):
                if _is_sqlite():
                    sql += " AND json_extract(doc_metadata, '$.school_name') = :school"
                else:
                    sql += " AND doc_metadata->>'school_name' = :school"
                params["school"] = filters["school"]
            if filters.get("source"):
                sql += " AND source_table = :source"
                params["source"] = filters["source"]

        sql += " LIMIT :limit"
        params["limit"] = top_k

        try:
            bindparams_list = [bindparam(k) for k in params.keys()]
            result = self.db.execute(text(sql).bindparams(*bindparams_list), params)
            rows = result.fetchall()
            return [
                {
                    "id": str(row.id),
                    "source_table": row.source_table,
                    "content": row.content,
                    "metadata": row.doc_metadata,
                    "similarity": 0.5,  # 关键词匹配给予中等相似度
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("降级搜索也失败: %s", e)
            return []

    def build_context(self, results: list[dict], max_tokens: int = 3000) -> str:
        """将检索结果构建为 LLM 上下文。"""
        context_parts = []
        current_tokens = 0

        for r in results:
            # 简单估算 token 数（中文约 1.5 字符/token）
            content = r["content"]
            estimated_tokens = len(content) / 1.5

            if current_tokens + estimated_tokens > max_tokens:
                break

            source = r["source_table"]
            similarity = r.get("similarity", 0)
            context_parts.append(
                f"[来源: {source} | 相关度: {similarity:.2f}]\n{content}"
            )
            current_tokens += estimated_tokens

        return "\n\n---\n\n".join(context_parts)


def get_rag_service(db: Session) -> RAGService:
    """获取 RAG 服务实例。"""
    return RAGService(db)
