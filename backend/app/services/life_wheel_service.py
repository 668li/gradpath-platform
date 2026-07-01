"""人生平衡轮服务层 — 8 维度生活满意度评估与 AI 分析。"""
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.life_wheel import LifeWheelSnapshot
from app.services.ai_service import AIService

# 8 个生活维度定义
LIFE_DIMENSIONS = [
    {"key": "career", "name": "职业发展", "desc": "工作满意度、职业进展、工作生活平衡"},
    {"key": "finance", "name": "财务状况", "desc": "财务安全、预算管理、未来财务目标"},
    {"key": "health", "name": "身心健康", "desc": "身体心理健康、睡眠、运动、能量水平"},
    {"key": "relationships", "name": "人际关系", "desc": "家庭、朋友、恋爱关系、沟通质量"},
    {"key": "growth", "name": "个人成长", "desc": "技能发展、自我提升、走出舒适区"},
    {"key": "fun", "name": "乐趣休闲", "desc": "爱好、休闲活动、工作与娱乐平衡"},
    {"key": "environment", "name": "生活环境", "desc": "居住和工作空间对幸福感的影响"},
    {"key": "spirituality", "name": "意义灵性", "desc": "目标感、灵性实践、社区参与"},
]

SYSTEM_PROMPT = """你是一位专业的人生教练，擅长基于人生平衡轮评估给出个性化建议。

用户刚完成了 8 个生活维度的自评（1-10 分）。请基于评分结果给出分析：

1. 指出最需要关注的低分维度（3 分以下）
2. 肯定高分维度的优势
3. 针对最低分维度给出 2-3 条具体可执行的建议
4. 鼓励用户关注维度间的平衡

请用中文回复，200-300 字，语气温暖但有建设性。不要使用 markdown 格式。"""


def submit_scores(db: Session, user_id: UUID, scores: dict, notes: str | None) -> LifeWheelSnapshot:
    """提交一次人生平衡轮评估。"""
    # 计算总分（8 维度平均，四舍五入）
    values = [v for v in scores.values() if isinstance(v, (int, float)) and 1 <= v <= 10]
    overall = round(sum(values) / len(values)) if values else 0

    snapshot = LifeWheelSnapshot(
        user_id=user_id,
        snapshot_date=date.today(),
        scores=scores,
        overall_score=overall,
        notes=notes,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_latest(db: Session, user_id: UUID) -> LifeWheelSnapshot | None:
    return (
        db.query(LifeWheelSnapshot)
        .filter(LifeWheelSnapshot.user_id == user_id)
        .order_by(LifeWheelSnapshot.snapshot_date.desc())
        .first()
    )


def get_history(db: Session, user_id: UUID, limit: int = 12) -> list[LifeWheelSnapshot]:
    return (
        db.query(LifeWheelSnapshot)
        .filter(LifeWheelSnapshot.user_id == user_id)
        .order_by(LifeWheelSnapshot.snapshot_date.desc())
        .limit(limit)
        .all()
    )


def generate_ai_analysis(db: Session, snapshot_id: UUID) -> str:
    """为指定快照生成 AI 分析建议。"""
    snapshot = db.query(LifeWheelSnapshot).filter(LifeWheelSnapshot.id == snapshot_id).first()
    if not snapshot:
        raise ValueError("快照不存在")

    # 组装维度评分文本
    lines = ["【人生平衡轮评分】"]
    for dim in LIFE_DIMENSIONS:
        score = snapshot.scores.get(dim["key"], "未评")
        lines.append(f"- {dim['name']}({dim['key']}): {score}/10 — {dim['desc']}")
    if snapshot.notes:
        lines.append(f"\n用户笔记: {snapshot.notes}")

    service = AIService()
    raw = service.chat(SYSTEM_PROMPT, "\n".join(lines), timeout=30)

    snapshot.ai_analysis = raw
    db.commit()
    return raw
