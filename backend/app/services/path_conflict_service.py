"""路径冲突调解服务层 — 检测冲突 + 生成选项 + 保存选择 + 生成行动计划。

当用户的测评结果(如 Holland RIASEC 推荐技术岗)与用户当前现状(如已在准备考公)冲突时，
不是强制推荐，而是提供 3 条路径让用户自主选择：
1. 坚持现状 — 继续当前路径，系统提供适配建议
2. 转向推荐 — 转向测评推荐方向，系统提供转型路径
3. 折中方案 — 双轨并行，主路径保持，副路径发展

LLM 调用可选：未配置 LLM_API_KEY 时使用模板生成选项与计划。
"""
import json
import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.assessment import Assessment
from app.models.destination_decision import DestinationDecision, DestinationType
from app.models.path_conflict import PathConflictResolution

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 路径映射 — 把测评推荐方向 / 去向决策类型映射到统一的「职业赛道」
# ----------------------------------------------------------------------
_TRACK_TECHNICAL = "technical"  # 技术/就业赛道
_TRACK_PUBLIC = "public_service"  # 考公赛道
_TRACK_ACADEMIC = "academic"  # 考研/读博赛道
_TRACK_BUSINESS = "business"  # 创业/商业赛道
_TRACK_CREATIVE = "creative"  # 创意赛道
_TRACK_UNKNOWN = "unknown"

# 测评推荐方向关键词 → 赛道
_DIRECTION_KEYWORDS = {
    _TRACK_TECHNICAL: ["开发", "工程师", "技术", "程序员", "数据", "算法", "前端", "后端", "AI", "测试", "运维"],
    _TRACK_PUBLIC: ["公务员", "考公", "事业单位", "体制内", "选调"],
    _TRACK_ACADEMIC: ["研究", "考研", "读博", "科研", "学术", "博士", "硕士"],
    _TRACK_BUSINESS: ["创业", "商业", "产品", "运营", "市场", "销售", "管理"],
    _TRACK_CREATIVE: ["设计", "创意", "艺术", "内容", "媒体", "写作"],
}

# 去向决策类型 → 赛道
_DESTINATION_TRACK = {
    DestinationType.employment: _TRACK_TECHNICAL,
    DestinationType.abroad: _TRACK_TECHNICAL,
    DestinationType.startup: _TRACK_BUSINESS,
    DestinationType.civil_service: _TRACK_PUBLIC,
    DestinationType.postgrad: _TRACK_ACADEMIC,
    DestinationType.phd: _TRACK_ACADEMIC,
    DestinationType.gap_year: _TRACK_UNKNOWN,
}

# 赛道中文名
_TRACK_LABEL = {
    _TRACK_TECHNICAL: "就业/技术",
    _TRACK_PUBLIC: "考公/体制内",
    _TRACK_ACADEMIC: "考研/深造",
    _TRACK_BUSINESS: "创业/商业",
    _TRACK_CREATIVE: "创意/内容",
    _TRACK_UNKNOWN: "未定向",
}


def _map_direction_to_track(directions: list[str]) -> str:
    """把测评推荐方向列表映射到主赛道。"""
    if not directions:
        return _TRACK_UNKNOWN
    scores: dict[str, int] = {}
    for d in directions:
        for track, keywords in _DIRECTION_KEYWORDS.items():
            if any(kw in d for kw in keywords):
                scores[track] = scores.get(track, 0) + 1
                break
    if not scores:
        return _TRACK_UNKNOWN
    return max(scores.items(), key=lambda x: x[1])[0]


def _get_latest_assessment(db: Session, user_id) -> Assessment | None:
    """获取用户最近一次测评记录。"""
    return (
        db.query(Assessment)
        .filter(Assessment.user_id == user_id)
        .order_by(Assessment.created_at.desc())
        .first()
    )


def _get_latest_decision(db: Session, user_id) -> DestinationDecision | None:
    """获取用户最近一次去向决策（视为用户当前现状）。"""
    return (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.created_at.desc())
        .first()
    )


