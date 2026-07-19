"""AI Agent API — unified endpoint combining DB search + web search + LLM.

Endpoints:
    POST /api/ai/agent          — answer a question (DB + optional web search + LLM)
    GET  /api/ai/agent/web-search — test web search independently
"""
import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.database import get_db, SessionLocal
from app.models.user import User
from app.services.ai_butler_service import route_agent, scan_user
from app.services.ai_service import AIService
from app.services.web_search import WebSearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/agent", tags=["AI Agent"])

# ---------------------------------------------------------------------------
# Singleton services (created once at import time)
# ---------------------------------------------------------------------------
_ai = AIService()
_web_search = WebSearchService()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class AgentRequest(BaseModel):
    question: str
    search_web: bool = True
    context: Optional[str] = None


class SourceItem(BaseModel):
    type: Literal["db", "web"]
    title: str = ""
    content: str = ""
    url: str = ""


class AgentResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    confidence: float


class WebSearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str


# ---------------------------------------------------------------------------
# Helpers — DB search (reuses patterns from app/api/search.py)
# ---------------------------------------------------------------------------

def _db_search(query: str, limit: int = 5) -> list[dict]:
    """Search experience_posts, knowledge_articles, qas, dark_knowledge."""
    db = SessionLocal()
    results: list[dict] = []
    try:
        search_sql = """
WITH experience_results AS (
    SELECT 'experience' AS type, e.title,
           COALESCE(e.summary, LEFT(e.content, 300)) AS content,
           '' AS url
    FROM experience_posts e
    WHERE e.status = 'approved'
      AND (e.title ILIKE '%' || :q || '%' OR e.content ILIKE '%' || :q || '%')
    LIMIT :lim
),
knowledge_results AS (
    SELECT 'knowledge' AS type, k.title,
           LEFT(k.content, 300) AS content,
           COALESCE(k.source, '') AS url
    FROM knowledge_articles k
    WHERE k.is_published = true
      AND (k.title ILIKE '%' || :q || '%' OR k.content ILIKE '%' || :q || '%')
    LIMIT :lim
),
qa_results AS (
    SELECT 'qa' AS type, q.title,
           LEFT(q.content, 300) AS content,
           '' AS url
    FROM qas q
    WHERE q.status = 'approved'
      AND (q.title ILIKE '%' || :q || '%' OR q.content ILIKE '%' || :q || '%')
    LIMIT :lim
),
dark_results AS (
    SELECT 'dark' AS type, d.title,
           LEFT(d.content, 300) AS content,
           '' AS url
    FROM dark_knowledge d
    WHERE d.title ILIKE '%' || :q || '%' OR d.content ILIKE '%' || :q || '%'
    LIMIT :lim
),
combined AS (
    SELECT * FROM experience_results
    UNION ALL SELECT * FROM knowledge_results
    UNION ALL SELECT * FROM qa_results
    UNION ALL SELECT * FROM dark_results
)
SELECT * FROM combined LIMIT :total;
"""
        rows = db.execute(
            text(search_sql),
            {"q": query, "lim": limit, "total": limit * 2},
        ).fetchall()
        for r in rows:
            results.append({
                "type": r.type,
                "title": r.title or "",
                "content": r.content or "",
                "url": r.url or "",
            })
    except Exception as e:
        logger.error("DB search failed: %s", e)
    finally:
        db.close()
    return results


# ---------------------------------------------------------------------------
# Intent classification (simple keyword-based)
# ---------------------------------------------------------------------------

def _classify_intent(question: str) -> str:
    """Classify question intent into one of: 考研 / 考公 / 就业 / 通用."""
    q = question.lower()
    if any(kw in q for kw in ("考研", "初试", "复试", "分数线", "调剂", "研究生", "导师", "院校")):
        return "考研"
    if any(kw in q for kw in ("考公", "公务员", "国考", "省考", "行测", "申论")):
        return "考公"
    if any(kw in q for kw in ("就业", "找工作", "简历", "面试", "实习", "offer", "薪资")):
        return "就业"
    return "通用"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/web-search")
async def web_search_endpoint(q: str = Query(..., min_length=1, max_length=200)):
    """Test web search independently."""
    results = await _web_search.search(q, max_results=5)
    return {
        "results": [
            {"title": r.title, "url": r.url, "snippet": r.snippet}
            for r in results
        ]
    }


class ScanResponse(BaseModel):
    profile: dict
    plan: list[dict]
    generated_at: str
    llm_enriched: bool


