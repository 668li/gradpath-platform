# backend/app/services/gamification_service.py
"""游戏化服务 — XP 计算、等级系统、徽章注册表与懒颁发。"""
import secrets
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent, EventType
from app.models.community_report import CommunityReport
from app.models.destination_decision import DestinationDecision
from app.models.interview_report import InterviewReport
from app.models.retrospective import Retrospective
from app.models.skill_node import SkillNode
from app.models.user_badge import UserBadge
from app.models.user_setting import UserSetting

# ======================================================================
# 等级系统
# ======================================================================

LEVEL_THRESHOLDS = [0, 50, 150, 350, 700, 1200, 2000]
LEVEL_NAMES = ["萌新", "探索者", "前行者", "进阶者", "达人", "专家", "大师"]


def get_level(xp: int) -> tuple[int, str, int, int]:
    """返回 (等级编号1-7, 等级名称, 当前等级下限, 下一等级下限)。"""
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            level = i + 1
        else:
            break
    name = LEVEL_NAMES[level - 1]
    current_min = LEVEL_THRESHOLDS[level - 1]
    next_min = LEVEL_THRESHOLDS[level] if level < len(LEVEL_THRESHOLDS) else LEVEL_THRESHOLDS[-1]
    return level, name, current_min, next_min


# ======================================================================
# XP 计算（实时，不存储）
# ======================================================================

def calculate_xp(db: Session, user_id: UUID) -> int:
    """从现有数据实时计算 XP。

    优化：用聚合查询替代 .all() 加载全量数据，避免 events/skills 表增长后内存膨胀。
    - events: 一次查询同时获取总数和特殊事件数（promotion/certification 各 +10 额外 XP）
    - skills: 用 sum(level) 替代遍历累加
    """
    decisions = (
        db.query(func.count(DestinationDecision.id))
        .filter(DestinationDecision.user_id == user_id)
        .scalar()
        or 0
    )
    # events: 一次查询获取总数 + 特殊事件数（promotion/certification）
    events_stats = (
        db.query(
            func.count(CareerEvent.id),
            func.count(
                case(
                    (
                        CareerEvent.event_type.in_(
                            [EventType.promotion, EventType.certification]
                        ),
                        1,
                    ),
                    else_=None,
                )
            ),
        )
        .filter(CareerEvent.user_id == user_id)
        .one()
    )
    total_events = events_stats[0] or 0
    special_events = events_stats[1] or 0
    # skills: 用 sum(level) 替代加载全量数据遍历
    skills_level_sum = (
        db.query(func.sum(SkillNode.level))
        .filter(SkillNode.user_id == user_id)
        .scalar()
        or 0
    )
    retros = (
        db.query(func.count(Retrospective.id))
        .filter(Retrospective.user_id == user_id)
        .scalar()
        or 0
    )
    community = (
        db.query(func.count(CommunityReport.id))
        .filter(CommunityReport.user_id == user_id)
        .scalar()
        or 0
    )
    interviews = (
        db.query(func.count(InterviewReport.id))
        .filter(InterviewReport.user_id == user_id)
        .scalar()
        or 0
    )

    xp = 0
    xp += decisions * 10
    xp += total_events * 5 + special_events * 10
    xp += int(skills_level_sum) * 5
    xp += retros * 15
    xp += community * 20
    xp += interviews * 20
    return xp


# ======================================================================
# 徽章注册表（代码定义，不存 DB）
# ======================================================================

@dataclass
class GamificationContext:
    decisions_count: int
    events_count: int
    skills_count: int
    retros_count: int
    community_count: int
    interview_count: int
    level: int


BADGE_REGISTRY: list[dict] = [
    {"code": "first_decision", "name": "破冰决策", "description": "创建第一个去向决策", "icon": "compass",
     "check": lambda ctx: ctx.decisions_count >= 1},
    {"code": "first_event", "name": "成长起步", "description": "记录第一个职业事件", "icon": "sparkles",
     "check": lambda ctx: ctx.events_count >= 1},
    {"code": "first_skill", "name": "技能初成", "description": "添加第一个技能节点", "icon": "wrench",
     "check": lambda ctx: ctx.skills_count >= 1},
    {"code": "first_retro", "name": "复盘达人", "description": "完成第一次阶段复盘", "icon": "clipboard",
     "check": lambda ctx: ctx.retros_count >= 1},
    {"code": "first_community", "name": "社区贡献", "description": "提交第一份社区报告", "icon": "users",
     "check": lambda ctx: ctx.community_count >= 1},
    {"code": "first_interview", "name": "经验分享", "description": "提交第一份面试经验", "icon": "briefcase",
     "check": lambda ctx: ctx.interview_count >= 1},
    {"code": "decision_master", "name": "决策大师", "description": "创建 5 个以上去向决策", "icon": "compass",
     "check": lambda ctx: ctx.decisions_count >= 5},
    {"code": "event_master", "name": "事件达人", "description": "记录 10 个以上职业事件", "icon": "sparkles",
     "check": lambda ctx: ctx.events_count >= 10},
    {"code": "skill_master", "name": "技能专家", "description": "拥有 10 个以上技能节点", "icon": "wrench",
     "check": lambda ctx: ctx.skills_count >= 10},
    {"code": "retro_master", "name": "复盘行者", "description": "完成 5 次以上复盘", "icon": "clipboard",
     "check": lambda ctx: ctx.retros_count >= 5},
    {"code": "community_master", "name": "社区先锋", "description": "提交 3 份以上社区报告", "icon": "users",
     "check": lambda ctx: ctx.community_count >= 3},
    {"code": "interview_master", "name": "面经达人", "description": "提交 3 份以上面试经验", "icon": "briefcase",
     "check": lambda ctx: ctx.interview_count >= 3},
    {"code": "level_explorer", "name": "探索者", "description": "达到等级 2", "icon": "star",
     "check": lambda ctx: ctx.level >= 2},
    {"code": "level_expert", "name": "专家", "description": "达到等级 5", "icon": "star",
     "check": lambda ctx: ctx.level >= 5},
    {"code": "level_master", "name": "大师", "description": "达到等级 7", "icon": "crown",
     "check": lambda ctx: ctx.level >= 7},
]