# ----------------------------------------------------------------------
# detect_conflict: 检测用户的测评结果与现状是否冲突
# ----------------------------------------------------------------------
def detect_conflict(db: Session, user_id) -> dict[str, Any]:
    """检测用户的测评结果与当前现状是否冲突。

    Returns:
        {
            "has_conflict": bool,
            "conflict_type": str,
            "assessment_summary": dict,
            "current_situation": dict,
            "message": str,
        }
    """
    assessment = _get_latest_assessment(db, user_id)
    decision = _get_latest_decision(db, user_id)

    # 兜底：无测评数据
    if assessment is None:
        return {
            "has_conflict": False,
            "conflict_type": "no_assessment",
            "assessment_summary": {},
            "current_situation": _serialize_decision(decision) if decision else {},
            "message": "暂无测评数据，请先完成职业测评后再进行冲突检测。",
        }

    # 兜底：无去向决策
    if decision is None:
        return {
            "has_conflict": False,
            "conflict_type": "no_decision",
            "assessment_summary": _serialize_assessment(assessment),
            "current_situation": {},
            "message": "暂无去向决策记录，无法检测冲突。",
        }

    assessment_summary = _serialize_assessment(assessment)
    situation = _serialize_decision(decision)

    # 计算赛道
    assessment_track = _map_direction_to_track(assessment.recommended_directions or [])
    decision_track = _DESTINATION_TRACK.get(
        decision.destination_type, _TRACK_UNKNOWN
    )

    # 同赛道或任一为未知 → 不冲突
    if assessment_track == _TRACK_UNKNOWN or decision_track == _TRACK_UNKNOWN:
        return {
            "has_conflict": False,
            "conflict_type": "no_conflict",
            "assessment_summary": assessment_summary,
            "current_situation": situation,
            "message": "当前测评推荐与现状无明显冲突。",
        }

    if assessment_track == decision_track:
        return {
            "has_conflict": False,
            "conflict_type": "no_conflict",
            "assessment_summary": assessment_summary,
            "current_situation": situation,
            "message": "测评推荐方向与当前现状一致，无需调解。",
        }

    # 冲突
    return {
        "has_conflict": True,
        "conflict_type": "assessment_vs_current",
        "assessment_summary": assessment_summary,
        "current_situation": situation,
        "assessment_track": assessment_track,
        "decision_track": decision_track,
        "message": (
            f"测评推荐方向（{_TRACK_LABEL.get(assessment_track, assessment_track)}）"
            f"与当前现状（{_TRACK_LABEL.get(decision_track, decision_track)}）存在冲突。"
        ),
    }


# ----------------------------------------------------------------------
# generate_options: 生成 3 条路径选项（LLM 可选，模板兜底）
# ----------------------------------------------------------------------
def generate_options(assessment_summary: dict, situation: dict) -> list[dict]:
    """根据测评摘要与现状摘要生成 3 条路径选项。

    优先尝试 LLM 生成，未配置 LLM_API_KEY 或调用失败时回退到模板。
    """
    if settings.LLM_API_KEY:
        try:
            import asyncio
            options = asyncio.run(_generate_options_via_llm(assessment_summary, situation))
            if options and len(options) == 3:
                return options
        except Exception as e:
            logger.warning("LLM 生成冲突选项失败，回退到模板: %s", e)

    return _generate_options_template(assessment_summary, situation)


