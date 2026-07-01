# backend/app/services/chat_service.py
"""对话服务层 — Phase 11 AI 职业管家核心。

负责对话/消息 CRUD 与 send_message 全流程：
1. 验证对话所有权
2. 保存用户消息
3. 构建用户上下文（复用 decision_advice_service / growth_insight_service 的 context 模式）
4. 获取对话历史（最近 20 条）
5. Skill 匹配（skill_hint 或自动）
6. 知识库 RAG 检索（top 3）
7. Skill 构建 prompt
8. 调用 AIService.chat()
9. Skill 解析输出
10. CareerPlan 持久化
11. AI 消息持久化（含 skill_used 与 context_snapshot）
"""
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent
from app.models.career_plan import CareerPlan
from app.models.conversation import Conversation, Message
from app.models.destination_decision import DestinationDecision
from app.models.retrospective import Retrospective
from app.models.skill_node import SkillNode
from app.models.user import User
from app.services.ai_service import AIService
from app.services.knowledge_service import search_articles
from app.skills.registry import find_skill, get_skill

# Context 各类数据条数上限
EVENT_LIMIT = 10
SKILL_LIMIT = 50  # all
DECISION_LIMIT = 5
RETRO_LIMIT = 3
HISTORY_LIMIT = 20
KNOWLEDGE_LIMIT = 3


def create_conversation(db: Session, user_id: UUID, title: str = "新对话") -> Conversation:
    """新建对话。"""
    conv = Conversation(user_id=user_id, title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def list_conversations(
    db: Session, user_id: UUID, page: int = 1, page_size: int = 20
) -> tuple[list[Conversation], int]:
    """分页列出对话。"""
    query = db.query(Conversation).filter(Conversation.user_id == user_id)
    total = query.count()
    offset = (page - 1) * page_size
    items = (
        query.order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return items, total


def get_conversation(db: Session, user_id: UUID, conversation_id: UUID) -> Conversation | None:
    """获取对话（验证所有权）。"""
    return (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )


def update_conversation_title(
    db: Session, user_id: UUID, conversation_id: UUID, title: str
) -> Conversation | None:
    """更新对话标题。"""
    conv = get_conversation(db, user_id, conversation_id)
    if not conv:
        return None
    conv.title = title
    db.commit()
    db.refresh(conv)
    return conv


def delete_conversation(db: Session, user_id: UUID, conversation_id: UUID) -> bool:
    """删除对话（级联删除消息由 DB 层或显式处理）。"""
    conv = get_conversation(db, user_id, conversation_id)
    if not conv:
        return False
    # 显式删除关联消息（SQLite 不支持外键级联删除时需手动清理）
    db.query(Message).filter(Message.conversation_id == conversation_id).delete(
        synchronize_session=False
    )
    db.delete(conv)
    db.commit()
    return True


def list_messages(db: Session, conversation_id: UUID) -> list[Message]:
    """获取对话消息（按时间升序）。"""
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )


def build_user_context(db: Session, user_id: UUID) -> str:
    """构建用户上下文字符串。

    复用 decision_advice_service / growth_insight_service 的 context 组装模式，
    查询：CareerEvent(最近10)、SkillNode(全部)、DestinationDecision(最近5)、
    Retrospective(最近3)、最新 GrowthInsight。
    """
    user = db.query(User).filter(User.id == user_id).first()
    lines = ["【用户画像】"]
    if user:
        lines.append(f"- 姓名：{user.name}")
        lines.append(
            f"- 当前阶段：{user.current_stage.value if user.current_stage else '未知'}"
        )
        if user.school:
            lines.append(f"- 学校：{user.school}")
        if user.major:
            lines.append(f"- 专业：{user.major}")
        if user.graduation_year:
            lines.append(f"- 毕业年份：{user.graduation_year}")
    else:
        lines.append("（未找到用户信息）")

    # 职业画像（教育背景 + 目标方向 + 自我评估）
    from app.models.career_profile import CareerProfile
    profile = (
        db.query(CareerProfile)
        .filter(CareerProfile.user_id == user_id)
        .first()
    )
    if profile:
        lines.append("【职业画像】")
        if profile.education_level:
            lines.append(f"- 学历：{profile.education_level}")
        if profile.major:
            lines.append(f"- 专业：{profile.major}")
        if profile.school_name:
            lines.append(f"- 学校：{profile.school_name}")
        if profile.school_tier:
            lines.append(f"- 学校层次：{profile.school_tier}")
        if profile.graduation_year:
            lines.append(f"- 毕业年份：{profile.graduation_year}")
        if profile.target_direction:
            lines.append(f"- 目标方向：{profile.target_direction}")
        if profile.target_industry:
            lines.append(f"- 目标行业：{profile.target_industry}")
        lines.append(
            f"- 自评：技术{profile.technical_skill}/5 沟通{profile.communication_skill}/5 "
            f"领导{profile.leadership_skill}/5 创造{profile.creativity_skill}/5"
        )
        if profile.self_introduction:
            lines.append(f"- 自我介绍：{profile.self_introduction}")

    # 技能树（全部，按 level 降序）
    skills = (
        db.query(SkillNode)
        .filter(SkillNode.user_id == user_id)
        .order_by(SkillNode.level.desc())
        .limit(SKILL_LIMIT)
        .all()
    )
    lines.append("【技能树】")
    if skills:
        for s in skills:
            lines.append(f"- {s.name}(Lv{s.level}) 分类:{s.category}")
    else:
        lines.append("（暂无记录）")

    # 最近 10 条职业事件
    events = (
        db.query(CareerEvent)
        .filter(CareerEvent.user_id == user_id)
        .order_by(CareerEvent.event_date.desc())
        .limit(EVENT_LIMIT)
        .all()
    )
    lines.append("【最近职业事件】")
    if events:
        for ev in events:
            lines.append(f"- {ev.event_date} [{ev.event_type.value}] {ev.title}")
    else:
        lines.append("（暂无记录）")

    # 最近 5 条历史决策
    decisions = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.decision_date.desc())
        .limit(DECISION_LIMIT)
        .all()
    )
    lines.append("【历史决策】")
    if decisions:
        for d in decisions:
            lines.append(
                f"- {d.decision_date} [{d.destination_type.value}] "
                f"状态={d.status.value} 置信度={d.confidence}"
            )
    else:
        lines.append("（暂无记录）")

    # 最近 3 条阶段复盘
    retros = (
        db.query(Retrospective)
        .filter(Retrospective.user_id == user_id)
        .order_by(Retrospective.period_end.desc())
        .limit(RETRO_LIMIT)
        .all()
    )
    lines.append("【阶段复盘】")
    if retros:
        for r in retros:
            lines.append(
                f"- {r.title}({r.period_start}~{r.period_end}) 满意度={r.satisfaction}"
            )
    else:
        lines.append("（暂无记录）")

    # 最新成长洞察（复用 growth_insight_service.get_latest_insight）
    try:
        from app.services.growth_insight_service import get_latest_insight

        insight = get_latest_insight(db, user_id)
        lines.append("【最新成长洞察】")
        if insight:
            lines.append(f"- 成长得分：{insight.get('growth_score', '未知')}")
            lines.append(f"- 趋势：{insight.get('trend', '未知')}")
            summary = insight.get("summary", "")
            if summary:
                lines.append(f"- 摘要：{summary}")
        else:
            lines.append("（暂无记录）")
    except Exception:
        # 成长洞察查询失败不应阻断对话流程
        pass

    return "\n".join(lines) + "\n"


