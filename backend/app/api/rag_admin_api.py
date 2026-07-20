"""RAG 管理 API — 管理员专用的向量索引管理。"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["RAG 管理"])


class RAGStatsResponse(BaseModel):
    """RAG 系统统计响应。"""
    total_embeddings: int
    source_counts: dict
    last_rebuild: str | None
    embedding_model: str


class RebuildRequest(BaseModel):
    """重建向量索引请求。"""
    clear_existing: bool = True
    sources: list[str] | None = None  # None = 全部


@router.get("/api/admin/rag/stats", response_model=RAGStatsResponse)
def get_rag_stats(
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """获取 RAG 系统统计 — 管理员专用。"""
    # 统计各表向量数
    result = db.execute(text("""
        SELECT source_table, COUNT(*) as count
        FROM document_embeddings
        GROUP BY source_table
    """))
    source_counts = {row.source_table: row.count for row in result}

    total = sum(source_counts.values())

    # 获取最后重建时间
    last_rebuild = db.execute(text("""
        SELECT MAX(created_at) FROM document_embeddings
    """)).scalar()

    return RAGStatsResponse(
        total_embeddings=total,
        source_counts=source_counts,
        last_rebuild=str(last_rebuild) if last_rebuild else None,
        embedding_model="BAAI/bge-large-zh-v1.5",
    )


@router.post("/api/admin/rag/rebuild")
def rebuild_rag_index(
    body: RebuildRequest,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """重建 RAG 向量索引 — 管理员专用。

    执行全量向量化，可能需要较长时间。
    """
    try:
        # 清空现有向量
        if body.clear_existing:
            db.execute(text("DELETE FROM document_embeddings"))
            db.commit()
            logger.info("已清空现有向量数据")

        # 执行向量化脚本
        import subprocess
        result = subprocess.run(
            ["python", "scripts/vectorize_data.py"],
            capture_output=True,
            text=True,
            timeout=3600,  # 1 小时超时
        )

        if result.returncode != 0:
            # 修复: FASTAPI-RESP-001 — 不向客户端泄漏 subprocess stderr，
            # 内部错误细节仅记录到服务端日志
            logger.error("向量化脚本执行失败 returncode=%s stderr=%s", result.returncode, result.stderr)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="向量化失败，请查看服务端日志",
            )

        logger.info("向量化脚本执行成功")
        return {"status": "success", "message": "向量索引重建完成"}

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="向量化任务超时，请稍后重试",
        )
    except HTTPException:
        raise
    except Exception as e:
        # 修复: FASTAPI-RESP-001 — 不向客户端泄漏内部异常信息，仅记录日志
        logger.exception("重建向量索引失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重建失败，请稍后重试",
        )


@router.get("/api/admin/rag/search-test")
def test_rag_search(
    query: str,
    top_k: int = 5,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """测试 RAG 检索 — 管理员专用。"""
    from app.rag_service import get_rag_service

    rag = get_rag_service(db)
    results = rag.search(query, top_k=top_k)

    return {
        "query": query,
        "results": results,
        "count": len(results),
    }