def _generate_options_template(assessment_summary: dict, situation: dict) -> list[dict]:
    """模板生成 3 条路径选项（不依赖 LLM）。"""
    directions = assessment_summary.get("directions") or []
    direction_text = "、".join(directions[:3]) if directions else "测评推荐方向"
    assessment_code = assessment_summary.get("result_code", "")
    assessment_type = assessment_summary.get("type", "")

    dest_type = situation.get("destination_type_label") or situation.get("destination_type") or "当前路径"
    dest_status = situation.get("status_label") or situation.get("status") or "进行中"

    return [
        {
            "id": 0,
            "title": "坚持现状",
            "description": (
                f"继续{dest_type}方向（当前状态：{dest_status}），系统将提供适配建议，"
                f"帮助你利用测评优势（{direction_text}）服务于当前路径。"
            ),
            "pros": [
                "保持已有投入与节奏，避免沉没成本损失",
                "心理压力较小，路径确定性高",
                f"可将测评能力（{assessment_code}）转化为当前路径的差异化优势",
            ],
            "cons": [
                f"可能与测评兴趣（{direction_text}）不完全匹配，长期动力不足",
                "若当前路径失败，转型成本随时间增加",
                "需要主动寻找测评能力在当前路径的应用场景",
            ],
            "estimated_timeline": "维持现有计划，6-12 个月评估一次",
            "risk_level": "low",
        },
        {
            "id": 1,
            "title": "转向推荐",
            "description": (
                f"转向测评推荐方向（{direction_text}），系统提供完整转型路径，"
                f"包括技能储备、项目积累与求职/深造策略。"
            ),
            "pros": [
                f"与个人兴趣/能力（{assessment_code}）高度匹配，长期发展潜力大",
                "学习动力强，更容易在领域内取得突破",
                "测评推荐方向通常对应更强的职业满意度",
            ],
            "cons": [
                "前期转型成本高，已有投入可能浪费",
                "需要重新积累领域知识与项目经验",
                "短期可能面临收入/地位下降",
            ],
            "estimated_timeline": "3-6 个月技能储备，6-12 个月项目积累，12-18 个月完成转型",
            "risk_level": "high",
        },
        {
            "id": 2,
            "title": "折中方案",
            "description": (
                f"双轨并行：主路径保持{dest_type}，副路径发展{direction_text}，"
                f"用业余时间验证兴趣与能力，保留未来转向的期权。"
            ),
            "pros": [
                "保留现状的稳定性，同时探索测评推荐方向",
                "渐进式验证，降低决策不确定性",
                "为未来转向预留期权，可逆性强",
            ],
            "cons": [
                "精力分散，两条路径可能都做不好",
                "时间压力大，需要强时间管理能力",
                "短期内看不到明显产出，需要耐心",
            ],
            "estimated_timeline": "3 个月试水，6 个月小成，12 个月决定是否全职转向",
            "risk_level": "medium",
        },
    ]


async def _generate_options_via_llm(assessment_summary: dict, situation: dict) -> list[dict]:
    """用 LLM 生成更个性化的 3 条路径选项。"""
    from app.services.ai_orchestrator import AIOrchestrator

    system_prompt = """你是一位职业规划调解师。用户的测评结果与当前现状存在冲突，请生成 3 条路径选项让用户自主选择：

1. 坚持现状 — 继续当前路径
2. 转向推荐 — 转向测评推荐方向
3. 折中方案 — 双轨并行

严格输出 JSON 数组（不要 markdown，不要解释），每条选项结构如下：
[
  {
    "id": 0,
    "title": "坚持现状",
    "description": "...",
    "pros": ["...", "..."],
    "cons": ["...", "..."],
    "estimated_timeline": "...",
    "risk_level": "low|medium|high"
  },
  ...
]
不要输出 JSON 以外的任何内容。"""

    user_prompt = (
        f"测评摘要：{json.dumps(assessment_summary, ensure_ascii=False)}\n"
        f"现状摘要：{json.dumps(situation, ensure_ascii=False)}"
    )

    orchestrator = AIOrchestrator()
    raw = await orchestrator.chat(system_prompt=system_prompt, user_prompt=user_prompt, timeout=30)

    # 解析 JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return []
        data = json.loads(match.group(0))

    # 校验结构
    if not isinstance(data, list) or len(data) != 3:
        return []
    normalized = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            return []
        normalized.append({
            "id": i,
            "title": str(item.get("title", ["坚持现状", "转向推荐", "折中方案"][i])),
            "description": str(item.get("description", "")),
            "pros": [str(p) for p in item.get("pros", []) if p],
            "cons": [str(c) for c in item.get("cons", []) if c],
            "estimated_timeline": str(item.get("estimated_timeline", "")),
            "risk_level": str(item.get("risk_level", "medium")) if item.get("risk_level") in ("low", "medium", "high") else "medium",
        })
    return normalized


# ----------------------------------------------------------------------
# save_resolution: 保存用户选择
# ----------------------------------------------------------------------
def save_resolution(
    db: Session,
    user_id,
    conflict_data: dict,
    options: list[dict],
    selected_option: int,
    reasoning: str,
) -> PathConflictResolution:
    """保存用户的冲突调解选择，并立即生成行动计划。"""
    resolution = PathConflictResolution(
        user_id=user_id,
        conflict_type=conflict_data.get("conflict_type", "assessment_vs_current"),
        assessment_summary=conflict_data.get("assessment_summary", {}),
        current_situation=conflict_data.get("current_situation", {}),
        options=options,
        selected_option=selected_option,
        reasoning=reasoning or "",
        action_plan={},  # 先占位，下一步生成
    )
    db.add(resolution)
    db.commit()
    db.refresh(resolution)

    # 立即生成行动计划并更新
    action_plan = generate_action_plan(resolution)
    resolution.action_plan = action_plan
    db.commit()
    db.refresh(resolution)
    return resolution


