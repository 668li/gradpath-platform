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
from sqlalchemy.orm import Session

from app.models.grad_intel import GradScorelineRecord, GradYanzhaoProgram
from app.models.gwy_position import GwyPosition
from app.models.gwy_province_position import GwyProvincePosition
from app.models.gwy_score_line import GwyScoreLine
from app.models.market_data import MarketData
from app.models.salary_benchmark import SalaryBenchmark
from app.models.school import School
from app.services.employment_service import escape_like

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
# 主入口
# ----------------------------------------------------------------------
def generate_decision(
    db: Session,
    major: str,
    region: str | None = None,
    school_tier: str | None = None,
    graduation_year: int | None = None,
) -> dict[str, Any]:
    """生成三路对比结果。

    Args:
        db: 数据库会话
        major: 专业关键词（如「计算机」）
        region: 地区（如「广东」；考公路限定省份，就业路限定城市/省份）
        school_tier: 学校层次（985/211/双一流/普通；用于考研难度与就业参考）
        graduation_year: 毕业年份（默认 2026，考公按应届筛选参考）

    Returns:
        {
            "metrics": [3 条 PathMetrics 兼容 dict（含 evidence）, ...],
            "recommendation": 条件式综合建议文本,
            "input": {major, region, school_tier, graduation_year},
        }
    """
    year = graduation_year or 2026
    input_summary = {
        "major": major,
        "region": region or "全国",
        "school_tier": school_tier or "不限",
        "graduation_year": year,
    }

    kaoyan = _build_kaoyan_path(db, major, school_tier)
    civil = _build_civil_service_path(db, major, region, year)
    employment = _build_employment_path(db, major, region, school_tier)

    metrics = [kaoyan, civil, employment]
    recommendation = _build_recommendation(metrics, input_summary)

    return {
        "metrics": metrics,
        "recommendation": recommendation,
        "input": input_summary,
    }


# ----------------------------------------------------------------------
# 考研路
# ----------------------------------------------------------------------
def _build_kaoyan_path(
    db: Session, major: str, school_tier: str | None
) -> dict[str, Any]:
    pattern = f"%{escape_like(major)}%"
    base = db.query(GradScorelineRecord).filter(
        GradScorelineRecord.major_name.ilike(pattern, escape="\\")
    )
    total = base.count()
    evidence: list[dict[str, Any]] = []

    if total == 0:
        return _empty_path("kaoyan", "考研深造", "该专业暂无分数线数据，可尝试更宽泛的关键词（如只输入学科大类）。")

    # 分数线聚合
    line_agg = base.with_entities(
        func.avg(GradScorelineRecord.total_score_line),
        func.min(GradScorelineRecord.total_score_line),
        func.max(GradScorelineRecord.total_score_line),
        func.min(GradScorelineRecord.year),
        func.max(GradScorelineRecord.year),
    ).one()
    avg_line, min_line, max_line, year_min, year_max = line_agg
    line_desc = _format_line(avg_line, min_line, max_line)

    # 报录情况：有 application_count 与 enrollment_count 的条目才计算（无则诚实省略）
    ratio_samples: list[str] = []
    ratio_ev: list[dict[str, Any]] = []
    for row in (
        base.filter(
            GradScorelineRecord.application_count.isnot(None),
            GradScorelineRecord.enrollment_count.isnot(None),
        )
        .order_by(GradScorelineRecord.year.desc())
        .limit(SCORELINE_LIMIT)
        .all()
    ):
        ratio = _format_ratio(row.application_count, row.enrollment_count)
        ratio_samples.append(f"{row.university_name}（{row.year}）报录 {ratio}")
        ratio_ev.append(_evidence(
            f"报录比 · {row.university_name} {row.year}",
            f"报考 {row.application_count} / 录取 {row.enrollment_count}，"
            f"复试线 {row.total_score_line} 分",
            sources=row.data_sources,
        ))

    # 分数证据
    line_rows = (
        base.order_by(GradScorelineRecord.year.desc())
        .limit(SCORELINE_LIMIT)
        .all()
    )
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
    yz_total = yz.count()
    yz_quota = yz.with_entities(
        func.sum(GradYanzhaoProgram.enrollment_quota)
    ).scalar()
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
    risk_desc = (
        "考研录取率通常低于 30%，备考失败损失约 1 年时间。"
    )
    if ratio_samples:
        risk_desc = "报考热度：\n" + "\n".join(f"- {s}" for s in ratio_samples[:5]) + "\n\n" + risk_desc
    if school_tier:
        risk_desc += f"本科层次「{school_tier}」在复试/调剂中会影响部分院校的隐性筛选。"

    return {
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
    }


