"""Evidence Provider Registry：把现有结构化数据变成可验证证据来源。"""
from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.employment_data import EmploymentData
from app.models.grad_intel import GradScorelineRecord
from app.models.gwy_position import GwyPosition
from app.models.gwy_province_position import GwyProvincePosition
from app.models.salary_benchmark import SalaryBenchmark
from app.models.school import School
from app.services.ai_orchestrator import AIOrchestrator


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    label: str
    description: str
    needs: tuple[str, ...]


PROVIDERS = (
    ProviderSpec("university", "University Provider", "院校基础信息与就业/升学指标", ("school", "university", "college", "院校", "学校")),
    ProviderSpec("cutoff", "Cutoff Provider", "考研复试线与招生结果历史数据", ("cutoff", "admission", "score", "分数线", "复试线", "上岸")),
    ProviderSpec("salary", "Salary Provider", "岗位/城市/经验薪资基准", ("salary", "income", "pay", "薪资", "工资", "收入")),
    ProviderSpec("company", "Company Provider", "公司规模、行业与基础画像", ("company", "employer", "公司", "企业", "雇主")),
    ProviderSpec("recruitment", "Recruitment Provider", "岗位需求与招聘条件", ("job", "recruitment", "hiring", "岗位", "招聘", "就业")),
    ProviderSpec("civil_service", "Civil Service Provider", "国考与省考职位要求", ("civil", "government", "公务员", "国考", "省考", "考公")),
    ProviderSpec("employment", "Employment Outcome Provider", "学校/专业就业率、去向与雇主分布", ("employment", "outcome", "就业率", "就业去向", "毕业去向")),
)


def route_hypothesis(statement: str) -> list[ProviderSpec]:
    """第一版稳定、可测试的 Hypothesis → Provider 路由器。"""
    text = (statement or "").lower()
    scored: list[tuple[int, ProviderSpec]] = []
    for provider in PROVIDERS:
        score = sum(1 for keyword in provider.needs if keyword.lower() in text)
        if score:
            scored.append((score, provider))
    scored.sort(key=lambda item: (-item[0], PROVIDERS.index(item[1])))
    return [provider for _, provider in scored]



async def route_hypothesis_with_ai(statement: str) -> dict[str, Any]:
    """让 LLM 在白名单 Provider 中选择；解析失败时安全回退到规则路由。"""
    specs = "\n".join(
        f"- {p.name}: {p.label}；{p.description}；触发需求: {', '.join(p.needs)}"
        for p in PROVIDERS
    )
    prompt = f"""你是 GradPath 的 Evidence Provider Router。
根据用户的 Hypothesis，选择需要查询的 Provider。只能从白名单中选择，允许多选。
不要回答假设是否正确，不要推荐人生选择，只判断需要什么证据。
输出严格 JSON：{"providers":["provider_name"],"evidence_needs":["..."],"reason":"..."}。

白名单：
{specs}

Hypothesis：{statement}"""
    try:
        raw = await AIOrchestrator().chat(
            system_prompt="你是一个严格的证据检索路由器。只做 Provider 选择。",
            user_prompt=prompt,
            timeout=20,
        )
        payload = json.loads(raw)
        allowed = {x.name for x in PROVIDERS}
        selected = [p for p in payload.get("providers", []) if p in allowed]
        if selected:
            return {
                "providers": selected,
                "evidence_needs": payload.get("evidence_needs", []),
                "reason": payload.get("reason", "AI 根据 Hypothesis 选择了白名单 Provider。"),
                "router": "ai",
            }
    except Exception:
        logger.exception("AI Evidence Provider routing failed; falling back to deterministic routing")
    fallback = route_hypothesis(statement)
    return {
        "providers": [p.name for p in fallback],
        "evidence_needs": [],
        "reason": "AI 路由不可用，已回退到可解释规则路由。",
        "router": "rules_fallback",
    }

def _metadata(provider: ProviderSpec, *, source_url: str | None, observed_on: Any) -> dict:
    return {
        "provider": provider.name,
        "provider_label": provider.label,
        "verification_status": "internal_unverified",
        "evidence_origin": "gradpath_internal_dataset",
        "source_url": source_url,
        "observed_on": observed_on.isoformat() if hasattr(observed_on, "isoformat") else observed_on,
        "verification_note": "内部数据命中不等于外部官方已复核；需要时继续走外部验证。",
    }


def _like(column, *terms: str):
    clauses = [column.ilike(f"%{term}%") for term in terms if term]
    return or_(*clauses) if clauses else None


