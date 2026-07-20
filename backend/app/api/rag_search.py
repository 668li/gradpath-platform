"""RAG Search API - search across all GradPath data with AI-synthesizable context."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.rag_engine import RAGEngine, RAGResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["RAG"])

SOURCE_LABELS = {
    "experience": "经验帖",
    "knowledge": "知识文章",
    "qa": "问答",
    "dark": "暗知识",
}


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    top_k: int = 10
    source_types: list[str] = ["experience", "knowledge", "qa", "dark"]
    use_semantic: bool = True


class RAGSearchResult(BaseModel):
    content: str
    source_type: str
    source_id: str = ""
    title: str = ""
    score: float = 0.0
    metadata: dict = {}


class RAGSearchResponse(BaseModel):
    query: str
    total: int
    results: list[RAGSearchResult]
    context: str  # Combined context string for LLM consumption


@router.post("/search", response_model=RAGSearchResponse)
def rag_search(req: RAGSearchRequest, db: Session = Depends(get_db)):
    """Hybrid RAG search — keyword + semantic over 200K+ records.

    Returns structured results plus a pre-built context string ready
    to inject into an LLM prompt.
    """
    try:
        engine = RAGEngine(db)
        results = engine.search(
            req.query,
            top_k=req.top_k,
            source_types=req.source_types,
            use_semantic=req.use_semantic,
        )
    except Exception as e:
        # 修复: FASTAPI-RESP-001 — 不向客户端泄漏内部异常信息，仅记录日志
        logger.exception("RAG engine error: %s", e)
        raise HTTPException(status_code=500, detail="RAG 检索失败，请稍后重试")

    # Build context string for LLM
    context_parts: list[str] = []
    for r in results:
        label = SOURCE_LABELS.get(r.source_type, r.source_type)
        snippet = r.content[:500] if r.content else ""
        context_parts.append(f"[{label}] {r.title}: {snippet}")

    return RAGSearchResponse(
        query=req.query,
        total=len(results),
        results=[
            RAGSearchResult(
                content=r.content[:1000],
                source_type=r.source_type,
                source_id=r.source_id,
                title=r.title,
                score=r.score,
                metadata=r.metadata,
            )
            for r in results
        ],
        context="\n\n".join(context_parts),
    )


@router.get("/search")
def rag_search_get(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    top_k: int = Query(10, ge=1, le=50),
    use_semantic: bool = Query(True),
    db: Session = Depends(get_db),
):
    """GET variant of RAG search for quick testing."""
    try:
        engine = RAGEngine(db)
        results = engine.search(q, top_k=top_k, use_semantic=use_semantic)
    except Exception as e:
        # 修复: FASTAPI-RESP-001 — 不向客户端泄漏内部异常信息，仅记录日志
        logger.exception("RAG engine error: %s", e)
        raise HTTPException(status_code=500, detail="RAG 检索失败，请稍后重试")

    context_parts: list[str] = []
    for r in results:
        label = SOURCE_LABELS.get(r.source_type, r.source_type)
        snippet = r.content[:500] if r.content else ""
        context_parts.append(f"[{label}] {r.title}: {snippet}")

    return {
        "query": q,
        "total": len(results),
        "results": [
            {
                "content": r.content[:1000],
                "source_type": r.source_type,
                "source_id": r.source_id,
                "title": r.title,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in results
        ],
        "context": "\n\n".join(context_parts),
    }