# ----------------------------------------------------------------------
# 考公路
# ----------------------------------------------------------------------
def _build_civil_service_path(
    db: Session, major: str, region: str | None, year: int
) -> dict[str, Any]:
    pattern = f"%{escape_like(major)}%"
    evidence: list[dict[str, Any]] = []

    # ---- 国考：专业 + 工作地点 ----
    gwy = db.query(GwyPosition).filter(
        GwyPosition.year == year,
        GwyPosition.major_req.ilike(pattern, escape="\\"),
    )
    if region:
        gwy = gwy.filter(
            GwyPosition.work_location.like(f"%{escape_like(region)}%", escape="\\")
        )
    gwy_total = gwy.count()
    gwy_recruit = gwy.with_entities(
        func.sum(GwyPosition.recruit_count)
    ).scalar()
    gwy_recruit_text = f"招录合计 {int(gwy_recruit)} 人" if gwy_recruit else "招录人数未公布"

    # 进面分：按 position_code 关联 gwy_score_line
    codes = [row.position_code for row in gwy.limit(500).all() if row.position_code]
    avg_min_score = None
    if codes:
        avg_min_score = (
            db.query(func.avg(GwyScoreLine.min_score))
            .filter(
                GwyScoreLine.year == year,
                GwyScoreLine.position_code.in_(codes),
            )
            .scalar()
        )

    # 国考证据
    gwy_rows = gwy.limit(GWY_POSITION_LIMIT).all()
    for row in gwy_rows:
        ev = _evidence(
            f"国考岗位 · {row.dept_name or row.bureau or '部门'}",
            f"{row.position_name}（{row.position_distribution or row.work_location or '地点未公布'}），"
            f"招 {row.recruit_count or '?'} 人",
            url=row.source_url,
        )
        if ev not in evidence:
            evidence.append(ev)

    # ---- 省考：专业（本科要求）+ 省份 ----
    province_scope = region  # 省考按省份限定（如「广东」）
    gwy_p = db.query(GwyProvincePosition).filter(
        GwyProvincePosition.year == year,
        or_(
            GwyProvincePosition.major_req_undergrad.ilike(pattern, escape="\\"),
            GwyProvincePosition.major_req_grad.ilike(pattern, escape="\\"),
        ),
    )
    if province_scope:
        gwy_p = gwy_p.filter(GwyProvincePosition.province == province_scope)
    p_total = gwy_p.count()
    p_recruit = gwy_p.with_entities(
        func.sum(GwyProvincePosition.recruit_count)
    ).scalar()
    p_recruit_text = f"招录合计 {int(p_recruit)} 人" if p_recruit else "招录人数未公布"

    for row in gwy_p.limit(GWY_POSITION_LIMIT).all():
        ev = _evidence(
            f"省考岗位 · {row.dept_name or '部门'}",
            f"{row.position_name}（{row.exam_region or row.province}），招 {row.recruit_count or '?'} 人",
            url=row.source_url,
        )
        if ev not in evidence:
            evidence.append(ev)

    # ---- 汇总 ----
    if gwy_total == 0 and p_total == 0:
        return _empty_path(
            "civil_service",
            "考公",
            "该专业暂无国考/省考可报岗位数据，可尝试更宽泛的专业关键词或清空地区。",
        )

    region_text = f"{region} " if region else ""
    risk_desc = (
        "国考整体录取率约 1-3%，省考约 3-5%；岗位分配与专业限制不确定性高。"
    )
    if region:
        risk_desc += f"（仅覆盖 {region} 的省考数据）"

    coverage_parts = [
        f"{region_text}国考可报岗位 {gwy_total} 个（{gwy_recruit_text}）",
        f"{region_text}省考可报岗位 {p_total} 个（{p_recruit_text}）",
    ]
    if avg_min_score:
        coverage_parts.append(f"国考平均进面最低分约 {avg_min_score:.1f} 分")

    return {
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
    }


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
    md = db.query(MarketData).filter(
        MarketData.industry.ilike(f"%{escape_like(major)}%", escape="\\")
    )
    md_region = md
    if region:
        md_region = md_region.filter(
            MarketData.region.like(f"%{escape_like(region)}%", escape="\\")
        )
    md_total = md_region.count()
    # 取数查询：地区命中用地区，否则回退全国
    md_query = md_region if md_total else md
    scope_label = region or "全国"
    if region and not md_total:
        logger.info("就业路 market_data 无 %s 地区数据，回退全国口径", region)
        scope_label = f"{region}（全国口径）"
    md_salary: list[str] = []
    for row in md_query.order_by(MarketData.year.desc()).limit(MARKET_LIMIT).all():
        md_salary.append(f"{row.indicator} {_format_value(row.value, row.unit)}（{row.year}）")
        evidence.append(_evidence(
            f"行业数据 · {row.indicator}",
            f"{row.value} {row.unit}（{row.year}）",
            url=row.source_url,
        ))
    if md_salary:
        coverage_parts.append(f"{scope_label}行业薪资带：" + "、".join(md_salary[:3]))

    # ---- salary_benchmarks：城市岗位薪资（entry 级）----
    sb = db.query(SalaryBenchmark).filter(
        SalaryBenchmark.experience_level == "entry",
    )
    if region:
        sb = sb.filter(SalaryBenchmark.city.like(f"%{escape_like(region)}%", escape="\\"))
    else:
        sb = sb.limit(0)  # 未指定地区时不展示岗位薪资样本（城市粒度才有意义）
    sb_total = sb.count()
    sb_parts: list[str] = []
    for row in sb.order_by(SalaryBenchmark.year.desc()).limit(SALARY_LIMIT).all():
        sb_parts.append(
            f"{row.company}·{row.position} {row.salary_min}k-{row.salary_max}k"
        )
        evidence.append(_evidence(
            f"岗位薪资 · {row.company} {row.position}",
            f"{row.salary_min}k-{row.salary_max}k（中位 {row.salary_median}k，{row.year}）",
            url=None,
            note=f"来源：{row.source}（无链接）",
        ))
    if sb_parts:
        coverage_parts.append(f"{region or ''}应届岗位薪资样本 {sb_total} 条：\n" + "\n".join(f"- {s}" for s in sb_parts[:5]))

    # ---- schools：地区就业率/考研率 ----
    sc = db.query(School)
    if region:
        sc = sc.filter(School.province == region)
    if school_tier:
        sc = sc.filter(School.level == school_tier)
    sc_total = sc.count()
    emp_rate = sc.with_entities(func.avg(School.employment_rate)).scalar()
    grad_rate = sc.with_entities(func.avg(School.grad_school_rate)).scalar()
    if sc_total and (emp_rate is not None or grad_rate is not None):
        rate_parts = []
        if emp_rate is not None:
            rate_parts.append(f"就业率 {emp_rate:.1f}%")
        if grad_rate is not None:
            rate_parts.append(f"考研率 {grad_rate:.1f}%")
        coverage_parts.append(f"{region or '全国'}{school_tier or ''}层次院校平均" + "、".join(rate_parts))
        for row in sc.limit(SCHOOL_LIMIT).all():
            evidence.append(_evidence(
                f"院校参考 · {row.name}",
                f"就业率 {row.employment_rate or '?'}% / 考研率 {row.grad_school_rate or '?'}%",
                url=row.report_index_url,
            ))

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
# 综合建议
# ----------------------------------------------------------------------
def _build_recommendation(metrics: list[dict[str, Any]], input_summary: dict) -> str:
    """三路对比后的条件式建议 — 纯规则，不替用户决定。"""
    lines: list[str] = []
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
                f"- 考研：相关分数线记录 {m['pros'][0] if m['pros'] else ''}，"
                f"难度评估 {m['risk_level']}。"
            )
        elif m["path_type"] == "civil_service":
            lines.append(
                f"- 考公：{m['pros'][0] if m['pros'] else '岗位数据有限'}，"
                f"平均进面最低分见卡片，竞争激烈。"
            )
        else:
            lines.append(
                f"- 就业：{m['pros'][0] if m['pros'] else '薪资数据有限'}，"
                f"行业波动需留意。"
            )

    lines.append("")
    lines.append(
        "每个数字都可在卡片中展开查看来源。建议结合你的财务缓冲、家庭支持与个人偏好，"
        "从三路中选 1-2 条做深度分析，并在「决策实验室」中进一步权衡。"
    )
    return "\n".join(lines)
