"""考公作战室服务层 — 岗位情报 + 考公定位 + 考公暗知识。

借鉴 career_intel_service 的三段式结构，覆盖考公全流程的信息差。

历史注记：考公暗知识种子（28 条无溯源经验断言，含编造竞争比/占比统计）
已于 2026-09-06 随假数据管道一并删除（用户拍板"除了A全部删了"：
平台内容必须全部可溯源）。暗知识表保留空表，GET 接口返回空列表；
未来重建设须走"官方来源 + data_source 溯源"管线。
"""

import json
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.civil_service_intel import (
    CivilServiceDarkKnowledge,
    CivilServicePositioning,
    PostIntel,
)
from app.services.ai_orchestrator import AIOrchestrator

# 阶段名称映射
STAGE_NAMES = {
    "early_prep": "大一准备",
    "preparation": "备考选岗",
    "exam": "笔试面试",
    "onboarding": "入职适应",
    "career_dev": "职业发展",
}


# ===== 暗知识服务（只读；种子已删除，禁止再预填充无溯源内容） =====


def get_civil_service_dark_knowledge_by_stage(
    db: Session, stage: str | None = None
) -> list[CivilServiceDarkKnowledge]:
    """按阶段获取暗知识列表。"""
    query = db.query(CivilServiceDarkKnowledge)
    if stage:
        query = query.filter(CivilServiceDarkKnowledge.stage == stage)
    return query.order_by(CivilServiceDarkKnowledge.sort_order).all()


def get_civil_service_dark_knowledge_stages(db: Session) -> list[dict]:
    """获取各阶段的统计信息。"""
    results = []
    for stage_code, stage_name in STAGE_NAMES.items():
        count = (
            db.query(CivilServiceDarkKnowledge)
            .filter(CivilServiceDarkKnowledge.stage == stage_code)
            .count()
        )
        results.append(
            {
                "stage": stage_code,
                "stage_name": stage_name,
                "count": count,
            }
        )
    return results


# ===== 岗位情报服务 =====


async def query_post_intel(region: str, department: str, post_name: str, exam_type: str) -> dict:
    """AI 查询岗位情报。不落库，返回结构化结果供前端预览。"""
    system_prompt = """你是一位资深体制内情报分析师，专门分析中国公务员/事业单位岗位的真实情况和信息差。

用户会提供地区、部门、岗位名称和考试类型，你需要输出结构化的岗位情报。

严格输出以下 JSON 格式（不要输出任何其他内容）：
```json
{
  "region": "地区",
  "department": "部门",
  "post_name": "岗位名称",
  "exam_type": "考试类型",
  "real_competition": "low/medium/high/extreme/unknown",
  "treatment_level": "low/medium/high/top/unknown",
  "promotion_speed": "slow/medium/fast/unknown",
  "workload": "light/moderate/heavy/extreme/unknown",
  "radish_post": "unlikely/possible/likely/unknown",
  "service_period": "yes/no/unknown",
  "admission_ratio": "预估报录比，如 25:1",
  "cutoff_score": 预估进面分数线（整数，如135）,
  "salary_estimate": "年薪估算描述，如 到手12-15万/年",
  "housing_fund": "公积金描述，如 双边2000/月",
  "bonus_info": "年终绩效描述",
  "department_tier": "部门梯队描述，如 第一梯队（两办组纪宣）",
  "work_content": "核心工作内容描述",
  "insider_notes": "内部消息和注意事项，如 加班强度、科室氛围、领导风格等",
  "risk_warnings": ["风险提示列表，每条一句话"],
  "data_sources": ["数据来源说明，如 QZZN论坛、在职人员反馈、公开招录数据等"],
  "tags": ["标签列表，如 国考、税务、热门岗、应届生友好"],
  "ai_summary": "100-200字的综合分析总结"
}
```

枚举值说明：
- real_competition: low=竞争小(20:1以内), medium=中等(20-50:1), high=激烈(50-200:1), extreme=极其激烈(200:1以上)
- treatment_level: low=6-10万/年, medium=10-18万/年, high=18-30万/年, top=30万+/年
- promotion_speed: slow=晋升慢（清水衙门）, medium=中等, fast=晋升快（核心部门）
- workload: light=清闲, moderate=适中, heavy=较忙, extreme=极忙（两办/纪委常加班）
- radish_post: unlikely=不太可能, possible=有可能, likely=很可能是萝卜岗
- service_period: yes=有5年服务期, no=无明确服务期, unknown=不确定

重要：不确定的信息一律标为 unknown 或 null，不要编造。所有判断都要基于公开可查的信息和体制内常识。"""

    user_content = f"地区：{region}\n部门：{department}\n岗位：{post_name}\n考试类型：{exam_type}\n\n请提供这个岗位的真实情报。"

    orchestrator = AIOrchestrator()
    raw = await orchestrator.chat(system_prompt=system_prompt, user_prompt=user_content, timeout=45)

    # 提取 JSON
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            try:
                data = json.loads(match.group(1))
            except (json.JSONDecodeError, TypeError):
                match2 = re.search(r"\{.*\}", raw, re.DOTALL)
                if match2:
                    try:
                        data = json.loads(match2.group(0))
                    except (json.JSONDecodeError, TypeError):
                        data = {}
                else:
                    data = {}
        else:
            data = {}

    # 确保必要字段存在
    data.setdefault("region", region)
    data.setdefault("department", department)
    data.setdefault("post_name", post_name)
    data.setdefault("exam_type", exam_type)
    data.setdefault("real_competition", "unknown")
    data.setdefault("treatment_level", "unknown")
    data.setdefault("promotion_speed", "unknown")
    data.setdefault("workload", "unknown")
    data.setdefault("radish_post", "unknown")
    data.setdefault("service_period", "unknown")
    data.setdefault("admission_ratio", None)
    data.setdefault("cutoff_score", None)
    data.setdefault("salary_estimate", None)
    data.setdefault("housing_fund", None)
    data.setdefault("bonus_info", None)
    data.setdefault("department_tier", None)
    data.setdefault("work_content", None)
    data.setdefault("insider_notes", None)
    data.setdefault("risk_warnings", [])
    data.setdefault("data_sources", [])
    data.setdefault("tags", [])
    data.setdefault("ai_summary", "")

    return data


