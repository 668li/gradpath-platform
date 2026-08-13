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
from app.services.ai_orchestrator import AIOrchestrator
from app.services.ai_service import AIServiceNotConfigured

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


# ===== 规则化兜底诊断（LLM 未配置时使用） =====

_DIRECTION_LABELS = {
    "postgrad": "考研",
    "civil_service": "考公",
    "employment": "就业",
    "abroad": "出国",
    "phd": "读博",
    "startup": "创业",
    "gap_year": "间隔年",
}

_STAGE_LABELS = {
    "freshman": "大一",
    "sophomore": "大二",
    "junior": "大三",
    "senior": "大四",
    "graduated": "已毕业",
}

_DIRECTION_ACTIONS: dict[str, dict[str, list[str]]] = {
    "postgrad": {
        "short_term": ["确定目标院校和专业方向", "收集目标院校历年分数线和报录比", "制定每日复习计划（数学/英语/专业课）"],
        "mid_term": ["完成第一轮基础复习", "做 2-3 套真题摸底", "联系目标院校学长学姐获取一手信息"],
        "long_term": ["冲刺阶段模拟考试", "准备复试材料（简历/科研经历/英语口语）", "关注调剂信息作为保底"],
    },
    "civil_service": {
        "short_term": ["了解国考/省考时间线和报名条件", "确定目标岗位类型（中央/省级/市级）", "开始行测数量关系和言语理解专项训练"],
        "mid_term": ["系统学习行测五大模块", "每周完成 2 套申论真题", "关注目标岗位报录比和分数线"],
        "long_term": ["全真模拟考试训练", "申论热点素材积累", "面试结构化答题训练"],
    },
    "employment": {
        "short_term": ["明确目标行业和岗位方向", "优化简历（STAR 法则量化经历）", "在目标公司官网/招聘平台投递实习"],
        "mid_term": ["积累 1-2 段相关实习经历", "建立行业人脉（LinkedIn/校友群）", "准备技术面试或案例分析"],
        "long_term": ["秋招/春招集中投递", "模拟面试训练（行为面+技术面）", "对比 offer 做最终决策"],
    },
    "abroad": {
        "short_term": ["确定目标国家和学校档次", "了解申请时间线和所需材料", "开始语言考试准备（托福/雅思/GRE）"],
        "mid_term": ["完成语言考试达标", "积累科研/实习/志愿者经历", "联系推荐人并准备文书素材"],
        "long_term": ["完成申请文书（PS/CV/RL）", "提交申请并跟踪状态", "准备签证和行前事宜"],
    },
}

_DEFAULT_ACTIONS = {
    "short_term": ["明确你的核心目标和优先级", "收集相关信息，减少信息差", "制定可执行的周计划"],
    "mid_term": ["积累核心经历（实习/科研/项目）", "建立同行交流圈子", "定期复盘调整方向"],
    "long_term": ["形成差异化竞争力", "做出关键决策并全力执行", "建立长期职业发展框架"],
}


def _rule_based_diagnosis(ob: UserOnboarding) -> tuple[str, dict, list[dict]]:
    """基于用户输入生成规则化诊断，无需 LLM。"""
    direction = ob.target_direction or ""
    stage = ob.current_stage or ""
    skills = (ob.self_assessment or {}).get("skills", {})

    dir_label = _DIRECTION_LABELS.get(direction, direction)
    stage_label = _STAGE_LABELS.get(stage, stage)

    # 分析技能分布
    tech = skills.get("technical", 3)
    comm = skills.get("communication", 3)
    lead = skills.get("leadership", 3)
    crea = skills.get("creativity", 3)
    avg = (tech + comm + lead + crea) / 4

    # 找出最强和最弱维度
    dims = [("技术能力", tech), ("沟通能力", comm), ("领导能力", lead), ("创新能力", crea)]
    dims_sorted = sorted(dims, key=lambda x: x[1], reverse=True)
    strongest = dims_sorted[0]
    weakest = dims_sorted[-1]

    # 生成诊断文本
    diagnosis = (
        f"你目前处于{stage_label}阶段，目标方向是{dir_label}。"
        f"从自我评估来看，你的{strongest[0]}相对突出（{strongest[1]}/5），"
        f"而{weakest[0]}是当前短板（{weakest[1]}/5）。"
    )

    if avg >= 4:
        diagnosis += "整体能力均衡且偏高，你具备较强的综合竞争力，关键在于选对方向并持续深耕。"
    elif avg >= 3:
        diagnosis += "整体能力处于中等水平，有明确的提升空间。建议聚焦 1-2 个核心维度重点突破，而非平均用力。"
    else:
        diagnosis += "当前各项能力仍有较大成长空间，不必焦虑——制定清晰的提升计划，每天进步一点，半年后会有质的变化。"

    if stage in ("freshman", "sophomore"):
        diagnosis += f"作为{stage_label}学生，你最大的优势是时间充裕。现在最重要的是广泛探索、积累经验，不必过早锁定唯一方向。"
    elif stage == "junior":
        diagnosis += "大三是关键准备期，距离毕业决策还有约一年。现在是集中发力、积累核心经历的最佳窗口。"
    elif stage in ("senior", "graduated"):
        diagnosis += "时间紧迫，建议立即进入执行模式：减少犹豫，用 2 周时间做出决策，然后全力以赴。"

    # 推荐路径
    path = _DIRECTION_ACTIONS.get(direction, _DEFAULT_ACTIONS)

    # 关键洞察
    insights = [
        {"type": "strength", "text": f"{strongest[0]}是你的核心竞争力（{strongest[1]}/5），在{dir_label}中要充分利用这一优势。"},
        {"type": "risk", "text": f"{weakest[0]}（{weakest[1]}/5）可能成为瓶颈，建议每周投入 2-3 小时针对性提升。"},
        {"type": "opportunity", "text": f"选择{dir_label}方向，平台已为你准备了院校情报、暗知识、社区经验等工具，善用它们打破信息差。"},
    ]

    return diagnosis, path, insights


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
        ai = AIOrchestrator()
        raw = await ai.chat(
            system_prompt=DIAGNOSIS_SYSTEM_PROMPT,
            user_prompt=user_input,
            timeout=30,
        )
    except AIServiceNotConfigured:
        logger.warning("LLM 未配置，使用规则化诊断 onboarding_id=%s", onboarding_id)
        # 规则化兜底诊断：基于用户输入生成有意义的指导
        diagnosis, path, insights = _rule_based_diagnosis(onboarding)
        onboarding.ai_diagnosis = diagnosis
        onboarding.recommended_path = path
        onboarding.key_insights = insights
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
    """检查用户是否完成 onboarding（completed 或 skipped 均视为已完成）。"""
    ob = get_onboarding(db, user_id)
    return ob is not None and ob.status in (OnboardingStatus.completed, OnboardingStatus.skipped)


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
