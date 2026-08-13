"""复盘中心 Service — 复盘 CRUD / AI 分析（AIOrchestrator 透传 + 模板降级）。

对齐系统设计 §3.2.M4 复盘中心契约（方案 C 做实）。

- 创建复盘：X-Idempotency-Key → t_review_record.biz_req_no，命中返回已有；
  action_refs: list 落库转换为 {"action_ids": [...]} dict（JSONB）
- AI 分析：经 AIOrchestrator 调 LLM（未配置/熔断/解析失败一律模板降级），
  结果写回 ai_summary / ai_insights / ai_suggestions / uncertainty_score，
  status → COMPLETED；AIReviewVO.created_at 无模型列 → 映射审计 updated_time
"""
import json
import logging
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.growth_center import GrowthTrajectory
from app.models.review_record import ReviewRecord
from app.schemas.review import AIReviewVO, ReviewCreateRequest
from app.services.ai_orchestrator import AIOrchestrator

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是职业规划平台的复盘分析师。请根据用户的复盘内容输出严格 JSON："
    '{"summary": "…", "insights": [{"insight": "…", "evidence": "…"}], '
    '"suggestions": ["…"], "uncertainty_score": 0.0~1.0}'
)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def get_review(db: Session, user_id: UUID, review_id: int) -> ReviewRecord:
    review = (
        db.query(ReviewRecord)
        .filter(
            ReviewRecord.id == review_id,
            ReviewRecord.user_id == user_id,
            ReviewRecord.deleted.is_(False),
        )
        .first()
    )
    if review is None:
        raise _not_found("复盘记录不存在")
    return review


def create_review(
    db: Session,
    user_id: UUID,
    data: ReviewCreateRequest,
    idempotency_key: str | None = None,
) -> ReviewRecord:
    """创建复盘记录。

    幂等：idempotency_key 命中 t_review_record.biz_req_no 时返回已有记录。
    落库转换：action_refs: list → {"action_ids": [...]} dict。
    联动：写成长轨迹（event_type=review_completed，source_event_id 复用幂等键）。
    """
    if idempotency_key:
        existing = (
            db.query(ReviewRecord)
            .filter(ReviewRecord.biz_req_no == idempotency_key)
            .first()
        )
        if existing:
            return existing

    review = ReviewRecord(
        user_id=user_id,
        review_type=data.review_type,
        period_start=data.period_start,
        period_end=data.period_end,
        content=data.content,
        action_refs={"action_ids": list(data.action_refs)},
        mood_score=data.mood_score,
        status="DRAFT",
        biz_req_no=idempotency_key,
    )
    db.add(review)
    db.flush()
    db.add(
        GrowthTrajectory(
            user_id=user_id,
            event_type="review_completed",
            event_payload={
                "review_id": review.id,
                "review_type": review.review_type,
                "period_start": review.period_start.isoformat(),
                "period_end": review.period_end.isoformat(),
                "mood_score": review.mood_score,
            },
            source_event_id=idempotency_key or uuid.uuid4().hex,
            occurred_at=review.created_time,
        )
    )
    db.commit()
    db.refresh(review)
    return review


def list_reviews(
    db: Session,
    user_id: UUID,
    page: int = 1,
    size: int = 20,
) -> tuple[list[ReviewRecord], int]:
    """分页复盘列表（按周期结束日期倒序）。"""
    query = db.query(ReviewRecord).filter(
        ReviewRecord.user_id == user_id,
        ReviewRecord.deleted.is_(False),
    )
    total = query.count()
    items = (
        query.order_by(ReviewRecord.period_end.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return items, total


def _parse_ai_json(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("LLM 输出不包含 JSON 对象")
    return json.loads(raw[start : end + 1])


def _template_analysis(review: ReviewRecord) -> dict:
    """LLM 不可用时的模板降级分析（确定性输出，便于测试）。"""
    preview = (review.content or "")[:120]
    return {
        "summary": (
            f"模板降级摘要：{review.review_type} 复盘已记录，"
            f"内容概览「{preview}…」。"
        ),
        "insights": [
            {
                "insight": "持续完成复盘本身就是稳定的成长动作",
                "evidence": "复盘内容已成功写入成长档案",
            }
        ],
        "suggestions": ["配置 LLM_API_KEY 后重新触发 AI 分析获取深度洞察"],
        "uncertainty_score": 0.5,
    }


async def ai_analyze_review(
    db: Session,
    user_id: UUID,
    review_id: int,
    focus_areas: list | None = None,
    temperature: float = 0.3,
) -> ReviewRecord:
    """触发 AI 复盘分析并写回结果。

    幂等：已 COMPLETED 且含 ai_summary 时直接返回既有结果（重复触发不重算）。
    LLM 不可用（未配置 / 熔断 / 超时 / 解析失败）→ 模板降级，均落库。
    """
    review = get_review(db, user_id, review_id)
    if review.status == "COMPLETED" and review.ai_summary:
        return review

    focus = focus_areas or ["总结", "行动计划"]
    user_content = (
        f"复盘类型：{review.review_type}（{review.period_start} ~ {review.period_end}）\n"
        f"关注维度：{'、'.join(focus)}\n"
        f"复盘内容：\n{review.content}\n\n"
        "请输出复盘摘要、洞察（含证据）、建议与不确定性评分（严格 JSON）。"
    )

    result: dict
    try:
        orchestrator = AIOrchestrator()
        raw = await orchestrator.chat(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_content,
            timeout=30,
            retry=1,
        )
        parsed = _parse_ai_json(raw)
        result = {
            "summary": str(parsed.get("summary", "")).strip(),
            "insights": parsed.get("insights", []),
            "suggestions": parsed.get("suggestions", []),
            "uncertainty_score": float(
                min(max(float(parsed.get("uncertainty_score", 0.5)), 0.0), 1.0)
            ),
        }
    except Exception as e:  # 未配置 / 熔断 / 超时 / 解析失败 → 模板降级
        logger.warning("AI 复盘分析降级（review_id=%s）: %s", review_id, e)
        result = _template_analysis(review)

    review.ai_summary = result["summary"]
    review.ai_insights = {"items": result["insights"]}
    review.ai_suggestions = {"items": result["suggestions"]}
    review.uncertainty_score = result["uncertainty_score"]
    review.status = "COMPLETED"
    db.commit()
    db.refresh(review)
    return review


def to_ai_vo(review: ReviewRecord) -> AIReviewVO:
    """AI 结果 VO：created_at 无模型列 → 映射审计 updated_time；
    insights/suggestions 从 {"items": [...]} 取出。"""
    return AIReviewVO(
        review_id=review.id,
        summary=review.ai_summary or "",
        insights=(review.ai_insights or {}).get("items", []),
        suggestions=(review.ai_suggestions or {}).get("items", []),
        uncertainty_score=float(review.uncertainty_score or 0.0),
        status=review.status,
        created_at=review.updated_time,
    )