def save_post_intel(db: Session, user_id: UUID, data: dict) -> PostIntel:
    """保存岗位情报。"""
    intel = PostIntel(user_id=user_id, **data)
    db.add(intel)
    db.commit()
    db.refresh(intel)
    return intel


def get_user_post_intel_list(db: Session, user_id: UUID) -> list[PostIntel]:
    return (
        db.query(PostIntel)
        .filter(PostIntel.user_id == user_id)
        .order_by(PostIntel.created_at.desc())
        .all()
    )


def delete_post_intel(db: Session, user_id: UUID, intel_id: UUID) -> bool:
    intel = (
        db.query(PostIntel).filter(PostIntel.id == intel_id, PostIntel.user_id == user_id).first()
    )
    if not intel:
        return False
    db.delete(intel)
    db.commit()
    return True


# ===== 考公定位服务 =====


async def create_civil_service_positioning(
    db: Session, user_id: UUID, data: dict
) -> CivilServicePositioning:
    """创建考公定位，自动触发 AI 评估。"""
    positioning = CivilServicePositioning(user_id=user_id, **data)
    db.add(positioning)
    db.commit()
    db.refresh(positioning)

    # AI 生成评估
    try:
        ai_result = await _generate_civil_service_assessment(positioning)
        positioning.ai_assessment = ai_result.get("ai_assessment", "")
        positioning.competitiveness_score = ai_result.get("competitiveness_score")
        positioning.eligible_for_xuandiao = ai_result.get("eligible_for_xuandiao", False)
        positioning.reach_posts = ai_result.get("reach_posts", [])
        positioning.target_posts = ai_result.get("target_posts", [])
        positioning.safety_posts = ai_result.get("safety_posts", [])
        positioning.preparation_timeline = ai_result.get("preparation_timeline", "")
        positioning.risk_warnings = ai_result.get("risk_warnings", [])
        db.commit()
        db.refresh(positioning)
    except Exception:
        positioning.ai_assessment = "AI 评估暂时不可用，请稍后重试。"
        db.commit()
        db.refresh(positioning)

    return positioning


