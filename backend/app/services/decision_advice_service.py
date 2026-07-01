# backend/app/services/decision_advice_service.py
"""AI 决策指导服务层 — 组装 context、调用 LLM、解析返回。

Context 注入优先级：用户画像 > 薪资基准 > 社区数据 > 市场趋势。
"""
import json
import re
import uuid
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent
from app.models.community_report import CommunityReport
from app.models.company import Company
from app.models.destination_decision import DestinationDecision
from app.models.interview_report import InterviewReport
from app.models.market_data import MarketData
from app.models.salary_benchmark import SalaryBenchmark
from app.models.skill_node import SkillNode
from app.models.user import User
from app.schemas.ai import DecisionAdviceRequest, DecisionAdviceResponse
from app.services.ai_service import AIService
from app.services.employment_service import escape_like

# 用户最近职业事件条数
RECENT_EVENT_LIMIT = 5
# 各类市场/社区数据查询条数上限
SALARY_LIMIT = 10
MARKET_LIMIT = 10
COMMUNITY_LIMIT = 10
INTERVIEW_LIMIT = 10

SYSTEM_PROMPT = """你是一位资深的中国职场职业规划顾问，精通互联网、金融、通信、制造、国企等行业的求职与发展路径。

你的任务：基于用户提供的个人信息（用户画像）、外部市场数据（薪资基准、行业宏观指标、公司元数据）以及社区参考（同类人去向、面试经验），为用户即将做出的毕业去向/职业决策提供个性化、结构化的分析建议。

请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "summary": "一句话总览该决策的总体评价",
  "pros": ["优势1", "优势2", "..."],
  "cons": ["风险1", "风险2", "..."],
  "market_analysis": "该岗位/公司在当前市场的需求、薪资水平与竞争激烈程度分析",
  "alternatives": [{"option": "备选方案", "reason": "推荐理由"}],
  "skill_gap": ["用户当前缺少的关键技能1", "..."],
  "confidence": 1到5的整数，表示你对这个建议的置信度,
  "advice": "一段个性化建议（200字以内），结合用户画像给出具体可执行的下一步行动"
}

注意事项：
- pros 和 cons 至少各给 2 条
- alternatives 至少给 1 个备选方案
- confidence 为 1-5 的整数
- 所有内容使用中文
- 分析要结合提供的外部数据与社区数据，避免泛泛而谈"""


