"""用户长期记忆服务 — AI 个性化护城河。

从对话中自动抽取结构化事实，存储为 UserMemoryFact，
下次 AI 调用时注入 system prompt，实现"AI 记得用户"。

核心流程：
1. extract_memory_facts: 对话结束后调用 LLM 抽取事实
2. get_user_memory: 检索事实（按类型/键过滤）
3. update_memory_feedback: 用户反馈调整置信度
4. mark_used: AI 使用事实时更新 use_count + last_used_at
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user_memory import MemoryFactType, UserMemoryFact
from app.services.ai_service import AIService, AIServiceNotConfigured

logger = logging.getLogger(__name__)


EXTRACT_SYSTEM_PROMPT = """你是一个事实抽取器。从用户与 AI 的对话中，抽取结构化的用户事实。

只抽取明确、可验证的事实，不要推测。每条事实包含：
- fact_type: preference(偏好) / background(背景) / goal(目标) / constraint(约束) / behavior(行为模式) / fact(客观事实)
- fact_key: 事实键（snake_case，如 preferred_industry, gpa, target_school）
- fact_value: 事实值（简洁文本，如 "金融科技", "3.8", "清华大学"）
- confidence: 置信度 0-100（用户明确说出的 90+，AI 推断的 50-70）

返回 JSON 数组，无事实则返回 []。示例：
[
  {"fact_type": "preference", "fact_key": "preferred_industry", "fact_value": "金融科技", "confidence": 95},
  {"fact_type": "background", "fact_key": "gpa", "fact_value": "3.8", "confidence": 90}
]

