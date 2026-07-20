"""决策日志与回溯服务层 — 记录决策预测，追踪实际结果，校准判断力。

护城河逻辑：纵向数据随时间累积，越用越准；迁移成本极高。
"""
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.destination_decision import DestinationDecision
from app.services.ai_service import AIService
from app.services.ai_orchestrator import AIOrchestrator

SYSTEM_PROMPT = """你是一位决策分析教练。用户在做一个决策时记录了预测和假设，现在填写了实际结果。

请对比"预测 vs 实际"，分析：
1. 哪些假设被验证了？哪些被推翻了？
2. 预测的准确度如何？
3. 从这次决策中学到了什么？
4. 下次类似决策的建议

请用中文回复，200-300 字，语气客观但鼓励。不要使用 markdown 格式。"""


def get_pending_reviews(db: Session, user_id: UUID) -> list[DestinationDecision]:
    """获取待回溯的决策列表（已到回溯日期但未完成回溯）。"""
    today = date.today()
    return (
        db.query(DestinationDecision)
        .filter(
            DestinationDecision.user_id == user_id,
            DestinationDecision.review_completed == False,
            DestinationDecision.review_date.isnot(None),
            DestinationDecision.review_date <= today,
        )
        .order_by(DestinationDecision.review_date.asc())
        .all()
    )


async def complete_review(
    db: Session,
    user_id: UUID,
    decision_id: UUID,
    actual_outcome: str,
    review_notes: str | None,
) -> DestinationDecision:
    """完成决策回溯评估。"""
    decision = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.id == decision_id, DestinationDecision.user_id == user_id)
        .first()
    )
    if not decision:
        raise ValueError("决策不存在或无权访问")

    decision.actual_outcome = actual_outcome
    decision.review_notes = review_notes
    decision.review_completed = True

    # 生成 AI 对比分析
    try:
        context = f"""【决策信息】
- 决策日期: {decision.decision_date}
- 类型: {decision.destination_type.value}
- 置信度: {decision.confidence}/5
- 理由: {decision.reasoning or '未记录'}

【决策时的预测】
{decision.prediction or '未记录'}

【关键假设】
{chr(10).join(f'- {a}' for a in (decision.assumptions or [])) or '未记录'}

【实际结果】
{actual_outcome}

【用户回溯笔记】
{review_notes or '无'}"""

        orchestrator = AIOrchestrator()
        decision.ai_analysis = await orchestrator.chat(system_prompt=SYSTEM_PROMPT, user_prompt=context, timeout=30)
    except Exception:
        # AI 不可用时不阻断回溯流程
        pass

    db.commit()
    db.refresh(decision)
    return decision


def get_reviewed_decisions(db: Session, user_id: UUID) -> list[DestinationDecision]:
    """获取已完成回溯的决策列表（用于查看历史对比）。"""
    return (
        db.query(DestinationDecision)
        .filter(
            DestinationDecision.user_id == user_id,
            DestinationDecision.review_completed == True,
        )
        .order_by(DestinationDecision.review_date.desc())
        .all()
    )