async def _generate_civil_service_assessment(positioning: CivilServicePositioning) -> dict:
    """AI 生成考公定位评估。"""
    system_prompt = """你是一位资深考公规划师和体制内过来人，深谙中国公务员考试的信息不对称和选岗策略。

用户会提供个人背景信息，你需要：
1. 评估其考公竞争力（0-100分）
2. 判断是否符合选调生条件
3. 推荐三档目标岗位：冲刺（20-40%概率）、匹配（50-70%概率）、保底（80-95%概率），每档3-5个岗位
4. 制定备考时间线
5. 给出风险提示

严格输出以下 JSON 格式（不要输出任何其他内容）：
```json
{
  "ai_assessment": "300-500字的综合评估，包括竞争力分析、选岗方向建议、核心优势与劣势、赛道选择建议",
  "competitiveness_score": 0到100的整数,
  "eligible_for_xuandiao": true或false,
  "reach_posts": [
    {"region": "地区", "department": "部门", "post": "具体岗位", "reason": "推荐理由", "probability": 30}
  ],
  "target_posts": [
    {"region": "地区", "department": "部门", "post": "具体岗位", "reason": "推荐理由", "probability": 60}
  ],
  "safety_posts": [
    {"region": "地区", "department": "部门", "post": "具体岗位", "reason": "推荐理由", "probability": 90}
  ],
  "preparation_timeline": "备考时间线安排建议，分阶段描述",
  "risk_warnings": ["风险提示列表，每条一句话"]
}
```

每档推荐3-5个岗位。岗位要具体到部门和岗位类型（如 国家税务总局XX市税务局-一级行政执法员）。
选岗建议需考虑：专业匹配度、应届生身份、政治面貌、学历层次、目标地区待遇水平、竞争激烈程度。
不确定的评分给中间值，不要给极端值。"""

    party_status = "是" if positioning.is_party_member else "否"
    leader_status = "是" if positioning.student_leader else "否"
    honors_status = "是" if positioning.has_honors else "否"
    fresh_status = "是" if positioning.is_fresh_graduate else "否"

    user_content = f"""个人背景：
学历层次：{positioning.education_level}
学校层次：{positioning.school_tier or '未提供'}
专业：{positioning.major or '未提供'}
是否党员：{party_status}
是否学生干部：{leader_status}
是否有校级以上荣誉：{honors_status}
是否应届生：{fresh_status}
目标地区：{positioning.target_region or '未提供'}
目标考试类型：{positioning.target_type or '未提供'}
家庭背景：{positioning.family_background or '未提供'}
其他信息：{positioning.other_info or '无'}
"""

    orchestrator = AIOrchestrator()
    raw = await orchestrator.chat(system_prompt=system_prompt, user_prompt=user_content, timeout=45)

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            try:
                data = json.loads(match.group(1))
            except (json.JSONDecodeError, TypeError):
                match2 = re.search(r"\{.*\}", raw, re.DOTALL)
                if match2:
                    try:
                        data = json.loads(match2.group(0))
                    except (json.JSONDecodeError, TypeError):
                        data = {}
                else:
                    data = {}
        else:
            data = {}

    data.setdefault("ai_assessment", "")
    data.setdefault("competitiveness_score", 50)
    data.setdefault("eligible_for_xuandiao", False)
    data.setdefault("reach_posts", [])
    data.setdefault("target_posts", [])
    data.setdefault("safety_posts", [])
    data.setdefault("preparation_timeline", "")
    data.setdefault("risk_warnings", [])

    return data


def get_latest_civil_service_positioning(
    db: Session, user_id: UUID
) -> CivilServicePositioning | None:
    return (
        db.query(CivilServicePositioning)
        .filter(CivilServicePositioning.user_id == user_id)
        .order_by(CivilServicePositioning.created_at.desc())
        .first()
    )


def get_civil_service_positioning_history(
    db: Session, user_id: UUID
) -> list[CivilServicePositioning]:
    return (
        db.query(CivilServicePositioning)
        .filter(CivilServicePositioning.user_id == user_id)
        .order_by(CivilServicePositioning.created_at.desc())
        .all()
    )