严格只返回 JSON 数组，不要任何解释。"""


async def extract_memory_facts(
    db: Session,
    user_id: UUID,
    conversation_id: UUID | None,
    messages: list[dict[str, str]],
) -> list[UserMemoryFact]:
    """从对话消息中抽取结构化事实并存储。

    Args:
        messages: 对话消息列表，格式 [{"role": "user"/"assistant", "content": "..."}]

    Returns:
        新创建的 UserMemoryFact 列表
    """
    if not messages:
        return []

    # 过滤空消息
    valid_messages = [m for m in messages if m.get("content")]
    if not valid_messages:
        return []

    # 拼接对话文本
    dialog_text = "\n".join(
        f"{m['role'].upper()}: {m['content'][:500]}"  # 单条消息截断 500 字符
        for m in valid_messages[-20:]  # 最多取最近 20 条
    )

    try:
        ai = AIService()
        raw = await ai.chat(
            system_prompt=EXTRACT_SYSTEM_PROMPT,
            user_content=f"请从以下对话中抽取用户事实：\n\n{dialog_text}",
            timeout=20,
        )
    except AIServiceNotConfigured:
        logger.warning("LLM 未配置，跳过记忆抽取 user_id=%s", user_id)
        return []
    except Exception as e:
        logger.error("LLM 调用失败，跳过记忆抽取 user_id=%s: %s", user_id, e)
        return []

    # 解析 JSON
    try:
        facts_data = _parse_json_array(raw)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("记忆抽取 JSON 解析失败 user_id=%s: %s", user_id, e)
        return []

    if not facts_data:
        return []

    # 存储事实（去重：同 user_id + fact_key 覆盖旧值）
    created: list[UserMemoryFact] = []
    for fact in facts_data[:20]:  # 一次最多抽取 20 条
        fact_type_str = str(fact.get("fact_type", "fact"))
        fact_key = str(fact.get("fact_key", "")).strip()
        fact_value = str(fact.get("fact_value", "")).strip()
        confidence = int(fact.get("confidence", 70))

        if not fact_key or not fact_value:
            continue

        # 枚举值校验
        try:
            fact_type = MemoryFactType(fact_type_str)
        except ValueError:
            fact_type = MemoryFactType.fact

        confidence = max(0, min(100, confidence))

        # 同 key 覆盖（旧事实置为 inactive）
        existing = (
            db.query(UserMemoryFact)
            .filter(
                UserMemoryFact.user_id == user_id,
                UserMemoryFact.fact_key == fact_key,
                UserMemoryFact.is_active.is_(True),
            )
            .first()
        )
        if existing:
            existing.is_active = False

        new_fact = UserMemoryFact(
            user_id=user_id,
            fact_type=fact_type,
            fact_key=fact_key,
            fact_value=fact_value,
            confidence=confidence,
            source="ai_extracted",
            conversation_id=conversation_id,
        )
        db.add(new_fact)
        created.append(new_fact)

    if created:
        db.commit()
        for f in created:
            db.refresh(f)
        logger.info("抽取并存储 %d 条记忆事实 user_id=%s", len(created), user_id)

    return created


def get_user_memory(
    db: Session,
    user_id: UUID,
    fact_type: MemoryFactType | None = None,
    limit: int = 50,
) -> list[UserMemoryFact]:
    """检索用户记忆事实（按 confidence + use_count 排序）。"""
    query = db.query(UserMemoryFact).filter(
        UserMemoryFact.user_id == user_id,
        UserMemoryFact.is_active.is_(True),
    )
    if fact_type is not None:
        query = query.filter(UserMemoryFact.fact_type == fact_type)
    return (
        query.order_by(UserMemoryFact.confidence.desc(), UserMemoryFact.use_count.desc())
        .limit(limit)
        .all()
    )


def update_memory_feedback(
    db: Session,
    user_id: UUID,
    fact_id: UUID,
    feedback: str,
) -> UserMemoryFact | None:
    """用户反馈调整置信度。

    feedback: "positive" / "negative"
    - positive: confidence +10（最高 100），use_feedback=positive
    - negative: confidence -20（最低 0），连续 2 次 negative 则 is_active=False
    """
    fact = (
        db.query(UserMemoryFact)
        .filter(
            UserMemoryFact.id == fact_id,
            UserMemoryFact.user_id == user_id,
        )
        .first()
    )
    if not fact:
        return None

    fact.user_feedback = feedback
    if feedback == "positive":
        fact.confidence = min(100, fact.confidence + 10)
    elif feedback == "negative":
        fact.confidence = max(0, fact.confidence - 20)
        # 连续 2 次 negative 则停用
        # 这里简化处理：confidence 低于 20 时停用
        if fact.confidence < 20:
            fact.is_active = False

    db.commit()
    db.refresh(fact)
    return fact


def mark_used(db: Session, fact_ids: list[UUID]) -> None:
    """AI 使用事实后更新 use_count + last_used_at。"""
    if not fact_ids:
        return
    now = datetime.now(timezone.utc)
    # C3: 原子 UPDATE — 高并发下 N 个 AI 调用同时使用同一事实不会丢失计数
    col = UserMemoryFact.use_count
    db.query(UserMemoryFact).filter(
        UserMemoryFact.id.in_(fact_ids)
    ).update({
        col: col + 1,
        UserMemoryFact.last_used_at: now,
    }, synchronize_session=False)
    db.commit()


def add_user_provided_fact(
    db: Session,
    user_id: UUID,
    fact_type: MemoryFactType,
    fact_key: str,
    fact_value: str,
) -> UserMemoryFact:
    """用户主动告知事实（confidence=100，source=user_provided）。"""
    # 同 key 覆盖
    existing = (
        db.query(UserMemoryFact)
        .filter(
            UserMemoryFact.user_id == user_id,
            UserMemoryFact.fact_key == fact_key,
            UserMemoryFact.is_active.is_(True),
        )
        .first()
    )
    if existing:
        existing.is_active = False

    fact = UserMemoryFact(
        user_id=user_id,
        fact_type=fact_type,
        fact_key=fact_key,
        fact_value=fact_value,
        confidence=100,
        source="user_provided",
    )
    db.add(fact)
    db.commit()
    db.refresh(fact)
    return fact


def delete_memory_fact(db: Session, user_id: UUID, fact_id: UUID) -> bool:
    """删除记忆事实（软删除，is_active=False）。"""
    fact = (
        db.query(UserMemoryFact)
        .filter(
            UserMemoryFact.id == fact_id,
            UserMemoryFact.user_id == user_id,
        )
        .first()
    )
    if not fact:
        return False
    fact.is_active = False
    db.commit()
    return True


def _parse_json_array(raw: str) -> list[dict[str, Any]]:
    """解析 LLM 返回的 JSON 数组（容错处理）。"""
    raw = raw.strip()
    # 去除可能的 markdown 代码块
    if raw.startswith("```"):
        lines = raw.split("\n")
        # 去首尾 ``` 行
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines)
    raw = raw.strip()
    if not raw.startswith("["):
        # 尝试找到第一个 [
        idx = raw.find("[")
        if idx >= 0:
            raw = raw[idx:]
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Expected JSON array")
    return [d for d in data if isinstance(d, dict)]
