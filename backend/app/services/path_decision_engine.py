"""两路对比决策引擎 — 用真实数据聚合考研/就业两条路（考公路已于 2026-09-26 随考公线退役删除）。

设计目标（与「决策引擎」方向一致）：
- 不依赖 LLM：纯规则聚合，未配置 LLM 也不会 503。
- 每个数字都来自现有数据库，可溯源（source_url / data_sources）。
- 没有数据的指标诚实降级为占位文本，绝不编造。

数据来源：
- 考研路：grad_scoreline_records（复试分数线/报录情况）+ grad_yanzhao_programs（招生目录）
- 就业路：market_data（宏观薪资带）+ salary_benchmarks（城市岗位薪资）+ schools（就业率/考研率）

输出兼容 path_comparison_service 的 PathMetrics 结构（extra 字段 evidence），
持久化复用 PathComparison 表（JSONB），不新建表。
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, load_only

from app.core.cache import cache
from app.models.grad_intel import GradSchoolIntel, GradScorelineRecord, GradYanzhaoProgram
from app.models.market_data import MarketData
from app.models.salary_benchmark import SalaryBenchmark
from app.models.school import School
from app.services.employment_service import escape_like
from app.services.grad_intel_service import scoreline_has_traceable_source

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# 常量限制（镜像 decision_advice_service 风格）
# ----------------------------------------------------------------------
# 各表最多取回的样本数（用于证据展示，聚合仍用全量）
SCORELINE_LIMIT = 8
YANZHAO_LIMIT = 5
MARKET_LIMIT = 8
SALARY_LIMIT = 8
SCHOOL_LIMIT = 5

# 主观评分（无法从数据溯源的部分，明确标注为行业公开认知的固定评估）
_TIME_COST = {"kaoyan": 12, "employment": 3}
_GROWTH_SCORE = {"kaoyan": 7, "employment": 6}

# 路径中文标签（与前端 PATH_PRESETS 对齐）
PATH_LABELS = {
    "kaoyan": "考研深造",
    "employment": "直接就业",
}

# 空数据占位（诚实降级）
_NO_DATA = "暂无相关数据"

# ----------------------------------------------------------------------
# 个人条件包（决策飞轮第一圈）
# ----------------------------------------------------------------------
# 学历档位（用于 education_req 匹配）
_EDU_RANK = {"大专": 1, "本科": 2, "硕士": 3, "博士": 4}
# 应届限定词：出现在 remarks 中即视为「限应届」岗（"非应届"表述优先排除）
_FRESH_MARKERS = ("限应届", "仅限应届", "面向应届毕业生", "应届高校毕业生")
# 进面线分级阈值（预估分相对岗位进面线）
_STEADY_DIFF = 10  # 高于进面线 10+ 分 → 稳健；低于 10+ 分 → 冲刺
# 劝退阈值：低于进面线 20+ 分 → 建议放弃（诚实拒绝）。
# 宁缺毋滥：阈值取「冲刺档再跌一整档」，且数据不足时不出卡——
# 劝退错一次毁掉的信任十倍于推荐对一次。
_DISCOURAGE_DIFF = 20
# 考研劝退阈值：模考估分低于复试线 30+ 分 → 建议放弃。
# 考研初试 500 分制、复试线只是门槛（录取均分更高），30 分是"冲刺档（10 分）的三倍"，
# 纪律：宁可少劝，不可错劝。
_KAOYAN_DISCOURAGE_DIFF = 30
# analyze 结果缓存：同输入（专业/地区/条件包）直接复用，TTL 10 分钟（数据每日更新）
_DECISION_CACHE_TTL = 600

# B3（2026-09-26）：省级 region → salary_benchmarks.city 的市级值映射（城市集合=表内实际有数据的市）。
# 键为省级短名（region.rstrip("省") 后查表）；直辖市/市名本身经 city.like 子串直接命中，不进本表。
# 表内 city 全集实况（2026-09-26 生产复核）：东莞市/广州市/杭州市/武汉市/济南市/深圳市/重庆市/长三角一体化示范区。
_PROVINCE_CITIES: dict[str, tuple[str, ...]] = {
    "广东": ("广州市", "深圳市", "东莞市"),
    "浙江": ("杭州市",),
    "湖北": ("武汉市",),
    "山东": ("济南市",),
}


# ----------------------------------------------------------------------
# 主入口
# ----------------------------------------------------------------------
def generate_decision(
    db: Session,
    major: str,
    region: str | None = None,
    school_tier: str | None = None,
    graduation_year: int | None = None,
    *,
    fresh_status: str | None = None,
    party_status: str | None = None,
    education: str | None = None,
    has_grassroots: bool | None = None,
    gender: str | None = None,
    estimated_score: int | None = None,
    kaoyan_estimated_score: int | None = None,
) -> dict[str, Any]:
    """生成两路对比结果（考研 / 就业）。

    Args:
        db: 数据库会话
        major: 专业关键词（如「计算机」）
        region: 地区（如「广东」；就业路限定城市/省份）
        school_tier: 学校层次（985/211/双一流/普通；用于考研难度与就业参考）
        graduation_year: 毕业年份（默认 2026）
        fresh_status / party_status / education / has_grassroots / gender:
            个人条件包（keyword-only，全部默认 None → 与旧行为完全兼容），
            参与考研院校匹配与就业参考，均为可选。
        estimated_score: 已退役的考公估分字段（200 分制），仅保留请求兼容，
            不再产生任何考公语义输出。
        kaoyan_estimated_score: 考研初试模考估分（500 分制），参与院校冲稳保派生。

    Returns:
        {
            "metrics": [2 条 PathMetrics 兼容 dict（含 evidence）, ...],
            "recommendation": 条件式综合建议文本,
            "input": {major, region, school_tier, graduation_year, ...个人条件},
            "position_analysis": None（考公路 2026-09-26 退役，恒为 None）,
            "school_analysis": 考研院校级分析（竞争档位/隐性情报）| None,
        }
    """
    year = graduation_year or 2026
    cache_key = "pathdecision:" + ":".join(
        str(x)
        for x in (
            major,
            region,
            school_tier,
            graduation_year,
            fresh_status,
            party_status,
            education,
            has_grassroots,
            gender,
            estimated_score,
            kaoyan_estimated_score,
        )
    )
    cached_decision = cache.get(cache_key)
    if cached_decision is not None:
        return cached_decision

    input_summary = {
        "major": major,
        "region": region or "全国",
        "school_tier": school_tier or "不限",
        "graduation_year": year,
    }
    # 个人条件包（None 即未填写，该维度不过滤）
    conditions: dict[str, Any] = {}
    if fresh_status:
        conditions["fresh_status"] = fresh_status
        input_summary["fresh_status"] = fresh_status
    if party_status:
        conditions["party_status"] = party_status
        input_summary["party_status"] = party_status
    if education:
        conditions["education"] = education
        input_summary["education"] = education
    if has_grassroots is not None:
        conditions["has_grassroots"] = has_grassroots
        input_summary["has_grassroots"] = has_grassroots
    if gender:
        conditions["gender"] = gender
        input_summary["gender"] = gender
    if estimated_score is not None:
        conditions["estimated_score"] = estimated_score
        input_summary["estimated_score"] = estimated_score
    if kaoyan_estimated_score is not None:
        conditions["kaoyan_estimated_score"] = kaoyan_estimated_score
        input_summary["kaoyan_estimated_score"] = kaoyan_estimated_score

    kaoyan, school_analysis = _build_kaoyan_path(db, major, school_tier, kaoyan_estimated_score)
    employment = _build_employment_path(db, major, region, school_tier)

    metrics = [kaoyan, employment]
    recommendation = _build_recommendation(metrics, input_summary, conditions)

    decision = {
        "metrics": metrics,
        "recommendation": recommendation,
        "input": input_summary,
        "position_analysis": None,
        "school_analysis": school_analysis,
    }
    cache.set(cache_key, decision, ttl=_DECISION_CACHE_TTL)
    return decision


# ----------------------------------------------------------------------
# 考研路
# ----------------------------------------------------------------------
def _build_kaoyan_path(
    db: Session, major: str, school_tier: str | None, est: int | None = None
) -> dict[str, Any]:
    pattern = f"%{escape_like(major)}%"
    # 一次取回全部命中行，count/聚合/证据/院校级分析都在 Python 侧算（原来同一查询跑 3 遍）
    rows = (
        db.query(GradScorelineRecord)
        .options(
            load_only(
                GradScorelineRecord.university_name,
                GradScorelineRecord.major_name,
                GradScorelineRecord.degree_type,
                GradScorelineRecord.year,
                GradScorelineRecord.total_score_line,
                GradScorelineRecord.application_count,
                GradScorelineRecord.enrollment_count,
                GradScorelineRecord.data_sources,
            )
        )
        .filter(GradScorelineRecord.major_name.ilike(pattern, escape="\\"))
        .all()
    )
    # 溯源过滤：data_sources 只写机构泛称（无 URL/数据文件可核验）的记录不进决策依据
    rows = [r for r in rows if scoreline_has_traceable_source(r.data_sources)]
    total = len(rows)
    evidence: list[dict[str, Any]] = []

    if total == 0:
        return (
            _empty_path(
                "kaoyan",
                "考研深造",
                "该专业暂无分数线数据，可尝试更宽泛的关键词（如只输入学科大类）。",
            ),
            None,
        )

    # 分数线聚合（total_score_line=0 为脏数据占位，视为未公布，排除后再聚合）
    line_rows_all = [r for r in rows if r.total_score_line is not None and r.total_score_line > 0]
    line_scores = [r.total_score_line for r in line_rows_all]
    avg_line = sum(line_scores) / len(line_scores) if line_scores else None
    min_line = min(line_scores) if line_scores else None
    max_line = max(line_scores) if line_scores else None
    if line_rows_all:
        year_min = min(r.year for r in line_rows_all)
        year_max = max(r.year for r in line_rows_all)
    else:
        year_min = year_max = None
    line_desc = _format_line(avg_line, min_line, max_line)

    # 报录情况：有 application_count 与 enrollment_count 的条目才计算（无则诚实省略）
    ratio_rows = [
        r for r in rows if r.application_count is not None and r.enrollment_count is not None
    ]
    ratio_rows.sort(key=lambda r: r.year, reverse=True)
    ratio_samples: list[str] = []
    ratio_ev: list[dict[str, Any]] = []
    for row in ratio_rows[:SCORELINE_LIMIT]:
        ratio = _format_ratio(row.application_count, row.enrollment_count)
        ratio_samples.append(f"{row.university_name}（{row.year}）报录 {ratio}")
        ratio_ev.append(
            _evidence(
                f"报录比 · {row.university_name} {row.year}",
                f"报考 {row.application_count} / 录取 {row.enrollment_count}，"
                f"复试线 {row.total_score_line} 分",
                sources=row.data_sources,
            )
        )

    # 分数证据（同样排除 0 分占位脏数据）
    line_rows = sorted(line_rows_all, key=lambda r: r.year, reverse=True)[:SCORELINE_LIMIT]
    for row in line_rows:
        ev = _evidence(
            f"分数线 · {row.university_name} {row.year}",
            f"{row.major_name} 复试线 {row.total_score_line} 分",
            sources=row.data_sources,
        )
        if ev not in evidence:
            evidence.append(ev)

    # 招生目录：相关专业招生名额
    yz = db.query(GradYanzhaoProgram).filter(
        GradYanzhaoProgram.major_name.ilike(pattern, escape="\\")
    )
    yz_total, yz_quota = yz.with_entities(
        func.count(), func.sum(GradYanzhaoProgram.enrollment_quota)
    ).one()
    quota_text = (
        f"研招目录相关专业 {yz_total} 个，公布招生名额合计约 {int(yz_quota)} 人"
        if yz_quota
        else f"研招目录相关专业 {yz_total} 个"
    )
    for row in yz.limit(YANZHAO_LIMIT).all():
        ev = _evidence(
            f"招生 · {row.university_name}",
            f"{row.major_name} 招生 {row.enrollment_quota or '未公布'} 人（{row.year}）",
            sources=row.data_sources,
        )
        if ev not in evidence:
            evidence.append(ev)

    # 难度评估：有报录比样本则参考；学校层次越高越难
    risk = "high"
    risk_desc = "考研录取率通常低于 30%，备考失败损失约 1 年时间。"
    if ratio_samples:
        risk_desc = (
            "报考热度：\n" + "\n".join(f"- {s}" for s in ratio_samples[:5]) + "\n\n" + risk_desc
        )
    if school_tier:
        risk_desc += f"本科层次「{school_tier}」在复试/调剂中会影响部分院校的隐性筛选。"

    return (
        {
            "path_type": "kaoyan",
            "target_role": "考研深造",
            "income_1y": "0-5万",
            "income_3y": "暂无数据（读研期间）",
            "income_5y": "暂无数据",
            "risk_level": risk,
            "risk_description": risk_desc,
            "growth_score": _GROWTH_SCORE["kaoyan"],
            "time_cost_months": _TIME_COST["kaoyan"],
            "match_score": _coverage_score(total, 20),
            "match_description": f"依据现有数据覆盖度估算（命中 {total} 条分数线记录），"
            f"{_NO_DATA}个人画像匹配数据。",
            "pros": [
                f"相关专业分数线记录 {total} 条（{year_min}–{year_max} 年），"
                f"平均复试线 {line_desc}",
                quota_text,
            ],
            "cons": [
                "报录比数据覆盖有限（仅少量院校公开报考人数），难以精确估算竞争",
                "复试线只代表门槛，不代表录取实际难度",
            ],
            "evidence": evidence,
        },
        _build_school_analysis(db, line_rows_all, est=est),
    )


# ----------------------------------------------------------------------
# 就业路
# ----------------------------------------------------------------------
def _build_employment_path(
    db: Session, major: str, region: str | None, school_tier: str | None
) -> dict[str, Any]:
    """就业路 — market_data + salary_benchmarks + schools 兜底（employment_data 为空表）。

    B3（2026-09-26）：专业↔行业映射接入——专业名先经 major_prospect 映射表解析出
    对口行业精确名（market_data 的门类口径）再做行业查询；salary city 为市级口径，
    省级 region 经 _PROVINCE_CITIES 映射到城市集合（无映射=诚实空态）。
    """
    evidence: list[dict[str, Any]] = []
    coverage_parts: list[str] = []

    # 延迟导入：major_prospect_service 反向依赖本引擎（interpret 路径），顶层 import 成环
    from app.services.major_prospect_service import resolve_major

    _, major_entry = resolve_major(major)
    industries = list(major_entry.industries) if major_entry else []

    # ---- market_data：行业薪资带（宏观，带 source_url）----
    # 行业宏观数据多为全国口径：优先匹配地区，无命中则回退全国（诚实标注口径）。
    # 映射行业精确名命中（门类口径）与专业名子串（制造业细分含"计算机"类）取或。
    if industries:
        industry_filter = or_(
            MarketData.industry.in_(industries),
            MarketData.industry.ilike(f"%{escape_like(major)}%", escape="\\"),
        )
    else:
        industry_filter = MarketData.industry.ilike(f"%{escape_like(major)}%", escape="\\")
    md_base = db.query(MarketData).filter(industry_filter)
    md_total = 0
    scope_label = region or "全国"
    md_salary: list[str] = []
    if region:
        md_region_rows = md_base.filter(
            MarketData.region.like(f"%{escape_like(region)}%", escape="\\")
        ).all()
        md_total = len(md_region_rows)
        if md_region_rows:
            md_rows = sorted(md_region_rows, key=lambda r: r.year, reverse=True)[:MARKET_LIMIT]
        else:
            logger.info("就业路 market_data 无 %s 地区数据，回退全国口径", region)
            scope_label = f"{region}（全国口径）"
            md_rows = (
                db.query(MarketData)
                .filter(industry_filter)
                .order_by(MarketData.year.desc())
                .limit(MARKET_LIMIT)
                .all()
            )
    else:
        md_rows_all = md_base.all()
        md_total = len(md_rows_all)
        md_rows = sorted(md_rows_all, key=lambda r: r.year, reverse=True)[:MARKET_LIMIT]
    for row in md_rows:
        md_salary.append(f"{row.indicator} {_format_value(row.value, row.unit)}（{row.year}）")
        evidence.append(
            _evidence(
                f"行业数据 · {row.indicator}",
                f"{row.value} {row.unit}（{row.year}）",
                url=row.source_url,
            )
        )
    if md_salary:
        coverage_parts.append(f"{scope_label}行业薪资带：" + "、".join(md_salary[:3]))

    # ---- salary_benchmarks：城市岗位薪资（entry 级）----
    sb_scope = region or ""
    if region:
        # 城市口径：city 列是市级值（广州市/杭州市…）。region 是市名时子串直中；
        # 是省名时子串恒 miss → 经 _PROVINCE_CITIES 映射到该省城市集合（B3 口径打通）。
        sb_rows = (
            db.query(SalaryBenchmark)
            .filter(
                SalaryBenchmark.experience_level == "entry",
                SalaryBenchmark.city.like(f"%{escape_like(region)}%", escape="\\"),
            )
            .order_by(SalaryBenchmark.year.desc())
            .all()
        )
        if not sb_rows:
            cities = _PROVINCE_CITIES.get(region.rstrip("省"), ())
            if cities:
                sb_rows = (
                    db.query(SalaryBenchmark)
                    .filter(
                        SalaryBenchmark.experience_level == "entry",
                        SalaryBenchmark.city.in_(cities),
                    )
                    .order_by(SalaryBenchmark.year.desc())
                    .all()
                )
                if sb_rows:
                    short = "、".join(c.rstrip("市") for c in cities)
                    sb_scope = f"{region}（{short}等市样本）"
        sb_total = len(sb_rows)
        sample_rows = sb_rows[:SALARY_LIMIT]
    else:
        sb_total = 0
        sample_rows = []
    sb_parts: list[str] = []
    for row in sample_rows:
        sb_parts.append(f"{row.company}·{row.position} {row.salary_min}k-{row.salary_max}k")
        evidence.append(
            _evidence(
                f"岗位薪资 · {row.company} {row.position}",
                f"{row.salary_min}k-{row.salary_max}k（中位 {row.salary_median}k，{row.year}）",
                url=None,
                note=f"来源：{row.source}（无链接）",
            )
        )
    if sb_parts:
        coverage_parts.append(
            f"{sb_scope or region or ''}应届岗位薪资样本 {sb_total} 条：\n"
            + "\n".join(f"- {s}" for s in sb_parts[:5])
        )

    # ---- schools：地区就业率/考研率（一次取回，count/均值/样本都在 Python 侧）----
    sc_query = db.query(School)
    if region:
        sc_query = sc_query.filter(School.province == region)
    if school_tier:
        sc_query = sc_query.filter(School.level == school_tier)
    sc_rows = sc_query.all()
    sc_total = len(sc_rows)
    emp_rates = [r.employment_rate for r in sc_rows if r.employment_rate is not None]
    grad_rates = [r.grad_school_rate for r in sc_rows if r.grad_school_rate is not None]
    emp_rate = sum(emp_rates) / len(emp_rates) if emp_rates else None
    grad_rate = sum(grad_rates) / len(grad_rates) if grad_rates else None
    if sc_total and (emp_rate is not None or grad_rate is not None):
        rate_parts = []
        if emp_rate is not None:
            rate_parts.append(f"就业率 {emp_rate:.1f}%")
        if grad_rate is not None:
            rate_parts.append(f"考研率 {grad_rate:.1f}%")
        coverage_parts.append(
            f"{region or '全国'}{school_tier or ''}层次院校平均" + "、".join(rate_parts)
        )
        for row in sc_rows[:SCHOOL_LIMIT]:
            evidence.append(
                _evidence(
                    f"院校参考 · {row.name}",
                    f"就业率 {row.employment_rate or '?'}% / 考研率 {row.grad_school_rate or '?'}%",
                    url=row.report_index_url,
                )
            )

    # ---- 汇总 ----
    if not coverage_parts:
        return _empty_path(
            "employment",
            "直接就业",
            "暂无该专业/地区的就业薪资数据（就业数据覆盖有限），可尝试宽泛专业关键词或清空地区。",
        )

    income_1y = md_salary[0] if md_salary else "暂无数据"
    return {
        "path_type": "employment",
        "target_role": "直接就业",
        "income_1y": income_1y,
        "income_3y": "暂无数据",
        "income_5y": "暂无数据",
        "risk_level": "medium",
        "risk_description": "应届生就业竞争激烈，岗位供需失衡；试用期淘汰与行业周期波动需留意。",
        "growth_score": _GROWTH_SCORE["employment"],
        "time_cost_months": _TIME_COST["employment"],
        "match_score": _coverage_score(md_total + sb_total + sc_total, 30),
        "match_description": f"依据现有数据覆盖度估算（命中 {md_total + sb_total + sc_total} 条记录），"
        f"{_NO_DATA}个人画像匹配数据。",
        "pros": coverage_parts[:4],
        "cons": [
            "就业薪资数据覆盖有限，仅供参考",
            "行业周期波动直接影响稳定性",
        ],
        "evidence": evidence,
    }


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------
def _empty_path(path_type: str, label: str, reason: str) -> dict[str, Any]:
    """空数据路径 — 诚实降级，不编造数字。"""
    return {
        "path_type": path_type,
        "target_role": label,
        "income_1y": _NO_DATA,
        "income_3y": _NO_DATA,
        "income_5y": _NO_DATA,
        "risk_level": "medium",
        "risk_description": reason,
        "growth_score": _GROWTH_SCORE.get(path_type, 5),
        "time_cost_months": _TIME_COST.get(path_type, 6),
        "match_score": 0,
        "match_description": reason,
        "pros": [],
        "cons": [],
        "evidence": [],
    }


def _evidence(
    label: str,
    value: str,
    url: str | None = None,
    sources: list | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """构造证据条目 — 每个数字尽量带 source_url 或 data_sources。"""
    if url:
        source_url = url
    elif sources:
        source_url = None
        note = note or f"来源：{'、'.join(str(s) for s in sources)}"
    else:
        source_url = None
    return {"label": label, "value": value, "source_url": source_url, "note": note}


def _format_line(avg_line, min_line, max_line) -> str:
    if avg_line is None:
        return "未公布"
    # 注意 min/max 可能为 None（部分记录无总分线），此时回退平均分
    if min_line is not None and max_line is not None and min_line != max_line:
        return f"{min_line:.0f}-{max_line:.0f} 分"
    return f"{avg_line:.0f} 分"


def _format_ratio(application: int, enrollment: int) -> str:
    if not enrollment:
        return "未知"
    return f"{application / enrollment:.1f}:1"


def _format_value(value: float, unit: str) -> str:
    if unit == "万元":
        return f"{value:.1f} 万元"
    if unit == "元":
        return f"{value:.0f} 元"
    return f"{value} {unit}"


def _coverage_score(hits: int, cap: int) -> int:
    """数据覆盖度评分 0-100 — 命中越多越接近满分（封顶 95）。"""
    if hits <= 0:
        return 0
    return min(95, 40 + int((hits / cap) * 55))


def _percentile(sorted_vals: list[float], q: float) -> float:
    """线性插值分位数（q ∈ [0,1]，vals 已升序）。模拟器 v2 复用（09-25 ponytail 收敛点）。"""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    idx = q * (n - 1)
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    w = idx - lo
    return sorted_vals[lo] * (1 - w) + sorted_vals[hi] * w


def _classify_level(est: int, line: float) -> str:
    """估分 vs 线档位（条件账本 preview 复用）。"""
    diff = est - line
    if diff >= _STEADY_DIFF:
        return "稳健"
    if diff <= -_STEADY_DIFF:
        return "冲刺"
    return "均衡"


def _classify_kaoyan_band(est: int, line: float) -> str:
    """考研冲/稳/保档位 — 阈值 ±_STEADY_DIFF。

    单一真源：统一由后端按预估分 vs 复试线口径判定，前端不再用另一套 ±15 自行推导，
    避免同一份报告前后端口径打架。标签用「稳/均衡/冲」与前端展示一致。
    """
    diff = est - line
    if diff >= _STEADY_DIFF:
        return "稳"
    if diff <= -_STEADY_DIFF:
        return "冲"
    return "均衡"


# ----------------------------------------------------------------------
# 考研院校级分析（决策飞轮第一圈）
# ----------------------------------------------------------------------
_BG_DISCRIMINATION_LABEL = {
    "none": "不卡第一学历",
    "light": "轻度卡第一学历",
    "moderate": "明显卡第一学历",
    "severe": "严重卡第一学历",
}
_FIRST_CHOICE_LABEL = {
    "yes": "保护一志愿",
    "partial": "部分保护一志愿",
    "no": "不保护一志愿",
}


def _load_intel_map(db: Session, universities: list[str]) -> dict[str, GradSchoolIntel]:
    """批量取回院校隐性情报（每校一行：真实行优先，AI 行次之，同为真实取最近更新）。

    替代院校循环里逐校查询的 N+1；排序语义与原逐校 first() 一致。
    """
    if not universities:
        return {}
    rows = (
        db.query(GradSchoolIntel)
        .options(
            load_only(
                GradSchoolIntel.school_name,
                GradSchoolIntel.background_discrimination,
                GradSchoolIntel.first_choice_protection,
                GradSchoolIntel.admission_ratio,
                GradSchoolIntel.is_ai_generated,
            )
        )
        .filter(GradSchoolIntel.school_name.in_(universities))
        .order_by(
            GradSchoolIntel.is_ai_generated.asc(),
            GradSchoolIntel.updated_at.desc(),
        )
        .all()
    )
    intel_map: dict[str, GradSchoolIntel] = {}
    for row in rows:
        intel_map.setdefault(row.school_name, row)
    return intel_map


def _school_intel_summary(intel: GradSchoolIntel | None) -> str | None:
    """院校隐性情报摘要文本（grad_school_intel）— 真实行优先，AI 生成行显式标注。"""
    if intel is None:
        return None
    parts: list[str] = []
    bg = _BG_DISCRIMINATION_LABEL.get(intel.background_discrimination or "")
    if bg:
        parts.append(bg)
    fcp = _FIRST_CHOICE_LABEL.get(intel.first_choice_protection or "")
    if fcp:
        parts.append(fcp)
    if intel.admission_ratio:
        parts.append(f"报录比约 {intel.admission_ratio}")
    if not parts:
        return None
    text = "；".join(parts)
    if intel.is_ai_generated:
        text = f"{text}（AI 生成情报，未经核实）"
    return text


def _build_school_analysis(
    db: Session, line_rows: list[GradScorelineRecord], est: int | None = None
) -> dict[str, Any] | None:
    """考研院校级分析 — 命中院校按复试线竞争档位分组 + 隐性情报 + 劝退卡。

    档位边界：院校最近年份复试线相对样本中位数 ±10 分为界线（偏高/中等/偏低），
    样本过少（<3 校）时全部标"中等"并用覆盖说明兜底。
    est（考研模考估分）非空时对"估分低于复试线 30+ 分"的院校出劝退卡。
    """
    if not line_rows:
        return None

    # 按院校取最近年份记录
    group: dict[str, GradScorelineRecord] = {}
    for row in line_rows:
        cur = group.get(row.university_name)
        if cur is None or row.year >= cur.year:
            group[row.university_name] = row

    intel_map = _load_intel_map(db, list(group.keys()))

    items: list[dict[str, Any]] = []
    lines = [r.total_score_line or 0 for r in group.values()]
    if len(lines) >= 3:
        median_line = sorted(lines)[len(lines) // 2]
        for uni, row in sorted(group.items(), key=lambda kv: (kv[1].total_score_line or 0, kv[0])):
            score = row.total_score_line
            if score is None:
                competition = "中等"
            elif score > median_line + _STEADY_DIFF:
                competition = "偏高"
            elif score < median_line - _STEADY_DIFF:
                competition = "偏低"
            else:
                competition = "中等"
            ratio = (
                _format_ratio(row.application_count, row.enrollment_count)
                if row.application_count and row.enrollment_count
                else None
            )
            items.append(
                {
                    "university_name": uni,
                    "major_name": row.major_name,
                    "degree_type": row.degree_type,
                    "year": row.year,
                    "score_line": score,
                    "ratio": ratio,
                    "competition": competition,
                    "kaoyan_band": (
                        _classify_kaoyan_band(est, score)
                        if est is not None and score is not None
                        else None
                    ),
                    "intel": _school_intel_summary(intel_map.get(uni)),
                    "source_url": (
                        (row.data_sources or [None])[0]
                        if isinstance(row.data_sources, list)
                        else None
                    ),
                }
            )
    else:
        # 样本过少：不强行分档，全部标中等避免误导
        for uni, row in sorted(group.items(), key=lambda kv: (kv[1].total_score_line or 0, kv[0])):
            ratio = (
                _format_ratio(row.application_count, row.enrollment_count)
                if row.application_count and row.enrollment_count
                else None
            )
            items.append(
                {
                    "university_name": uni,
                    "major_name": row.major_name,
                    "degree_type": row.degree_type,
                    "year": row.year,
                    "score_line": row.total_score_line,
                    "ratio": ratio,
                    "competition": "中等",
                    "kaoyan_band": (
                        _classify_kaoyan_band(est, row.total_score_line)
                        if est is not None and row.total_score_line is not None
                        else None
                    ),
                    "intel": _school_intel_summary(intel_map.get(uni)),
                    "source_url": (
                        (row.data_sources or [None])[0]
                        if isinstance(row.data_sources, list)
                        else None
                    ),
                }
            )

    # ---- 考研劝退卡：模考估分显著低于复试线的院校（诚实拒绝镜像）----
    avoid_schools: list[dict[str, Any]] = []
    if est is not None:
        for uni, row in sorted(group.items(), key=lambda kv: (kv[1].total_score_line or 0, kv[0])):
            score = row.total_score_line
            if score is None or est > score - _KAOYAN_DISCOURAGE_DIFF:
                continue
            # 替代建议：估分高于其复试线的院校，按复试线降序（越接近估分越值得冲）
            safe_alts = [
                f"{u}（复试线 {r.total_score_line:.0f} 分）"
                for u, r in group.items()
                if r.total_score_line is not None and est >= r.total_score_line and u != uni
            ]
            avoid_schools.append(
                {
                    "university_name": uni,
                    "major_name": row.major_name,
                    "verdict": "建议放弃",
                    "basis": (
                        f"{row.year} 年复试线 {score:.0f} 分，你的模考估分 {est} 分"
                        f"低 {score - est:.0f} 分（复试线仅为进入门槛，实际录取均分通常更高）"
                    ),
                    "confidence": "该院校为单年分数线数据；复试线不等于录取线，请结合招生人数判断",
                    "alternatives": safe_alts[:2],
                    "source_url": (
                        (row.data_sources or [None])[0]
                        if isinstance(row.data_sources, list)
                        else None
                    ),
                }
            )

    return {
        "matched_school_count": len(items),
        "coverage_note": (
            f"命中 {len(items)} 所院校（基于现有复试线数据；数据覆盖有限，未覆盖院校不在此列，"
            "竞争档位仅供参考）"
        ),
        "items": items[:8],
        "avoid_schools": avoid_schools[:5],
    }


# ----------------------------------------------------------------------
# 综合建议
# ----------------------------------------------------------------------
def _personal_condition_line(conditions: dict[str, Any]) -> str | None:
    """个人条件摘要行（无任何个人条件时返回 None）。"""
    parts = []
    if conditions.get("fresh_status"):
        parts.append(conditions["fresh_status"])
    if conditions.get("education"):
        parts.append(f"{conditions['education']}学历")
    if conditions.get("party_status"):
        parts.append(conditions["party_status"])
    if conditions.get("gender"):
        parts.append(conditions["gender"])
    if conditions.get("has_grassroots") is True:
        parts.append("有基层经历")
    if not parts and conditions.get("kaoyan_estimated_score") is None:
        return None
    cond_text = "、".join(parts) if parts else "档案条件"
    est_text = (
        f"，预估考研初试 {conditions['kaoyan_estimated_score']} 分"
        if conditions.get("kaoyan_estimated_score")
        else ""
    )
    return f"以你的条件（{cond_text}{est_text}）为准，考研难度与就业匹配已按此个性化评估。"


def _build_recommendation(
    metrics: list[dict[str, Any]], input_summary: dict, conditions: dict[str, Any] | None = None
) -> str:
    """两路对比后的条件式建议 — 纯规则，不替用户决定。"""
    conditions = conditions or {}
    lines: list[str] = []
    personal_line = _personal_condition_line(conditions)
    if personal_line:
        lines.append(personal_line)
        lines.append("")
    lines.append(
        f"针对「{input_summary['major']} · {input_summary['region']} · "
        f"{input_summary['school_tier']} · {input_summary['graduation_year']} 届」的两路对比："
    )
    for m in metrics:
        if m["match_score"] <= 0:
            lines.append(f"- {PATH_LABELS[m['path_type']]}：{m['risk_description']}")
            continue
        if m["path_type"] == "kaoyan":
            lines.append(
                f"- 考研：{m['pros'][0] if m['pros'] else '数据有限'}，难度评估 {m['risk_level']}。"
            )
        else:
            lines.append(
                f"- 就业：{m['pros'][0] if m['pros'] else '薪资数据有限'}，行业波动需留意。"
            )

    lines.append("")
    lines.append(
        "每个数字都可在卡片中展开查看来源。建议结合你的财务缓冲、家庭支持与个人偏好，"
        "从两路中选 1 条做深度分析，并在「决策实验室」中进一步权衡。"
    )
    return "\n".join(lines)