def build_user_context(db: Session, user_id: UUID) -> str:
    """查询用户画像并格式化为文本。

    包含：基本信息（学校/专业/阶段）、技能树、最近 5 条职业事件、历史决策。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return "【用户画像】\n（未找到用户信息）\n"

    lines = ["【用户画像】"]
    lines.append(f"- 姓名：{user.name}")
    lines.append(f"- 当前阶段：{user.current_stage.value if user.current_stage else '未知'}")
    if user.school:
        lines.append(f"- 学校：{user.school}")
    if user.major:
        lines.append(f"- 专业：{user.major}")
    if user.graduation_year:
        lines.append(f"- 毕业年份：{user.graduation_year}")

    # 技能树（按 level 降序，取前 15 条）
    skills = (
        db.query(SkillNode)
        .filter(SkillNode.user_id == user_id)
        .order_by(SkillNode.level.desc())
        .limit(15)
        .all()
    )
    if skills:
        skill_strs = [f"{s.name}(Lv{s.level})" for s in skills]
        lines.append(f"- 核心技能：{', '.join(skill_strs)}")
    else:
        lines.append("- 核心技能：（暂无记录）")

    # 最近 5 条职业事件
    events = (
        db.query(CareerEvent)
        .filter(CareerEvent.user_id == user_id)
        .order_by(CareerEvent.event_date.desc())
        .limit(RECENT_EVENT_LIMIT)
        .all()
    )
    if events:
        lines.append("- 最近职业事件：")
        for ev in events:
            title = f"{ev.event_date} [{ev.event_type.value}] {ev.title}"
            lines.append(f"  * {title}")
    else:
        lines.append("- 最近职业事件：（暂无记录）")

    # 历史决策
    decisions = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.decision_date.desc())
        .limit(5)
        .all()
    )
    if decisions:
        lines.append("- 历史决策：")
        for d in decisions:
            lines.append(
                f"  * {d.decision_date} [{d.destination_type.value}] "
                f"状态={d.status.value} 置信度={d.confidence}"
            )
    else:
        lines.append("- 历史决策：（暂无记录）")

    return "\n".join(lines) + "\n"


def build_market_context(
    db: Session,
    company: str | None,
    position: str | None,
    city: str | None,
) -> str:
    """查询外部市场数据并格式化为文本。

    包含：薪资基准、市场宏观数据、公司元数据。
    """
    lines = ["【市场数据】"]

    # 公司元数据（精确匹配 + 模糊匹配）
    company_obj = None
    if company:
        company_obj = db.query(Company).filter(Company.name == company).first()
        if not company_obj:
            company_obj = (
                db.query(Company)
                .filter(Company.name.ilike(f"%{escape_like(company)}%", escape="\\"))
                .first()
            )
    if company_obj:
        lines.append(f"- 公司：{company_obj.name}")
        lines.append(f"  行业：{company_obj.industry}")
        lines.append(f"  规模：{company_obj.size.value}")
        if company_obj.stage:
            lines.append(f"  融资阶段：{company_obj.stage}")
        if company_obj.headquarters:
            lines.append(f"  总部：{company_obj.headquarters}")
        if company_obj.description:
            lines.append(f"  简介：{company_obj.description}")
    else:
        lines.append("- 公司：（未找到匹配的公司元数据）")

    # 薪资基准
    sal_query = db.query(SalaryBenchmark)
    if company:
        sal_query = sal_query.filter(
            SalaryBenchmark.company.ilike(f"%{escape_like(company)}%", escape="\\")
        )
    if position:
        sal_query = sal_query.filter(
            SalaryBenchmark.position.ilike(f"%{escape_like(position)}%", escape="\\")
        )
    if city:
        sal_query = sal_query.filter(
            SalaryBenchmark.city.ilike(f"%{escape_like(city)}%", escape="\\")
        )
    salaries = sal_query.order_by(SalaryBenchmark.year.desc()).limit(SALARY_LIMIT).all()
    if salaries:
        lines.append("- 薪资基准：")
        for s in salaries:
            lines.append(
                f"  * {s.company} | {s.position} | {s.city or '未指定'} | "
                f"{s.experience_level.value} | {s.salary_min}-{s.salary_median}-{s.salary_max}元/月 "
                f"(来源:{s.source} {s.year}年)"
            )
    else:
        lines.append("- 薪资基准：（未找到匹配的薪资数据）")

    # 市场宏观数据
    mkt_query = db.query(MarketData)
    if company_obj:
        mkt_query = mkt_query.filter(
            (MarketData.industry == company_obj.industry)
            | (MarketData.industry.is_(None))
        )
    market_rows = (
        mkt_query.order_by(MarketData.year.desc()).limit(MARKET_LIMIT).all()
    )
    if market_rows:
        lines.append("- 行业宏观数据：")
        for m in market_rows:
            region_str = f" 地区={m.region}" if m.region else ""
            ind_str = f" 行业={m.industry}" if m.industry else ""
            lines.append(
                f"  * {m.indicator}: {m.value}{m.unit}{region_str}{ind_str} "
                f"(来源:{m.source} {m.year}年)"
            )
    else:
        lines.append("- 行业宏观数据：（暂无数据）")

    return "\n".join(lines) + "\n"


def build_community_context(
    db: Session,
    company: str | None,
    position: str | None,
) -> str:
    """查询社区数据并格式化为文本。

    包含：InterviewReport 聚合（该公司面试经验）、CommunityReport 聚合（同类人去向）。
    """
    lines = ["【社区参考】"]

    # 面试经验聚合
    if company:
        int_query = db.query(InterviewReport).filter(
            InterviewReport.company.ilike(f"%{escape_like(company)}%", escape="\\")
        )
        if position:
            int_query = int_query.filter(
                InterviewReport.position.ilike(f"%{escape_like(position)}%", escape="\\")
            )
        interviews = (
            int_query.order_by(InterviewReport.interview_year.desc())
            .limit(INTERVIEW_LIMIT)
            .all()
        )
        if interviews:
            total = (
                db.query(func.count(InterviewReport.id))
                .filter(
                    InterviewReport.company.ilike(
                        f"%{escape_like(company)}%", escape="\\"
                    )
                )
                .scalar()
                or 0
            )
            lines.append(f"- 面试经验（共 {total} 条记录，展示前 {len(interviews)} 条）：")
            offer_count = sum(1 for i in interviews if i.result and i.result.value == "offer")
            lines.append(f"  Offer 率（展示样本）：{offer_count}/{len(interviews)}")
            for it in interviews:
                dims = ",".join(it.dimensions) if it.dimensions else "无"
                diff = f"难度{i.difficulty}" if i.difficulty is not None else "难度未知"
                lines.append(
                    f"  * {it.company}|{it.position} {it.interview_year}年 "
                    f"{it.result.value if it.result else '未知'} {diff} 维度:{dims}"
                )
        else:
            lines.append("- 面试经验：（该公司暂无面试经验记录）")
    else:
        lines.append("- 面试经验：（未指定公司，跳过）")

    # 同类人去向聚合（按 employer 分布）
    comm_query = db.query(CommunityReport)
    if company:
        comm_query = comm_query.filter(
            CommunityReport.employer.ilike(f"%{escape_like(company)}%", escape="\\")
        )
    comm_rows = (
        comm_query.order_by(CommunityReport.graduation_year.desc())
        .limit(COMMUNITY_LIMIT)
        .all()
    )
    if comm_rows:
        lines.append(
            f"- 同类人去向（展示前 {len(comm_rows)} 条）："
        )
        # 薪资分布聚合
        sal_dist: dict[str, int] = {}
        dest_dist: dict[str, int] = {}
        for c in comm_rows:
            if c.salary_range:
                sal_dist[c.salary_range.value] = sal_dist.get(c.salary_range.value, 0) + 1
            if c.destination_type:
                dest_dist[c.destination_type.value] = (
                    dest_dist.get(c.destination_type.value, 0) + 1
                )
        if dest_dist:
            dest_str = ", ".join(f"{k}:{v}" for k, v in dest_dist.items())
            lines.append(f"  去向分布：{dest_str}")
        if sal_dist:
            sal_str = ", ".join(f"{k}:{v}" for k, v in sal_dist.items())
            lines.append(f"  薪资分布：{sal_str}")
        for c in comm_rows:
            sal = c.salary_range.value if c.salary_range else "未透露"
            lines.append(
                f"  * {c.school_name} {c.major} {c.graduation_year}届 "
                f"-> {c.employer or '未知'}({c.city or '未知'}) 薪资:{sal}"
            )
    else:
        lines.append("- 同类人去向：（暂无匹配的社区报告）")

    return "\n".join(lines) + "\n"


def _parse_llm_json(content: str) -> dict:
    """解析 LLM 返回的 JSON，支持容错。

    1. 尝试直接 json.loads
    2. 失败则用正则提取 ```json...``` 代码块
    3. 再失败则将原始文本放入 advice 字段返回
    """
    # 1. 直接解析
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. 提取 markdown 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    # 2.5 兜底：提取第一个 {...} 块
    brace_match = re.search(r"\{.*\}", content, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except (json.JSONDecodeError, TypeError):
            pass

    # 3. 返回原始文本
    return {
        "summary": "无法解析 AI 返回的结构化结果",
        "pros": [],
        "cons": [],
        "market_analysis": "",
        "alternatives": [],
        "skill_gap": [],
        "confidence": 1,
        "advice": content,
    }


def _coerce_response(data: dict) -> DecisionAdviceResponse:
    """将解析后的 dict 强制转换为 DecisionAdviceResponse，容忍字段缺失/类型错误。"""
    def _get_list(key: str) -> list:
        v = data.get(key, [])
        return v if isinstance(v, list) else []

    def _get_int(key: str, default: int = 3) -> int:
        v = data.get(key, default)
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    alts_raw = data.get("alternatives", [])
    if not isinstance(alts_raw, list):
        alts_raw = []
    alternatives = []
    for a in alts_raw:
        if isinstance(a, dict):
            alternatives.append(
                {
                    "option": str(a.get("option", "")),
                    "reason": str(a.get("reason", "")),
                }
            )

    return DecisionAdviceResponse(
        summary=str(data.get("summary", "")),
        pros=[str(p) for p in _get_list("pros")],
        cons=[str(c) for c in _get_list("cons")],
        market_analysis=str(data.get("market_analysis", "")),
        alternatives=alternatives,
        skill_gap=[str(s) for s in _get_list("skill_gap")],
        confidence=_get_int("confidence", 3),
        advice=str(data.get("advice", "")),
    )


def get_decision_advice(
    db: Session, user: User, request: DecisionAdviceRequest
) -> DecisionAdviceResponse:
    """组装全部 context，调用 AIService.chat()，解析 LLM 返回的 JSON。

    Args:
        db: 数据库会话
        user: 当前登录用户
        request: 决策指导请求

    Returns:
        DecisionAdviceResponse 结构化建议
    """
    # 组装 context（优先级：用户画像 > 薪资基准 > 社区数据 > 市场趋势）
    user_ctx = build_user_context(db, user.id)
    market_ctx = build_market_context(db, request.company, request.position, request.city)
    community_ctx = build_community_context(db, request.company, request.position)

    # 组装用户请求描述
    req_lines = ["【用户决策请求】"]
    req_lines.append(f"- 去向类型：{request.destination_type}")
    if request.company:
        req_lines.append(f"- 意向公司：{request.company}")
    if request.position:
        req_lines.append(f"- 意向岗位：{request.position}")
    if request.city:
        req_lines.append(f"- 意向城市：{request.city}")
    if request.expected_salary:
        req_lines.append(f"- 期望薪资：{request.expected_salary}")
    req_lines.append("")
    req_lines.append("请基于以上信息给出结构化的决策建议（严格按 JSON 格式输出）。")
    user_content = "\n".join(req_lines)

    full_content = (
        f"{user_ctx}\n{market_ctx}\n{community_ctx}\n{user_content}"
    )

    # 调用 LLM
    service = AIService()
    raw = service.chat(SYSTEM_PROMPT, full_content)

    # 解析返回
    data = _parse_llm_json(raw)
    return _coerce_response(data)
