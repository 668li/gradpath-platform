"""求职作战室服务层 — 公司情报 + 求职定位 + 求职暗知识。

借鉴 grad_intel_service 的三段式结构，覆盖求职全流程的信息差。
"""

import json
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.career_intel import CareerDarkKnowledge, CareerPositioning, CompanyIntel
from app.services.ai_orchestrator import AIOrchestrator

# 阶段名称映射
STAGE_NAMES = {
    "self_awareness": "自我认知",
    "application": "简历投递",
    "interview": "面试阶段",
    "signing": "签约阶段",
    "onboarding": "入职阶段",
}


def get_career_dark_knowledge_by_stage(
    db: Session,
    stage: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[CareerDarkKnowledge], int]:
    """按阶段获取暗知识列表，支持分页。"""
    query = db.query(CareerDarkKnowledge)
    if stage:
        query = query.filter(CareerDarkKnowledge.stage == stage)

    total = query.count()
    offset = (page - 1) * limit
    items = query.order_by(CareerDarkKnowledge.sort_order).offset(offset).limit(limit).all()

    return items, total


def get_career_dark_knowledge_stages(db: Session) -> list[dict]:
    """获取各阶段的统计信息。"""
    results = []
    for stage_code, stage_name in STAGE_NAMES.items():
        count = (
            db.query(CareerDarkKnowledge).filter(CareerDarkKnowledge.stage == stage_code).count()
        )
        results.append(
            {
                "stage": stage_code,
                "stage_name": stage_name,
                "count": count,
            }
        )
    return results


# ===== 公司情报服务 =====


async def query_company_intel(company_name: str, position_name: str) -> dict:
    """AI 查询公司情报。不落库，返回结构化结果供前端预览。"""
    system_prompt = """你是一位资深职场情报分析师，专门分析中国企业的真实工作环境和招聘信息。

用户会提供公司名称和岗位名称，你需要输出结构化的公司情报。

严格输出以下 JSON 格式（不要输出任何其他内容）：
```json
{
  "company_name": "公司名称",
  "position_name": "岗位名称",
  "industry": "所属行业",
  "overtime_intensity": "none/mild/moderate/severe/unknown",
  "layoff_risk": "none/low/moderate/high/unknown",
  "promotion_outlook": "good/fair/poor/unknown",
  "education_barrier": "none/mild/moderate/severe/unknown",
  "salary_honesty": "honest/exaggerated/misleading/unknown",
  "culture_fit": "good/neutral/toxic/unknown",
  "salary_range": "该岗位的薪资范围描述，如 15-25k*16",
  "actual_salary": "实际到手薪资描述，注意绩效和年终的浮动",
  "interview_style": "面试风格描述，如 3轮：笔试+技术面+HR面，偏算法和系统设计",
  "interview_rounds": 面试轮数（整数）,
  "turnover_rate": "人员流动率描述，如 年流动率约15%",
  "growth_path": "晋升路径描述，如 初级-高级-专家-架构师，约3年一级",
  "insider_notes": "内部消息和注意事项，如 近期有裁员传闻、XX部门加班严重等",
  "risk_warnings": ["风险提示列表，每条一句话"],
  "data_sources": ["数据来源说明，如 看准网员工评价、脉脉匿名爆料、公开财报等"],
  "tags": ["标签列表，如 互联网、大厂、996、高薪"],
  "ai_summary": "100-200字的综合分析总结"
}
```

枚举值说明：
- overtime_intensity: none=不加班, mild=偶尔加班, moderate=经常加班, severe=严重加班/996
- layoff_risk: none=无风险, low=低风险, moderate=有风险, high=高风险
- promotion_outlook: good=晋升通畅, fair=一般, poor=晋升困难
- education_barrier: none=不卡学历, mild=轻微偏好, moderate=明显偏好, severe=严格卡学历
- salary_honesty: honest=薪资透明, exaggerated=部分夸大, misleading=严重误导
- culture_fit: good=氛围好, neutral=一般, toxic=氛围差

重要：不确定的信息一律标为 unknown 或 null，不要编造。所有判断都要基于公开可查的信息。"""

    user_content = (
        f"公司：{company_name}\n岗位：{position_name}\n\n请提供这家公司这个岗位的真实情报。"
    )

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
    data.setdefault("company_name", company_name)
    data.setdefault("position_name", position_name)
    data.setdefault("industry", "")
    data.setdefault("overtime_intensity", "unknown")
    data.setdefault("layoff_risk", "unknown")
    data.setdefault("promotion_outlook", "unknown")
    data.setdefault("education_barrier", "unknown")
    data.setdefault("salary_honesty", "unknown")
    data.setdefault("culture_fit", "unknown")
    data.setdefault("risk_warnings", [])
    data.setdefault("data_sources", [])
    data.setdefault("tags", [])
    data.setdefault("ai_summary", "")

    return data


def save_company_intel(db: Session, user_id: UUID, data: dict) -> CompanyIntel:
    """保存公司情报。"""
    intel = CompanyIntel(user_id=user_id, **data)
    db.add(intel)
    db.commit()
    db.refresh(intel)
    return intel