# ----------------------------------------------------------------------
# generate_action_plan: 根据用户选择生成行动计划
# ----------------------------------------------------------------------
def generate_action_plan(resolution: PathConflictResolution) -> dict:
    """根据用户选择生成对应的行动计划。

    LLM 可选：未配置 LLM_API_KEY 时使用模板生成。
    """
    selected = resolution.selected_option
    if selected is None:
        return {}

    options = resolution.options or []
    selected_option = next((o for o in options if o.get("id") == selected), None)
    option_title = selected_option.get("title", "") if selected_option else ""

    assessment = resolution.assessment_summary or {}
    situation = resolution.current_situation or {}
    directions = assessment.get("directions") or []
    direction_text = "、".join(directions[:3]) if directions else "测评推荐方向"
    dest_type = situation.get("destination_type_label") or situation.get("destination_type") or "当前路径"

    if settings.LLM_API_KEY:
        try:
            import asyncio
            plan = asyncio.run(_generate_action_plan_via_llm(resolution, option_title))
            if plan and plan.get("summary"):
                return plan
        except Exception as e:
            logger.warning("LLM 生成行动计划失败，回退到模板: %s", e)

    return _generate_action_plan_template(selected, option_title, direction_text, dest_type)


def _generate_action_plan_template(
    selected: int, option_title: str, direction_text: str, dest_type: str
) -> dict:
    """模板生成行动计划。"""
    if selected == 0:
        # 坚持现状
        return {
            "summary": f"继续{dest_type}路径，将测评能力转化为差异化优势",
            "milestones": [
                {"phase": "第 1-2 周", "goal": f"梳理{dest_type}所需能力清单，找出与测评能力（{direction_text}）的交叉点"},
                {"phase": "第 1 个月", "goal": "制定能力迁移计划，将测评强项应用到当前路径"},
                {"phase": "第 3 个月", "goal": "在当前路径中找一个能体现测评优势的具体项目/任务"},
                {"phase": "第 6 个月", "goal": "评估当前路径进展，决定是否继续或调整"},
            ],
            "resources": [
                "寻找当前领域的导师或前辈，咨询能力迁移经验",
                "加入相关社群，了解测评能力在当前领域的应用案例",
                "定期复盘，记录能力迁移的进展与挑战",
            ],
            "risks": [
                "若长期无法在当前路径中发挥测评优势，可能产生倦怠",
                "需要主动创造机会，而非被动等待",
            ],
        }
    if selected == 1:
        # 转向推荐
        return {
            "summary": f"转向{direction_text}方向，分阶段完成转型",
            "milestones": [
                {"phase": "第 1 个月", "goal": f"深入了解{direction_text}方向的职业路径、核心能力要求与市场现状"},
                {"phase": "第 2-3 个月", "goal": "技能储备：完成 1-2 门核心课程或认证，建立知识体系"},
                {"phase": "第 4-6 个月", "goal": "项目积累：完成 2-3 个可展示的项目，构建作品集"},
                {"phase": "第 7-12 个月", "goal": "求职/申请：投递目标岗位或院校，完成转型"},
            ],
            "resources": [
                f"关注{direction_text}方向的招聘要求与岗位画像",
                "寻找转型成功的案例，学习其路径与方法",
                "加入领域社群，建立人脉与信息源",
                "考虑找一位转型导师，少走弯路",
            ],
            "risks": [
                "前期收入/地位可能下降，需要财务缓冲",
                "已有投入的沉没成本需要心理调适",
                "转型周期可能比预期更长，需要耐心",
            ],
        }
    if selected == 2:
        # 折中方案
        return {
            "summary": f"双轨并行：主路径{dest_type}+ 副路径{direction_text}",
            "milestones": [
                {"phase": "第 1 个月", "goal": f"制定双轨时间表：主路径投入 70%，副路径（{direction_text}）投入 30%"},
                {"phase": "第 2-3 个月", "goal": f"副路径试水：完成{direction_text}方向的入门项目或课程"},
                {"phase": "第 4-6 个月", "goal": "副路径小成：产出可展示的作品或获得副业收入"},
                {"phase": "第 6-12 个月", "goal": "评估双轨进展，决定是否全职转向副路径"},
            ],
            "resources": [
                "时间管理工具（如番茄钟、OKR）确保双轨推进",
                "寻找双轨并行的成功案例，学习其平衡方法",
                "定期与导师/朋友复盘，避免主路径被副路径拖累",
            ],
            "risks": [
                "精力分散可能导致两条路径都进展缓慢",
                "需要强自律，否则容易放弃副路径",
                "若主路径压力大，副路径容易被牺牲",
            ],
        }
    return {}


