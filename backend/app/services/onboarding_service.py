"""首次诊断服务 — 用户入门 5 分钟职业诊断。

4 步流程：
1. 基本信息（当前阶段、目标方向、目标行业）
2. 自我评估（技能、优势、劣势）
3. 提交 → AI 生成诊断
4. 返回推荐路径 + 关键洞察

诊断结果作为后续 AI 个性化的初始基线。
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.onboarding import OnboardingStatus, UserOnboarding
from app.services.ai_service import AIService, AIServiceNotConfigured

logger = logging.getLogger(__name__)


DIAGNOSIS_SYSTEM_PROMPT = """你是一位资深职业规划师。基于用户的首次诊断信息，生成个性化诊断 + 推荐路径。

输出严格的 JSON 格式（不要任何解释、不要 markdown 代码块）：
{
  "diagnosis": "200-300 字的诊断文本，指出用户的核心优势、风险点、关键决策点",
  "recommended_path": {
    "short_term": ["1个月内可执行的行动项1", "行动项2"],
    "mid_term": ["3个月内可执行的行动项1", "行动项2"],
    "long_term": ["6-12个月的目标1", "目标2"]
  },
  "key_insights": [
    {"type": "strength", "text": "用户的核心优势"},
    {"type": "risk", "text": "用户的主要风险"},
    {"type": "opportunity", "text": "可抓住的机会"}
  ]
}

诊断应具体、可执行，避免空话套话。"""


def create_onboarding(
    db: Session,
    user_id: UUID,
    current_stage: str,
    target_direction: str,
    target_industry: str | None,
    self_assessment: dict,
) -> UserOnboarding:
    """保存首次诊断答案（状态为 in_progress）。"""
    # 一个用户只能有一个有效 onboarding
    existing = (
        db.query(UserOnboarding)
        .filter(
            UserOnboarding.user_id == user_id,
            UserOnboarding.status != OnboardingStatus.skipped,
        )
        .first()
    )
    if existing:
        # 已有诊断，更新而非新建
        existing.current_stage = current_stage
        existing.target_direction = target_direction
        existing.target_industry = target_industry
        existing.self_assessment = self_assessment
        existing.status = OnboardingStatus.in_progress
        existing.ai_diagnosis = None
        existing.recommended_path = {}
        existing.key_insights = []
        existing.completed_at = None
        db.commit()
        db.refresh(existing)
        return existing

    onboarding = UserOnboarding(
        user_id=user_id,
        current_stage=current_stage,
        target_direction=target_direction,
        target_industry=target_industry,
        self_assessment=self_assessment,
    )
    db.add(onboarding)
    db.commit()
    db.refresh(onboarding)
    return onboarding


async def generate_diagnosis(db: Session, onboarding_id: UUID) -> UserOnboarding:
    """调用 LLM 生成诊断 + 推荐路径。

    失败时 onboarding 状态保持 in_progress，不阻断流程。
    """
    onboarding = (
        db.query(UserOnboarding).filter(UserOnboarding.id == onboarding_id).first()
    )
    if not onboarding:
        raise ValueError("诊断记录不存在")

    # 构建用户输入
    user_input = f"""【当前阶段】{onboarding.current_stage}
【目标方向】{onboarding.target_direction}
【目标行业】{onboarding.target_industry or '未指定'}

【自我评估】
{json.dumps(onboarding.self_assessment, ensure_ascii=False, indent=2)}

请基于以上信息生成诊断 + 推荐路径。"""

    try:
        ai = AIService()
        raw = await ai.chat(
            system_prompt=DIAGNOSIS_SYSTEM_PROMPT,
            user_content=user_input,
            timeout=30,
        )
    except AIServiceNotConfigured:
        logger.warning("LLM 未配置，跳过诊断生成 onboarding_id=%s", onboarding_id)
        # 保存兜底诊断
        onboarding.ai_diagnosis = "AI 服务未配置，请稍后再试或联系管理员。"
        onboarding.recommended_path = {}
        onboarding.key_insights = []
        onboarding.status = OnboardingStatus.completed
        onboarding.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(onboarding)
        return onboarding
    except Exception as e:
        logger.error("LLM 调用失败 onboarding_id=%s: %s", onboarding_id, e)
        raise

    # 解析 JSON
    try:
        result = _parse_diagnosis_result(raw)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("诊断 JSON 解析失败 onboarding_id=%s: %s", onboarding_id, e)
        # 兜底：将原始文本作为诊断
        onboarding.ai_diagnosis = raw[:1000] if raw else "诊断生成失败"
        onboarding.recommended_path = {}
        onboarding.key_insights = []
    else:
        onboarding.ai_diagnosis = result.get("diagnosis", "")
        onboarding.recommended_path = result.get("recommended_path", {})
        onboarding.key_insights = result.get("key_insights", [])

    onboarding.status = OnboardingStatus.completed
    onboarding.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(onboarding)
    return onboarding


def get_onboarding(db: Session, user_id: UUID) -> UserOnboarding | None:
    """查询用户最新的 onboarding 记录。"""
    return (
        db.query(UserOnboarding)
        .filter(UserOnboarding.user_id == user_id)
        .order_by(UserOnboarding.created_at.desc())
        .first()
    )


def is_onboarding_completed(db: Session, user_id: UUID) -> bool:
    """检查用户是否完成 onboarding。"""
    ob = get_onboarding(db, user_id)
    return ob is not None and ob.status == OnboardingStatus.completed


def skip_onboarding(db: Session, user_id: UUID) -> UserOnboarding | None:
    """跳过 onboarding（标记为 skipped）。"""
    ob = get_onboarding(db, user_id)
    if not ob:
        # 创建一个 skipped 记录
        ob = UserOnboarding(
            user_id=user_id,
            current_stage="unknown",
            target_direction="unknown",
            target_industry=None,
            self_assessment={},
            status=OnboardingStatus.skipped,
        )
        db.add(ob)
    else:
        ob.status = OnboardingStatus.skipped
    db.commit()
    db.refresh(ob)
    return ob


def _parse_diagnosis_result(raw: str) -> dict[str, Any]:
    """解析 LLM 返回的诊断 JSON（容错处理）。"""
    raw = raw.strip()
    # 去除可能的 markdown 代码块
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines)
    raw = raw.strip()
    if not raw.startswith("{"):
        idx = raw.find("{")
        if idx >= 0:
            raw = raw[idx:]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    return data