def search_provider(db: Session, provider_name: str, statement: str, limit: int = 5) -> dict:
    """查询一个 Provider，返回可直接转成 DecisionEvidence 的候选证据。"""
    provider = next((p for p in PROVIDERS if p.name == provider_name), None)
    if provider is None:
        raise ValueError(f"未知 Evidence Provider: {provider_name}")
    limit = max(1, min(limit, 20))
    rows: list[dict] = []
    terms = [t for t in statement.replace("，", " ").replace("。", " ").split() if len(t) >= 2][:4]

    if provider_name == "university":
        query = db.query(School)
        if terms:
            query = query.filter(or_(*[_like(School.name, t) for t in terms]))
        for row in query.limit(limit).all():
            rows.append({
                "title": f"院校：{row.name}",
                "claim": f"{row.name}：{row.province or '地区未知'}，层次={row.level or '未知'}，就业率={row.employment_rate if row.employment_rate is not None else '未知'}",
                "source_url": row.report_index_url,
                "reliability": 3,
                "metadata": _metadata(provider, source_url=row.report_index_url, observed_on=row.updated_at),
            })

    elif provider_name == "cutoff":
        query = db.query(GradScorelineRecord)
        if terms:
            query = query.filter(or_(*[_like(GradScorelineRecord.university_name, t) for t in terms], *[_like(GradScorelineRecord.major_name, t) for t in terms]))
        for row in query.order_by(GradScorelineRecord.year.desc()).limit(limit).all():
            source = row.data_sources[0] if row.data_sources and isinstance(row.data_sources[0], str) else None
            rows.append({
                "title": f"分数线：{row.university_name} {row.major_name} {row.year}",
                "claim": f"{row.year} {row.university_name} {row.major_name}：总分线={row.total_score_line if row.total_score_line is not None else '未知'}，报名={row.application_count if row.application_count is not None else '未知'}，录取={row.enrollment_count if row.enrollment_count is not None else '未知'}",
                "source_url": source,
                "reliability": 4 if source else 3,
                "metadata": _metadata(provider, source_url=source, observed_on=row.updated_at),
            })

    elif provider_name == "salary":
        query = db.query(SalaryBenchmark)
        if terms:
            query = query.filter(or_(*[_like(SalaryBenchmark.position, t) for t in terms], *[_like(SalaryBenchmark.company, t) for t in terms]))
        for row in query.order_by(SalaryBenchmark.year.desc()).limit(limit).all():
            rows.append({
                "title": f"薪资：{row.position}",
                "claim": f"{row.year} {row.position}（{row.city or '城市未知'}，{row.experience_level.value}）：薪资 {row.salary_min}-{row.salary_max}，中位数 {row.salary_median}",
                "source_url": None,
                "reliability": 3,
                "metadata": _metadata(provider, source_url=None, observed_on=row.updated_at),
            })

    elif provider_name == "company":
        query = db.query(Company)
        if terms:
            query = query.filter(or_(*[_like(Company.name, t) for t in terms], *[_like(Company.industry, t) for t in terms]))
        for row in query.limit(limit).all():
            rows.append({
                "title": f"公司：{row.name}",
                "claim": f"{row.name}：行业={row.industry}，规模={row.size.value}，总部={row.headquarters or '未知'}",
                "source_url": None,
                "reliability": 3,
                "metadata": _metadata(provider, source_url=None, observed_on=row.updated_at),
            })

    elif provider_name in {"recruitment", "civil_service"}:
        query = db.query(GwyPosition)
        if terms:
            query = query.filter(or_(*[_like(GwyPosition.position_name, t) for t in terms], *[_like(GwyPosition.major_req, t) for t in terms], *[_like(GwyPosition.position_desc, t) for t in terms], *[_like(GwyPosition.dept_name, t) for t in terms]))
        for row in query.order_by(GwyPosition.year.desc()).limit(limit).all():
            rows.append({
                "title": f"{'国考' if provider_name == 'civil_service' else '招聘'}：{row.position_name or row.position_code}",
                "claim": f"{row.year}：{row.dept_name or '未知部门'} / {row.position_name or '未命名'}，招录={row.recruit_count if row.recruit_count is not None else '未知'}，学历={row.education_req or '未知'}，专业={row.major_req or '未知'}",
                "source_url": row.source_url,
                "reliability": 5 if row.source_url else 4,
                "metadata": _metadata(provider, source_url=row.source_url, observed_on=row.updated_at),
            })

        # 省考职位同属公考/招聘 Evidence Provider，避免已有省考数据留在孤岛。
        province_query = db.query(GwyProvincePosition)
        if terms:
            province_query = province_query.filter(or_(*[_like(GwyProvincePosition.position_name, t) for t in terms], *[_like(GwyProvincePosition.major_req_grad, t) for t in terms], *[_like(GwyProvincePosition.major_req_undergrad, t) for t in terms], *[_like(GwyProvincePosition.dept_name, t) for t in terms]))
        for row in province_query.order_by(GwyProvincePosition.year.desc()).limit(limit).all():
            rows.append({
                "title": f"省考：{row.position_name or row.position_code}",
                "claim": f"{row.year} {row.province}：{row.dept_name or '未知部门'} / {row.position_name or '未命名'}，招录={row.recruit_count if row.recruit_count is not None else '未知'}，学历={row.education_req or '未知'}，专业={row.major_req_grad or row.major_req_undergrad or '未知'}",
                "source_url": row.source_url,
                "reliability": 5 if row.source_url else 4,
                "metadata": _metadata(provider, source_url=row.source_url, observed_on=row.updated_at),
            })

    elif provider_name == "employment":
        query = db.query(EmploymentData)
        if terms:
            query = query.filter(or_(*[_like(EmploymentData.major, t) for t in terms], *[_like(EmploymentData.major_category, t) for t in terms]))
        for row in query.order_by(EmploymentData.year.desc().nullslast()).limit(limit).all():
            rows.append({
                "title": f"就业结果：{row.school_name or '学校未知'} {row.major or row.major_category or '专业未知'}",
                "claim": f"{row.year or '年份未知'}：就业率={row.employment_rate if row.employment_rate is not None else '未知'}%，深造率={row.further_study_rate if row.further_study_rate is not None else '未知'}%，平均薪资={row.average_salary if row.average_salary is not None else '未知'}",
                "source_url": row.source_url,
                "reliability": 4 if row.source_url else 3,
                "metadata": _metadata(provider, source_url=row.source_url, observed_on=row.updated_at),
            })

    return {"provider": provider.name, "label": provider.label, "count": len(rows), "items": rows}