async def _generate_action_plan_via_llm(
    resolution: PathConflictResolution, option_title: str
) -> dict:
    """用 LLM 生成个性化行动计划。"""
    from app.services.ai_orchestrator import AIOrchestrator

    system_prompt = """你是一位职业规划执行教练。用户在测评与现状冲突后选择了「""" + option_title + """」路径，请生成详细的行动计划。

严格输出 JSON（不要 markdown，不要解释），结构如下：
{
  "summary": "计划摘要（1-2 句话）",
  "milestones": [
    {"phase": "第 1 个月", "goal": "具体目标"}
  ],
  "resources": ["资源1", "资源2"],
  "risks": ["风险1", "风险2"]
}
不要输出 JSON 以外的任何内容。"""

    user_prompt = (
        f"用户选择的路径：{option_title}\n"
        f"测评摘要：{json.dumps(resolution.assessment_summary, ensure_ascii=False)}\n"
        f"现状摘要：{json.dumps(resolution.current_situation, ensure_ascii=False)}\n"
        f"用户理由：{resolution.reasoning or '未提供'}"
    )

    orchestrator = AIOrchestrator()
    raw = await orchestrator.chat(system_prompt=system_prompt, user_prompt=user_prompt, timeout=30)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
        return {}


# ----------------------------------------------------------------------
# 查询辅助
# ----------------------------------------------------------------------
def list_resolutions(db: Session, user_id) -> list[PathConflictResolution]:
    """获取用户的历史调解记录（按时间倒序）。"""
    return (
        db.query(PathConflictResolution)
        .filter(PathConflictResolution.user_id == user_id)
        .order_by(PathConflictResolution.created_at.desc())
        .all()
    )


def get_resolution(db: Session, user_id, resolution_id) -> PathConflictResolution | None:
    """获取单条调解记录。"""
    return (
        db.query(PathConflictResolution)
        .filter(
            PathConflictResolution.id == resolution_id,
            PathConflictResolution.user_id == user_id,
        )
        .first()
    )


# ----------------------------------------------------------------------
# 序列化辅助
# ----------------------------------------------------------------------
def _serialize_assessment(a: Assessment) -> dict:
    return {
        "type": a.assessment_type,
        "result_code": a.result_code,
        "result_summary": a.result_summary,
        "directions": a.recommended_directions or [],
    }


def _serialize_decision(d: DestinationDecision) -> dict:
    dest_type = d.destination_type.value if hasattr(d.destination_type, "value") else str(d.destination_type)
    status = d.status.value if hasattr(d.status, "value") else str(d.status)
    return {
        "id": str(d.id),
        "destination_type": dest_type,
        "destination_type_label": _DESTINATION_LABEL.get(dest_type, dest_type),
        "status": status,
        "status_label": _STATUS_LABEL.get(status, status),
        "decision_date": d.decision_date.isoformat() if d.decision_date else None,
        "confidence": d.confidence,
        "reasoning": d.reasoning,
    }


_DESTINATION_LABEL = {
    "employment": "就业",
    "postgrad": "考研",
    "civil_service": "考公",
    "abroad": "出国",
    "phd": "读博",
    "startup": "创业",
    "gap_year": "间隔年",
}

_STATUS_LABEL = {
    "planned": "已规划",
    "confirmed": "已确认",
    "executed": "已执行",
    "changed": "已变更",
}


def make_conflict_id() -> str:
    """生成临时冲突 ID（用于 detect → resolve 流程中关联）。"""
    return uuid.uuid4().hex