def send_message(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
    content: str,
    skill_hint: str | None = None,
) -> dict:
    """发送消息并获取 AI 回复。

    流程见模块 docstring。Raises AIServiceNotConfigured if LLM_API_KEY empty.

    Returns:
        {content, skill_used, career_plan}
    """
    # 1. 验证对话所有权
    conv = get_conversation(db, user_id, conversation_id)
    if not conv:
        raise ValueError("对话不存在或无权访问")

    # 2. 保存用户消息
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=content,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 3. 构建用户上下文
    user_context = build_user_context(db, user_id)

    # 4. 获取对话历史（最近 20 条，含本次用户消息）
    history = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    history.reverse()  # 转为时间升序

    # 5. Skill 匹配
    context = {"conversation": conv, "history": history}
    if skill_hint:
        skill = get_skill(skill_hint)
        if skill is None:
            skill = find_skill(content, context)
    else:
        skill = find_skill(content, context)

    # 6. 知识库 RAG 检索（top 3）
    knowledge_articles = search_articles(db, content, limit=KNOWLEDGE_LIMIT)
    knowledge = [
        {
            "title": a.title,
            "category": a.category,
            "content": a.content,
            "tags": a.tags,
        }
        for a in knowledge_articles
    ]

    # 7. Skill 构建 prompt
    system_prompt = skill.build_system_prompt(user_context, knowledge)
    # 将对话历史拼入用户 prompt
    history_block = ""
    if len(history) > 1:
        h_lines = ["【对话历史】"]
        for h in history[:-1]:  # 排除刚保存的本次消息（已包含在 user_prompt）
            h_lines.append(f"[{h.role}] {h.content}")
        history_block = "\n".join(h_lines) + "\n\n"
    user_prompt = history_block + skill.build_user_prompt(content)

    # 8. 调用 LLM（AIService._check_config 在 key 为空时抛 AIServiceNotConfigured）
    service = AIService()
    raw = service.chat(system_prompt, user_prompt, timeout=30)

    # 9. Skill 解析输出
    parsed = skill.parse_response(raw)
    reply_content = parsed.get("content", raw)
    career_plan_data = parsed.get("career_plan")

    # 10. 如果生成了 CareerPlan，保存到 DB
    saved_plan_id = None
    if career_plan_data:
        plan = CareerPlan(
            user_id=user_id,
            conversation_id=conversation_id,
            goal_text=career_plan_data.get("goal_text", ""),
            current_state=career_plan_data.get("current_state", {}),
            target_state=career_plan_data.get("target_state", {}),
            gaps=career_plan_data.get("gaps", []),
            milestones=career_plan_data.get("milestones", []),
            timeline_months=career_plan_data.get("timeline_months", 6),
            status="draft",
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        saved_plan_id = str(plan.id)

    # 11. 保存 AI 消息（含 skill_used 与 context_snapshot）
    context_snapshot = {
        "knowledge_count": len(knowledge),
        "knowledge_titles": [k["title"] for k in knowledge],
        "has_career_plan": career_plan_data is not None,
    }
    ai_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=reply_content,
        skill_used=skill.code,
        context_snapshot=context_snapshot,
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)

    # 12. 返回结果
    return {
        "content": reply_content,
        "skill_used": skill.code,
        "career_plan": saved_plan_id,
    }
