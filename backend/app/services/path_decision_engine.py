"""三路对比决策引擎 — 用真实数据聚合考研/考公/就业三条路。

设计目标（与「决策引擎」方向一致）：
- 不依赖 LLM：纯规则聚合，未配置 LLM 也不会 503。
- 每个数字都来自现有数据库，可溯源（source_url / data_sources）。
- 没有数据的指标诚实降级为占位文本，绝不编造。

数据来源：
- 考研路：grad_scoreline_records（复试分数线/报录情况）+ grad_yanzhao_programs（招生目录）
- 考公路：gwy_position（国考职位表）+ gwy_province_position（省考职位表）+ gwy_score_line（进面分）
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
from app.models.gwy_position import GwyPosition
from app.models.gwy_province_position import GwyProvincePosition
from app.models.gwy_score_line import GwyScoreLine
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
GWY_POSITION_LIMIT = 10
MARKET_LIMIT = 8
SALARY_LIMIT = 8
SCHOOL_LIMIT = 5

# 主观评分（无法从数据溯源的部分，明确标注为行业公开认知的固定评估）
_TIME_COST = {"kaoyan": 12, "civil_service": 9, "employment": 3}
_GROWTH_SCORE = {"kaoyan": 7, "civil_service": 4, "employment": 6}

# 路径中文标签（与前端 PATH_PRESETS 对齐）
PATH_LABELS = {
    "kaoyan": "考研深造",
    "civil_service": "考公",
    "employment": "直接就业",
}

# 空数据占位（诚实降级）
_NO_DATA = "暂无相关数据"

# ----------------------------------------------------------------------
# 个人条件可报边界（决策飞轮第一圈）
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
# 与考公劝退阈值取同一纪律：宁可少劝，不可错劝。
_KAOYAN_DISCOURAGE_DIFF = 30
# 进面线数据的单年声明（当前 gwy_score_line 仅 2026 一个批次）
_SCORE_YEAR_NOTE = "进面线数据目前仅覆盖单个批次，无历史趋势可校验，请结合自身模考波动判断"

# analyze 结果缓存：同输入（专业/地区/条件包）直接复用，TTL 10 分钟（数据每日更新）
_DECISION_CACHE_TTL = 600


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
    """生成三路对比结果。

    Args:
        db: 数据库会话
        major: 专业关键词（如「计算机」）
        region: 地区（如「广东」；考公路限定省份，就业路限定城市/省份）
        school_tier: 学校层次（985/211/双一流/普通；用于考研难度与就业参考）
        graduation_year: 毕业年份（默认 2026，考公按应届筛选参考）
        fresh_status / party_status / education / has_grassroots / gender:
            个人条件包（keyword-only，全部默认 None → 与旧行为完全兼容）：
            参与考公可报边界过滤与岗位分级，均为可选。
        estimated_score: 行测+申论预估总分（200 分制），用于岗位竞争力分级。

    Returns:
        {
            "metrics": [3 条 PathMetrics 兼容 dict（含 evidence）, ...],
            "recommendation": 条件式综合建议文本,
            "input": {major, region, school_tier, graduation_year, ...个人条件},
            "position_analysis": 考公岗位级分析（可报数/进面线分布/个人分级）| None,
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
    civil, position_analysis = _build_civil_service_path(db, major, region, year, conditions)
    employment = _build_employment_path(db, major, region, school_tier)

    metrics = [kaoyan, civil, employment]
    recommendation = _build_recommendation(metrics, input_summary, conditions)

    decision = {
        "metrics": metrics,
        "recommendation": recommendation,
        "input": input_summary,
        "position_analysis": position_analysis,
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
# 考公路
# ----------------------------------------------------------------------
def _build_civil_service_path(
    db: Session, major: str, region: str | None, year: int, conditions: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """考公路 — 返回 (路径卡 dict, 岗位级分析 dict|None)。

    岗位级分析基于个人条件做可报边界过滤（政治面貌/学历/应届/性别/基层经历），
    关联进面线给出分布与个人竞争力分级；一切以真实字段为准，无法判定的保守放行。
    """
    pattern = f"%{escape_like(major)}%"
    evidence: list[dict[str, Any]] = []

    # ---- 国考：专业 + 工作地点（一次取回全部命中行，count/求和/证据/岗位分析都在 Python 侧）----
    gwy_query = db.query(GwyPosition).options(
        load_only(
            GwyPosition.position_code,
            GwyPosition.dept_name,
            GwyPosition.bureau,
            GwyPosition.position_name,
            GwyPosition.position_distribution,
            GwyPosition.work_location,
            GwyPosition.recruit_count,
            GwyPosition.source_url,
            GwyPosition.remarks,
            GwyPosition.political_status,
            GwyPosition.education_req,
            GwyPosition.grassroots_exp_req,
        )
    )
    gwy_query = gwy_query.filter(
        GwyPosition.year == year,
        GwyPosition.major_req.ilike(pattern, escape="\\"),
    )
    if region:
        gwy_query = gwy_query.filter(
            GwyPosition.work_location.like(f"%{escape_like(region)}%", escape="\\")
        )
    gwy_rows = gwy_query.all()
    gwy_total = len(gwy_rows)
    gwy_recruit = sum(r.recruit_count or 0 for r in gwy_rows)
    gwy_recruit_text = f"招录合计 {int(gwy_recruit)} 人" if gwy_recruit else "招录人数未公布"

    # 进面分：按 position_code 关联 gwy_score_line（一次取回，均值与岗位分析共用）
    codes = [r.position_code for r in gwy_rows if r.position_code]
    score_line_rows = _load_score_lines(db, year, codes)
    avg_min_score = _avg_min_score(score_line_rows)

    # 国考证据
    for row in gwy_rows[:GWY_POSITION_LIMIT]:
        ev = _evidence(
            f"国考岗位 · {row.dept_name or row.bureau or '部门'}",
            f"{row.position_name}（{row.position_distribution or row.work_location or '地点未公布'}），"
            f"招 {row.recruit_count or '?'} 人",
            url=row.source_url,
        )
        if ev not in evidence:
            evidence.append(ev)

    # ---- 省考：专业（本科要求）+ 省份（同样一次取回）----
    province_scope = region  # 省考按省份限定（如「广东」）
    p_query = db.query(GwyProvincePosition).options(
        load_only(
            GwyProvincePosition.position_code,
            GwyProvincePosition.dept_name,
            GwyProvincePosition.position_name,
            GwyProvincePosition.exam_region,
            GwyProvincePosition.province,
            GwyProvincePosition.recruit_count,
            GwyProvincePosition.source_url,
            GwyProvincePosition.education_req,
            GwyProvincePosition.fresh_grad_only,
            GwyProvincePosition.grassroots_exp_req,
        )
    )
    p_query = p_query.filter(
        GwyProvincePosition.year == year,
        or_(
            GwyProvincePosition.major_req_undergrad.ilike(pattern, escape="\\"),
            GwyProvincePosition.major_req_grad.ilike(pattern, escape="\\"),
        ),
    )
    if province_scope:
        p_query = p_query.filter(GwyProvincePosition.province == province_scope)
    p_rows = p_query.all()
    p_total = len(p_rows)
    p_recruit = sum(r.recruit_count or 0 for r in p_rows)
    p_recruit_text = f"招录合计 {int(p_recruit)} 人" if p_recruit else "招录人数未公布"

    for row in p_rows[:GWY_POSITION_LIMIT]:
        ev = _evidence(
            f"省考岗位 · {row.dept_name or '部门'}",
            f"{row.position_name}（{row.exam_region or row.province}），招 {row.recruit_count or '?'} 人",
            url=row.source_url,
        )
        if ev not in evidence:
            evidence.append(ev)

    # ---- 汇总 ----
    if gwy_total == 0 and p_total == 0:
        return (
            _empty_path(
                "civil_service",
                "考公",
                "该专业暂无国考/省考可报岗位数据，可尝试更宽泛的专业关键词或清空地区。",
            ),
            None,
        )

    region_text = f"{region} " if region else ""
    risk_desc = "国考整体录取率约 1-3%，省考约 3-5%；岗位分配与专业限制不确定性高。"
    if region:
        risk_desc += f"（仅覆盖 {region} 的省考数据）"

    coverage_parts = [
        f"{region_text}国考可报岗位 {gwy_total} 个（{gwy_recruit_text}）",
        f"{region_text}省考可报岗位 {p_total} 个（{p_recruit_text}）",
    ]
    if avg_min_score:
        coverage_parts.append(f"国考平均进面最低分约 {avg_min_score:.1f} 分")

    # ---- 岗位级分析（个人可报边界 + 进面线分布 + 竞争力分级）----
    position_analysis = _build_position_analysis(
        gwy_rows, p_rows, year, conditions, score_line_rows
    )

    return (
        {
            "path_type": "civil_service",
            "target_role": "考公",
            "income_1y": "暂无数据",
            "income_3y": "暂无数据",
            "income_5y": "暂无数据",
            "risk_level": "high",
            "risk_description": risk_desc,
            "growth_score": _GROWTH_SCORE["civil_service"],
            "time_cost_months": _TIME_COST["civil_service"],
            "match_score": _coverage_score(gwy_total + p_total, 30),
            "match_description": f"依据现有数据覆盖度估算（命中 {gwy_total + p_total} 个岗位），"
            f"{_NO_DATA}个人画像匹配数据。",
            "pros": [
                " · ".join(coverage_parts),
                "体制内稳定，福利保障完善",
            ],
            "cons": [
                "薪资增长缓慢，晋升论资排辈",
                "岗位分配不确定，调动困难",
            ],
            "evidence": evidence,
        },
        position_analysis,
    )


# ----------------------------------------------------------------------
# 就业路
# ----------------------------------------------------------------------
def _build_employment_path(
    db: Session, major: str, region: str | None, school_tier: str | None
) -> dict[str, Any]:
    """就业路 — 数据覆盖有限（employment_data 为空表），以 market_data + salary_benchmarks + schools 兜底。"""
    evidence: list[dict[str, Any]] = []
    coverage_parts: list[str] = []

    # ---- market_data：行业薪资带（宏观，带 source_url）----
    # 行业宏观数据多为全国口径：优先匹配地区，无命中则回退全国（诚实标注口径）。
    # market_data 全表千余行，一次取回命中行在 Python 侧计数/排序（原 count+取数两查）。
    md_base = db.query(MarketData).filter(
        MarketData.industry.ilike(f"%{escape_like(major)}%", escape="\\")
    )
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
                .filter(MarketData.industry.ilike(f"%{escape_like(major)}%", escape="\\"))
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
    if region:
        # 未指定地区时不展示岗位薪资样本（城市粒度才有意义）
        sb_rows = (
            db.query(SalaryBenchmark)
            .filter(
                SalaryBenchmark.experience_level == "entry",
                SalaryBenchmark.city.like(f"%{escape_like(region)}%", escape="\\"),
            )
            .order_by(SalaryBenchmark.year.desc())
            .all()
        )
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
            f"{region or ''}应届岗位薪资样本 {sb_total} 条：\n"
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


# ----------------------------------------------------------------------
# 个人条件可报边界（决策飞轮第一圈）
# ----------------------------------------------------------------------
def _is_fresh_limited(remarks: str | None) -> bool:
    """remarks 是否限定应届 — 规则保守：明确出现限定词才认定（含"非应届"视为不限）。"""
    if not remarks or "非应届" in remarks:
        return False
    return any(m in remarks for m in _FRESH_MARKERS)


def _is_gender_limited(remarks: str | None, only: str) -> bool:
    """remarks 是否限定某性别（如"限男性"）；未明确出现限定词视为不限。"""
    if not remarks:
        return False
    return ("限" + only) in remarks or ("仅限" + only) in remarks


def _party_eligible(political_status: str | None, user_party: str) -> bool:
    """政治面貌匹配：不限岗全放行；党员岗仅党员；党/团员岗放行党员与团员。"""
    if not political_status or political_status == "不限":
        return True
    if "共青团员" in political_status or "团员" in political_status:
        return user_party in ("中共党员", "党员或团员")
    if "中共党员" in political_status or "党员" in political_status:
        return user_party == "中共党员"
    return True


def _edu_eligible(education_req: str | None, user_edu: str) -> bool:
    """学历档位匹配 — "仅限X"需精确档位；"及以上/或"等开放表述满足最低档即可。

    未知学历表述视为不限（保守放行，避免误伤）。
    """
    if not education_req or not user_edu:
        return True
    levels = [l for l in ("博士", "硕士", "本科", "大专") if l in education_req]
    if not levels:
        return True
    user_rank = _EDU_RANK[user_edu]
    if "仅限" in education_req:
        return user_rank == _EDU_RANK[levels[0]]
    return user_rank >= min(_EDU_RANK[l] for l in levels)


def _province_fresh_limited(raw: str | None) -> bool:
    """省考 fresh_grad_only 官方字段：'否'/空 → 不限应届；其余（'是'/应届毕业生等）→ 限应届。"""
    if not raw or "否" in raw:
        return False
    return True


def _position_eligible_blockers(row: Any, conditions: dict[str, Any]) -> list[dict]:
    """国考岗位可报边界 — 返回不满足的资格维度 [{key,label,reason}]；空列表=可报。

    与 _position_eligible 判定完全一致（同一套规则、单一实现），供免登录预览复用。
    无个人条件的维度自动放行（不参与判定）。
    """
    blockers: list[dict] = []
    if conditions.get("fresh_status") == "非应届" and _is_fresh_limited(row.remarks):
        blockers.append(
            {"key": "fresh_grad", "label": "应届生要求", "reason": "该职位限应届毕业生报考"}
        )
    if conditions.get("gender") == "男" and _is_gender_limited(row.remarks, "女"):
        blockers.append({"key": "gender", "label": "性别要求", "reason": "该职位限女性报考"})
    if conditions.get("gender") == "女" and _is_gender_limited(row.remarks, "男"):
        blockers.append({"key": "gender", "label": "性别要求", "reason": "该职位限男性报考"})
    if conditions.get("party_status") and not _party_eligible(
        row.political_status, conditions["party_status"]
    ):
        blockers.append(
            {
                "key": "party_status",
                "label": "政治面貌要求",
                "reason": f"该职位要求「{row.political_status}」，与你的政治面貌"
                f"（{conditions['party_status']}）不符",
            }
        )
    if conditions.get("education") and not _edu_eligible(
        row.education_req, conditions["education"]
    ):
        blockers.append(
            {
                "key": "education",
                "label": "学历要求",
                "reason": f"该职位学历要求「{row.education_req}」，与你的学历"
                f"（{conditions['education']}）不符",
            }
        )
    if conditions.get("has_grassroots") is False and (
        row.grassroots_exp_req not in (None, "", "无限制")
    ):
        blockers.append(
            {
                "key": "grassroots",
                "label": "基层工作经历",
                "reason": f"该职位要求基层工作经历（{row.grassroots_exp_req}），你不满足",
            }
        )
    return blockers


def _position_eligible(row: Any, conditions: dict[str, Any]) -> bool:
    """国考岗位可报边界判断（无个人条件的维度自动放行）。"""
    return not _position_eligible_blockers(row, conditions)


def _province_position_eligible_blockers(row: Any, conditions: dict[str, Any]) -> list[dict]:
    """省考岗位可报边界 — 返回不满足维度；空列表=可报（官方结构化字段，不做文本解析）。"""
    blockers: list[dict] = []
    if conditions.get("fresh_status") == "非应届" and _province_fresh_limited(row.fresh_grad_only):
        blockers.append(
            {
                "key": "fresh_grad",
                "label": "应届生要求",
                "reason": f"该职位仅限应届毕业生（{row.fresh_grad_only}）",
            }
        )
    if conditions.get("education") and not _edu_eligible(
        row.education_req, conditions["education"]
    ):
        blockers.append(
            {
                "key": "education",
                "label": "学历要求",
                "reason": f"该职位学历要求「{row.education_req}」，与你的学历"
                f"（{conditions['education']}）不符",
            }
        )
    if conditions.get("has_grassroots") is False and row.grassroots_exp_req == "是":
        blockers.append(
            {
                "key": "grassroots",
                "label": "基层工作经历",
                "reason": "该职位要求基层工作经历，你不满足",
            }
        )
    return blockers


def _province_position_eligible(row: Any, conditions: dict[str, Any]) -> bool:
    """省考岗位可报边界判断（用官方结构化字段，不做文本解析）。"""
    return not _province_position_eligible_blockers(row, conditions)


def _applied_conditions_text(conditions: dict[str, Any]) -> str:
    """已应用的可报边界过滤描述（用于 analysis.notes）。"""
    parts = []
    if conditions.get("fresh_status"):
        parts.append(f"应届/非应届（{conditions['fresh_status']}）")
    if conditions.get("party_status"):
        parts.append(f"政治面貌（{conditions['party_status']}）")
    if conditions.get("education"):
        parts.append(f"学历（{conditions['education']}）")
    if conditions.get("has_grassroots") is True:
        parts.append("基层经历（有）")
    elif conditions.get("has_grassroots") is False:
        parts.append("基层经历（无）")
    if conditions.get("gender"):
        parts.append(f"性别（{conditions['gender']}）")
    return "、".join(parts)


def _percentile(sorted_vals: list[float], q: float) -> float:
    """线性插值分位数（q ∈ [0,1]，vals 已升序）。"""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    idx = q * (n - 1)
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    w = idx - lo
    return sorted_vals[lo] * (1 - w) + sorted_vals[hi] * w


def _classify_level(est: int, line: float) -> str:
    diff = est - line
    if diff >= _STEADY_DIFF:
        return "稳健"
    if diff <= -_STEADY_DIFF:
        return "冲刺"
    return "均衡"


def _alternatives_for(
    target_row: Any,
    by_code: dict[str, Any],
    score_map: dict[str, float],
    est: int,
    max_n: int = 2,
) -> list[str]:
    """为劝退岗位找替代出口：同部门（bureau/dept_name）中估分高于进面线的岗位。

    按安全余量降序取前 max_n 个；同部门无合格岗位则回退到全量稳健档
    （最多同样数量）。找不到就返回空列表——绝不编造替代。
    """
    scored = [
        (row, score_map[code])
        for code, row in by_code.items()
        if code in score_map and row is not target_row
    ]
    safe = [(r, s) for r, s in scored if est - s > 0]
    same_dept = [
        (r, s)
        for r, s in safe
        if (r.bureau and r.bureau == target_row.bureau)
        or (r.dept_name and r.dept_name == target_row.dept_name)
    ]
    pool = same_dept or safe
    pool.sort(key=lambda pair: pair[1])  # 进面线低 = 余量大 = 更稳
    alts = []
    for r, s in pool[:max_n]:
        alts.append(
            f"{r.dept_name or r.bureau or '部门未公布'}·{r.position_name or '职位未公布'}"
            f"（进面 {s:.0f} 分，你高 {est - s:.0f} 分）"
        )
    return alts


def _load_score_lines(db: Session, year: int, codes: list[str]) -> list[Any]:
    """一次取回指定职位代码的进面线（供均值聚合与岗位级分析共用，替代两次独立查询）。"""
    if not codes:
        return []
    return (
        db.query(GwyScoreLine)
        .options(
            load_only(
                GwyScoreLine.position_code,
                GwyScoreLine.min_score,
                GwyScoreLine.batch,
            )
        )
        .filter(GwyScoreLine.year == year, GwyScoreLine.position_code.in_(codes))
        .order_by(GwyScoreLine.batch == "首批")
        .all()
    )


def _avg_min_score(score_line_rows: list[Any]) -> float | None:
    """进面线均值（与 SQL AVG 一致：忽略 NULL；无行返回 None）。"""
    scores = [line.min_score for line in score_line_rows if line.min_score is not None]
    if not scores:
        return None
    return sum(scores) / len(scores)


def _build_position_analysis(
    gwy_rows: list[Any],
    province_rows: list[Any],
    year: int,
    conditions: dict[str, Any],
    score_line_rows: list[Any],
) -> dict[str, Any] | None:
    """考公岗位级分析 — 个人可报清单（按 position_code 去重）+ 进面线分层。

    应届/性别限定来自职位备注文本解析，无法判定的视为可报并在 notes 标注；
    所有数字均来自职位表/进面线真实字段。
    """
    eligible_rows = [r for r in gwy_rows if _position_eligible(r, conditions)]
    # 同一 position_code 对应多条专业/学历记录，去重后才是真实岗位数
    by_code: dict[str, Any] = {}
    for r in eligible_rows:
        if r.position_code and r.position_code not in by_code:
            by_code[r.position_code] = r
    eligible_count = len(by_code)

    p_eligible = [r for r in province_rows if _province_position_eligible(r, conditions)]
    p_by_code: dict[str, Any] = {}
    for r in p_eligible:
        if r.position_code and r.position_code not in p_by_code:
            p_by_code[r.position_code] = r
    province_count = len(p_by_code)

    if eligible_count == 0 and province_count == 0:
        return {
            "eligible_count": 0,
            "province_count": 0,
            "score_band": "无可报岗位数据",
            "personalized_level": None,
            "tier_summary": None,
            "top_positions": [],
            "notes": [
                f"已按个人条件过滤：{_applied_conditions_text(conditions) or '未应用'}；"
                "无符合全部条件的岗位。"
            ],
        }

    # ---- 进面线：按 position_code 关联，同 code 多批次取第一条（首批优先）----
    # score_line_rows 由调用方一次取回（覆盖全部命中岗位），这里只筛可报岗位的 code
    score_map: dict[str, float] = {}
    for line in score_line_rows:
        if line.min_score and line.position_code in by_code and line.position_code not in score_map:
            score_map[line.position_code] = line.min_score

    scores = sorted(score_map.values())
    has_score = len(scores) > 0

    # ---- 分数带（P25/P50/P75）----
    score_band = "本数据集中暂无进面线公布（面试名单未收录）"
    scored_ratio_text = f"{len(scores)}/{eligible_count} 岗已公布" if has_score else ""
    if has_score:
        p25, p50, p75 = (
            _percentile(scores, 0.25),
            _percentile(scores, 0.5),
            _percentile(scores, 0.75),
        )
        score_band = (
            f"进面线集中 {p25:.0f}–{p75:.0f} 分（中位 {p50:.0f}，公布 {scored_ratio_text}）"
        )

    # ---- 个人竞争力分级（仅国考有进面线的岗位）----
    personalized_level: str | None = None
    tier_summary: str | None = None
    avoid_positions: list[dict[str, Any]] = []
    discouraged_count = 0
    est = conditions.get("estimated_score")
    if est is not None and has_score:
        tier_counts: dict[str, int] = {"稳健": 0, "均衡": 0, "冲刺": 0}
        for line_score in scores:
            tier_counts[_classify_level(est, line_score)] += 1
        personalized_level = max(tier_counts, key=tier_counts.get)
        tier_summary = (
            f"按预估 {est} 分对比岗位进面线：稳健 {tier_counts['稳健']} 岗 · "
            f"均衡 {tier_counts['均衡']} 岗 · 冲刺 {tier_counts['冲刺']} 岗（仅统计已公布线岗位）"
        )

        # ---- 劝退卡：估分低于进面线 20+ 分的岗位，诚实拒绝 + 替代出口 ----
        discouraged = sorted(
            ((code, row, score_map[code]) for code, row in by_code.items() if code in score_map),
            key=lambda t: est - t[2],  # 估分差越小越绝望，排最前
        )
        p50 = _percentile(scores, 0.5)
        for code, row, line_score in discouraged:
            if est - line_score > -_DISCOURAGE_DIFF:
                break
            discouraged_count += 1
            if len(avoid_positions) < 5:
                avoid_positions.append(
                    {
                        "dept_name": row.dept_name or row.bureau or "部门未公布",
                        "position_name": row.position_name or "职位未公布",
                        "verdict": "建议放弃",
                        "basis": (
                            f"{year} 年此岗进面最低分 {line_score:.0f} 分，你的预估 {est} 分"
                            f"低 {line_score - est:.0f} 分；同类可报岗位进面线中位 {p50:.0f} 分"
                        ),
                        "confidence": f"仅 {year} 年单批数据，{_SCORE_YEAR_NOTE}",
                        "alternatives": _alternatives_for(row, by_code, score_map, est),
                        "source_url": row.source_url,
                    }
                )
        if discouraged_count:
            tier_summary += f"；其中 {discouraged_count} 岗进面希望渺茫（详见劝退分析）"
    elif est is not None:
        tier_summary = f"按预估 {est} 分：暂无已公布进面线可供分级（公布 {scored_ratio_text}）"

    # ---- 示例岗位（招录人数优先，≤5 个；带进面线与分级标签）----
    top_positions: list[dict[str, Any]] = []
    for r in sorted(
        by_code.values(), key=lambda x: (x.recruit_count or 0, x.position_code or ""), reverse=True
    )[:5]:
        line_score = score_map.get(r.position_code)
        label = "进面线未收录"
        if line_score:
            if est is not None:
                diff = est - line_score
                if diff <= -_DISCOURAGE_DIFF:
                    level = "建议放弃"
                else:
                    level = _classify_level(est, line_score)
                label = f"进面 {line_score:.0f} 分 · 你{'高' if diff >= 0 else '低'}{abs(diff):.0f} 分（{level}）"
            else:
                label = f"进面 {line_score:.0f} 分"
        top_positions.append(
            {
                "dept_name": r.dept_name or r.bureau or "部门未公布",
                "position_name": r.position_name or "职位未公布",
                "work_location": r.work_location,
                "recruit_count": r.recruit_count,
                "min_score": line_score,
                "score_label": label,
                "source_url": r.source_url,
            }
        )

    # ---- 数据诚实标注 ----
    notes: list[str] = []
    applied = _applied_conditions_text(conditions)
    if applied:
        notes.append(f"已按个人条件过滤：{applied}")
    is_text_parsed = bool(conditions.get("fresh_status")) or bool(conditions.get("gender"))
    if is_text_parsed:
        notes.append("应届/性别限定来自职位备注文本解析，个别岗位可能有偏差")
    if province_count > 0:
        notes.append("省考岗位无进面线数据，仅统计可报数")
    if has_score:
        notes.append(f"进面线口径：{_SCORE_YEAR_NOTE}")

    return {
        "eligible_count": eligible_count,
        "province_count": province_count,
        "score_band": score_band,
        "personalized_level": personalized_level,
        "tier_summary": tier_summary,
        "top_positions": top_positions,
        "avoid_positions": avoid_positions,
        "discouraged_count": discouraged_count,
        "notes": notes,
    }


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
    """个人条件摘要行（无任何个人条件时返回 None，输出与旧版逐字一致）。"""
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
    if not parts and conditions.get("estimated_score") is None:
        return None
    cond_text = "、".join(parts) if parts else "档案条件"
    est_text = (
        f"，预估行测+申论 {conditions['estimated_score']} 分"
        if conditions.get("estimated_score")
        else ""
    )
    return f"以你的条件（{cond_text}{est_text}）为准，考公可报岗位已按可报边界过滤（详见考公卡片下「岗位分析」）。"


def _build_recommendation(
    metrics: list[dict[str, Any]], input_summary: dict, conditions: dict[str, Any] | None = None
) -> str:
    """三路对比后的条件式建议 — 纯规则，不替用户决定。"""
    conditions = conditions or {}
    lines: list[str] = []
    personal_line = _personal_condition_line(conditions)
    if personal_line:
        lines.append(personal_line)
        lines.append("")
    lines.append(
        f"针对「{input_summary['major']} · {input_summary['region']} · "
        f"{input_summary['school_tier']} · {input_summary['graduation_year']} 届」的三路对比："
    )
    for m in metrics:
        if m["match_score"] <= 0:
            lines.append(f"- {PATH_LABELS[m['path_type']]}：{m['risk_description']}")
            continue
        if m["path_type"] == "kaoyan":
            lines.append(
                f"- 考研：{m['pros'][0] if m['pros'] else '数据有限'}，难度评估 {m['risk_level']}。"
            )
        elif m["path_type"] == "civil_service":
            lines.append(
                f"- 考公：{m['pros'][0] if m['pros'] else '岗位数据有限'}，"
                f"竞争激烈，岗位明细见卡片。"
            )
        else:
            lines.append(
                f"- 就业：{m['pros'][0] if m['pros'] else '薪资数据有限'}，行业波动需留意。"
            )

    lines.append("")
    lines.append(
        "每个数字都可在卡片中展开查看来源。建议结合你的财务缓冲、家庭支持与个人偏好，"
        "从三路中选 1-2 条做深度分析，并在「决策实验室」中进一步权衡。"
    )
    return "\n".join(lines)