def build_context(db: Session, user_id: UUID) -> GamificationContext:
    """查询各表计数并计算等级。"""
    decisions_count = db.query(DestinationDecision).filter(DestinationDecision.user_id == user_id).count()
    events_count = db.query(CareerEvent).filter(CareerEvent.user_id == user_id).count()
    skills_count = db.query(SkillNode).filter(SkillNode.user_id == user_id).count()
    retros_count = db.query(Retrospective).filter(Retrospective.user_id == user_id).count()
    community_count = db.query(CommunityReport).filter(CommunityReport.user_id == user_id).count()
    interview_count = db.query(InterviewReport).filter(InterviewReport.user_id == user_id).count()

    xp = calculate_xp(db, user_id)
    level, _, _, _ = get_level(xp)

    return GamificationContext(
        decisions_count=decisions_count,
        events_count=events_count,
        skills_count=skills_count,
        retros_count=retros_count,
        community_count=community_count,
        interview_count=interview_count,
        level=level,
    )


def check_and_award_badges(db: Session, user_id: UUID) -> list[dict]:
    """检查所有徽章，将新符合条件的颁发到 DB，返回新颁发的徽章列表。"""
    ctx = build_context(db, user_id)
    existing_codes = {
        ub.badge_code
        for ub in db.query(UserBadge).filter(UserBadge.user_id == user_id).all()
    }
    newly_awarded: list[dict] = []
    for badge in BADGE_REGISTRY:
        if badge["code"] not in existing_codes and badge["check"](ctx):
            ub = UserBadge(user_id=user_id, badge_code=badge["code"])
            db.add(ub)
            newly_awarded.append({
                "code": badge["code"],
                "name": badge["name"],
                "description": badge["description"],
                "icon": badge["icon"],
            })
    if newly_awarded:
        db.commit()
    return newly_awarded


def get_profile(db: Session, user_id: UUID) -> dict:
    """返回完整的游戏化档案。"""
    newly_awarded = check_and_award_badges(db, user_id)
    xp = calculate_xp(db, user_id)
    level, level_name, current_min, next_min = get_level(xp)

    earned_codes = {
        ub.badge_code
        for ub in db.query(UserBadge).filter(UserBadge.user_id == user_id).all()
    }
    earned_badges = [
        {"code": b["code"], "name": b["name"], "description": b["description"], "icon": b["icon"]}
        for b in BADGE_REGISTRY if b["code"] in earned_codes
    ]
    available_badges = [
        {"code": b["code"], "name": b["name"], "description": b["description"], "icon": b["icon"]}
        for b in BADGE_REGISTRY if b["code"] not in earned_codes
    ]

    progress_current = xp - current_min
    progress_needed = next_min - current_min if level < len(LEVEL_THRESHOLDS) else 0
    progress_percent = round(progress_current / progress_needed * 100) if progress_needed > 0 else 100

    return {
        "xp": xp,
        "level": level,
        "level_name": level_name,
        "progress": {
            "current": progress_current,
            "needed": progress_needed,
            "percent": progress_percent,
        },
        "earned_badges": earned_badges,
        "available_badges": available_badges,
        "newly_awarded": newly_awarded,
    }


# ======================================================================
# 用户设置
# ======================================================================

def get_or_create_settings(db: Session, user_id: UUID) -> UserSetting:
    """获取用户设置，不存在则创建默认。"""
    setting = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
    if not setting:
        setting = UserSetting(user_id=user_id, share_skills_enabled=False, share_token=None)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


def update_settings(db: Session, user_id: UUID, share_skills: bool | None) -> UserSetting:
    """更新分享设置。开启分享且无 token 时生成 token；关闭时保留 token。"""
    setting = get_or_create_settings(db, user_id)
    if share_skills is not None:
        setting.share_skills_enabled = share_skills
        if share_skills and not setting.share_token:
            setting.share_token = secrets.token_hex(16)
    db.commit()
    db.refresh(setting)
    return setting