def get_user_company_intel_list(db: Session, user_id: UUID) -> list[CompanyIntel]:
    return (
        db.query(CompanyIntel)
        .filter(CompanyIntel.user_id == user_id)
        .order_by(CompanyIntel.created_at.desc())
        .all()
    )


def delete_company_intel(db: Session, user_id: UUID, intel_id: UUID) -> bool:
    intel = (
        db.query(CompanyIntel)
        .filter(CompanyIntel.id == intel_id, CompanyIntel.user_id == user_id)
        .first()
    )
    if not intel:
        return False
    db.delete(intel)
    db.commit()
    return True


# ===== 求职定位服务 =====


async def create_career_positioning(db: Session, user_id: UUID, data: dict) -> CareerPositioning:
    """创建求职定位，自动触发 AI 评估。"""
    positioning = CareerPositioning(user_id=user_id, **data)
    db.add(positioning)
    db.commit()
    db.refresh(positioning)

    # AI 生成评估
    try:
        ai_result = await _generate_career_assessment(positioning)
        positioning.ai_assessment = ai_result.get("ai_assessment", "")
        positioning.competitiveness_score = ai_result.get("competitiveness_score")
        positioning.reach_companies = ai_result.get("reach_companies", [])
        positioning.target_companies = ai_result.get("target_companies", [])
        positioning.safety_companies = ai_result.get("safety_companies", [])
        positioning.salary_estimate = ai_result.get("salary_estimate", "")
        positioning.skill_gaps = ai_result.get("skill_gaps", [])
        positioning.risk_warnings = ai_result.get("risk_warnings", [])
        db.commit()
        db.refresh(positioning)
    except Exception:
        positioning.ai_assessment = "AI 评估暂时不可用，请稍后重试。"
        db.commit()
        db.refresh(positioning)

    return positioning


async def _generate_career_assessment(positioning: CareerPositioning) -> dict:
    """AI 生成求职定位评估。"""
    system_prompt = """你是一位资深职业规划师和猎头顾问，深谙中国就业市场的信息不对称。

用户会提供个人背景信息，你需要：
1. 评估其在求职市场的竞争力（0-100分）
2. 推荐三档目标公司：冲刺（20-40%概率）、匹配（50-70%概率）、保底（80-95%概率）
3. 估算合理的薪资区间
4. 指出能力差距
5. 给出风险提示

严格输出以下 JSON 格式（不要输出任何其他内容）：
```json
{
  "ai_assessment": "300-500字的综合评估，包括竞争力分析、市场定位建议、核心优势与劣势",
  "competitiveness_score": 0到100的整数,
  "reach_companies": [
    {"name": "公司名", "position": "岗位", "tier": "公司层次如大厂/独角兽", "reason": "推荐理由", "probability": 30}
  ],
  "target_companies": [
    {"name": "公司名", "position": "岗位", "tier": "公司层次", "reason": "推荐理由", "probability": 60}
  ],
  "safety_companies": [
    {"name": "公司名", "position": "岗位", "tier": "公司层次", "reason": "推荐理由", "probability": 90}
  ],
  "salary_estimate": "如 15-22k*14-16薪",
  "skill_gaps": [
    {"skill": "缺失技能名", "importance": "critical/high/medium", "suggestion": "如何补齐的建议"}
  ],
  "risk_warnings": ["风险提示列表，每条一句话"]
}
```

每档推荐 3-5 家公司。公司名称要具体真实（如确实不了解可给行业典型公司名）。
不确定的评分给中间值，不要给极端值。"""

    user_content = f"""个人背景：
学历层次：{positioning.education_level}
学校层次：{positioning.school_tier or '未提供'}
专业：{positioning.major or '未提供'}
毕业年份：{positioning.graduation_year or '未提供'}
GPA：{positioning.gpa or '未提供'}
实习经历：{positioning.internships or '未提供'}
技能：{', '.join(positioning.skills) if positioning.skills else '未提供'}
竞赛获奖：{', '.join(positioning.competitions) if positioning.competitions else '未提供'}
项目经历：{positioning.projects or '未提供'}
证书：{positioning.certifications or '未提供'}
目标行业：{positioning.target_industry or '未提供'}
目标岗位：{positioning.target_position or '未提供'}
目标城市：{positioning.target_city or '未提供'}
期望薪资：{positioning.salary_expectation or '未提供'}
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
    data.setdefault("reach_companies", [])
    data.setdefault("target_companies", [])
    data.setdefault("safety_companies", [])
    data.setdefault("salary_estimate", "")
    data.setdefault("skill_gaps", [])
    data.setdefault("risk_warnings", [])

    return data


def get_latest_career_positioning(db: Session, user_id: UUID) -> CareerPositioning | None:
    return (
        db.query(CareerPositioning)
        .filter(CareerPositioning.user_id == user_id)
        .order_by(CareerPositioning.created_at.desc())
        .first()
    )


def get_career_positioning_history(db: Session, user_id: UUID) -> list[CareerPositioning]:
    return (
        db.query(CareerPositioning)
        .filter(CareerPositioning.user_id == user_id)
        .order_by(CareerPositioning.created_at.desc())
        .all()
    )