class PersonalAgentRequest(BaseModel):
    message: str
    web_search: bool = True


class PersonalAgentResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    confidence: float
    intent: str


@router.get("/scan", response_model=ScanResponse)
async def scan_endpoint(
    db=Depends(get_db),
    user: User = Depends(get_current_user),
):
    """扫描当前用户全量数据，返回结构化画像 + 行动清单（AI 管家核心）。"""
    return scan_user(db, user.id)


@router.post("/chat", response_model=PersonalAgentResponse)
async def personal_agent_endpoint(
    body: PersonalAgentRequest,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
):
    """个性化 Agent：注入当前用户上下文回答（AI 管家对话）。"""
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message 不能为空")
    return route_agent(db, user.id, message, web_search=body.web_search)


@router.post("", response_model=AgentResponse)
async def agent_endpoint(body: AgentRequest):
    """Unified AI Agent — answer a question using DB + web + LLM.

    Flow:
    1. Classify intent
    2. Search DB for relevant content
    3. Optionally search the web
    4. Build context and call GLM-4
    5. Return answer with sources
    """
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question 不能为空")

    intent = _classify_intent(question)
    logger.info("Agent: intent=%s, question=%s", intent, question[:80])

    # --- 1. DB search ---
    db_results = _db_search(question, limit=5)

    # --- 2. Web search (optional) ---
    web_results: list[dict] = []
    if body.search_web:
        web_hits = await _web_search.search(question, max_results=5)
        web_results = [
            {"title": h.title, "content": h.snippet, "url": h.url}
            for h in web_hits
        ]

    # --- 3. Build context ---
    all_sources: list[SourceItem] = []
    context_parts: list[str] = []

    for i, item in enumerate(db_results, 1):
        all_sources.append(SourceItem(type="db", title=item["title"],
                                      content=item["content"], url=item["url"]))
        context_parts.append(f"[DB#{i}] {item['title']}: {item['content'][:200]}")

    for i, item in enumerate(web_results, 1):
        all_sources.append(SourceItem(type="web", title=item["title"],
                                      content=item["content"], url=item["url"]))
        context_parts.append(f"[Web#{i}] {item['title']}: {item['content'][:200]}")

    if body.context:
        context_parts.append(f"[用户补充] {body.context}")

    context_block = "\n".join(context_parts) if context_parts else "（暂无相关资料）"

    # --- 4. Call LLM ---
    system_prompt = f"""你是 GradPath 职业规划平台的 AI 助手，专注帮助学生进行考研、考公、就业规划。

当前问题分类: {intent}

回答要求:
- 基于提供的资料回答，优先引用资料中的内容
- 如果资料不足，可以结合你的知识补充，但要说明哪些信息来自资料、哪些是通用建议
- 用中文回答，语气专业但亲切
- 回答要有条理，适当使用要点列表
- 如果问题涉及具体数据（分数线、录取率等），尽量给出准确信息"""

    user_prompt = f"""用户问题: {question}

参考资料:
{context_block}

请基于以上资料回答用户问题。"""

    try:
        answer = _ai.chat(system_prompt, user_prompt, timeout=30)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        # Graceful fallback — return what we have without LLM
        if all_sources:
            answer = f"以下是与「{question}」相关的信息（AI 生成暂时不可用）：\n\n"
            for src in all_sources:
                answer += f"- **{src.title}** ({src.type})\n  {src.content[:150]}\n\n"
        else:
            answer = f"抱歉，未能找到与「{question}」相关的信息，请尝试换个关键词搜索。"

    # --- 5. Confidence ---
    has_db = len(db_results) > 0
    has_web = len(web_results) > 0
    if has_db and has_web:
        confidence = 0.9
    elif has_db:
        confidence = 0.7
    elif has_web:
        confidence = 0.6
    else:
        confidence = 0.3

    return AgentResponse(
        answer=answer,
        sources=all_sources,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# AI 管家统一入口 — 扫描用户全量数据，产出结构化画像 + 行动清单
# ---------------------------------------------------------------------------

class ScanResponse(BaseModel):
    profile: dict
    plan: list[dict]
    generated_at: str
    llm_enriched: bool
    context: str = ""


@router.post("/scan", response_model=ScanResponse)
async def scan_user_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI 管家「扫描我」：聚合当前用户全量信号，生成专属诊断与行动方案。

    LLM_API_KEY 为空时纯 DB + 启发式合成（见 ai_butler_service.scan_user）。
    """
    result = scan_user(db, user.id)
    return ScanResponse(**result)
