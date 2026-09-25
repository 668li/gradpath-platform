"""路径模拟器 v2 — 真数据胜率推演服务（2026-09-25 重构）。

范式转变（诊断报告 2026-09-19 判死旧版后的重生）：
- 旧版：10 年薪资/满意度/净资产曲线 = 零纵向数据下的伪精确计算器
- 新版：真实分布统计 + 你的位置 + 证据链 + 诚实降级

纪律（对抗审查 2026-09-25 裁决吸收）：
1. 不做第二台决策引擎 — 三线结论复用 path_decision_engine.generate_decision
   （继承条件包过滤/岗位级关联/劝退阈值/来源可溯闸），本层只叠"分布统计+可视化原料"
2. 无单点预测数 — 所有数字带 P25/P50/P75 + 样本量 N + 来源声明
3. badge 是位置描述不是概率 — 附"门槛分布位置≠录取概率"固定免责
4. 考公量纲分簇 — 进面线按 bureau 系统簇分层（边检/铁路公安簇≈50-65 分，
   税务/统计簇≈110-125 分，混池统计=数字垃圾），只对同簇算你的位置
5. 样本量阈值 N<5 → has_data=False 诚实降级，不硬算
6. 数据样本性质如实声明 — grad_school_intel 为人工核录样本（985/211 两档），
   非官方统计总量；market_data 为国家统计局官方口径
"""

import logging
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 样本量阈值：低于此值不做分布统计（防"三行数据算中位数"）
_MIN_SAMPLE = 5
# 来源可溯闸阈值（与 path_decision_engine 同纪律）


# ----------------------------------------------------------------------
# 工具：分位数（与 path_decision_engine._percentile 同口径）
# ----------------------------------------------------------------------


def _percentile(sorted_vals: list[float], q: float) -> float:
    """线性插值分位数。输入须已升序。"""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = (len(sorted_vals) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _ratio_to_float(raw: str | None) -> float | None:
    """报录比字符串 '15:1' → 15.0；脏值返回 None。"""
    if not raw:
        return None
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*[:：比/]\s*1?\s*$", str(raw).strip())
    return float(m.group(1)) if m else None


def _percentile_of_score(sorted_vals: list[float], score: float) -> int | None:
    """你的分数在分布中的百分位（0-100，四舍五入）。"""
    if not sorted_vals or len(sorted_vals) < _MIN_SAMPLE:
        return None
    below = sum(1 for v in sorted_vals if v <= score)
    return round(below / len(sorted_vals) * 100)


def _pos_word(pct: int | None) -> str:
    """百分位 → 纯位置描述词（刻意不给结果性判断）。"""
    if pct is None:
        return "数据不足"
    if pct >= 85:
        return "位于分布高位"
    if pct >= 50:
        return "位于分布中上"
    if pct >= 15:
        return "位于分布中下"
    return "位于分布低位"


# ----------------------------------------------------------------------
# 考研分支：grad_school_intel 按层次聚合
# ----------------------------------------------------------------------


def _grad_stats(db: Session, tier: str) -> dict[str, Any]:
    """按 school_tier 聚合报录比/复试线分布。

    样本性质：人工核录样本（90 校便利样本、单年口径），结果中如实声明。
    """
    try:
        rows = db.execute(
            text(
                "SELECT admission_ratio, score_line, background_discrimination "
                "FROM grad_school_intel WHERE school_tier = :tier"
            ),
            {"tier": tier},
        ).fetchall()
    except Exception:
        logger.exception("grad_school_intel 查询失败")
        rows = []

    ratios = sorted(v for v in (_ratio_to_float(r[0]) for r in rows) if v)
    lines = sorted(r[1] for r in rows if r[1])
    severe = sum(1 for r in rows if r[2] == "severe")
    n = len(rows)

    stats: dict[str, Any] = {
        "tier": tier,
        "sample_note": f"GradPath 人工核录样本 N={n}（{tier} 层次院校，单年口径，非官方统计总量）",
        "metrics": [],
        "carding_rate": None,
    }
    if len(ratios) >= _MIN_SAMPLE:
        stats["metrics"].append(
            {
                "label": "报录比分布",
                "p25": round(_percentile(ratios, 0.25), 1),
                "p50": round(_percentile(ratios, 0.5), 1),
                "p75": round(_percentile(ratios, 0.75), 1),
                "unit": ":1",
                "sample_size": len(ratios),
                "source": "grad_school_intel（人工核录）",
                "direction": "lower_better",
            }
        )
    if len(lines) >= _MIN_SAMPLE:
        stats["metrics"].append(
            {
                "label": "复试线分布",
                "p25": int(_percentile(lines, 0.25)),
                "p50": int(_percentile(lines, 0.5)),
                "p75": int(_percentile(lines, 0.75)),
                "unit": "分",
                "sample_size": len(lines),
                "source": "grad_school_intel（人工核录）",
                "direction": "your_score",
                "distribution": [int(v) for v in lines],  # 前端画分布图+你的位置竖线
            }
        )
    if n >= _MIN_SAMPLE:
        stats["carding_rate"] = {
            "severe_count": severe,
            "total": n,
            "rate": round(severe / n * 100),
            "note": f"该层次 {n} 所样本校中 {severe} 所明确卡第一学历（较严重档）",
        }
    return stats


# ----------------------------------------------------------------------
# 考公分支：gwy_score_line 按系统簇分桶（量纲修复）
# ----------------------------------------------------------------------

# 进面线量纲按用人系统分簇（对抗审查实测：两簇分数量纲不可混）。
# 簇内才是同量纲总体，簇间平均/分位都是数字垃圾。
_BUREAU_CLUSTERS: dict[str, list[str]] = {
    # 行测+申论+专业科目口径簇（公安/边检类，总分 ~50-70 区间为主）
    "police": ["公安", "边检", "边防检查", "出入境", "海关缉私", "移民局", "移民管理"],
    # 综合行测+申论口径簇（税务/统计/海事等，总分 ~90-140 区间为主）
    "general": ["税务", "统计", "海事", "气象", "地震", "审计", "财政", "海关", "邮政", "铁路"],
    # 中央党群/部委簇（单列呈现，不与地方混）
    "central": ["中央", "全国人大", "全国政协", "最高人民法院", "最高人民检察院", "外交部"],
}
_CLUSTER_LABELS = {
    "police": "公安/边检系统（含专业科目口径）",
    "general": "税务/统计/海事等综合口径系统",
    "central": "中央党群/部委系统",
}


def _cluster_of_bureau(bureau: str | None) -> str | None:
    if not bureau:
        return None
    for cluster, kws in _BUREAU_CLUSTERS.items():
        if any(k in bureau for k in kws):
            return cluster
    return "other"


def _civil_stats(db: Session, cluster: str | None) -> dict[str, Any]:
    """按系统簇聚合进面线分布。cluster=None → 全库分簇概览。"""
    try:
        rows = db.execute(
            text(
                "SELECT bureau, min_score, year, batch FROM gwy_score_line "
                "WHERE min_score IS NOT NULL"
            )
        ).fetchall()
    except Exception:
        logger.exception("gwy_score_line 查询失败")
        rows = []

    buckets: dict[str, list[float]] = {}
    for bureau, score, year, batch in rows:
        c = _cluster_of_bureau(bureau) or "other"
        buckets.setdefault(c, []).append(float(score))

    overview = {
        k: {"label": _CLUSTER_LABELS.get(k, "其他系统"), "count": len(v)}
        for k, v in sorted(buckets.items(), key=lambda item: -len(item[1]))
        if len(v) >= _MIN_SAMPLE
    }

    stats: dict[str, Any] = {
        "data_note": "国考进面线（职位级聚合，官方面试名单采集）",
        "clusters": overview,
        "metrics": [],
        "selected_cluster": cluster,
        "years": sorted({r[2] for r in rows if r[2]}),
    }

    if cluster and cluster in buckets:
        vals = sorted(buckets[cluster])
        if len(vals) >= _MIN_SAMPLE:
            stats["metrics"].append(
                {
                    "label": f"{_CLUSTER_LABELS.get(cluster, '该系统')}进面线分布",
                    "p25": round(_percentile(vals, 0.25), 1),
                    "p50": round(_percentile(vals, 0.5), 1),
                    "p75": round(_percentile(vals, 0.75), 1),
                    "unit": "分",
                    "sample_size": len(vals),
                    "source": "gwy_score_line（官方进面名单采集）",
                    "direction": "your_score",
                    "distribution": [round(v, 1) for v in vals],
                }
            )
    return stats


# ----------------------------------------------------------------------
# 就业分支：market_data（国家统计局官方口径）+ salary_benchmarks（若有）
# ----------------------------------------------------------------------


def _career_stats(db: Session) -> dict[str, Any]:
    """就业分支：官方年平均工资锚 + 众包薪资带（如有足够样本）。"""
    stats: dict[str, Any] = {"metrics": [], "data_note": ""}
    try:
        rows = db.execute(
            text(
                "SELECT indicator, category, region, value, unit, year, source, source_url "
                "FROM market_data "
                "WHERE indicator LIKE '%平均工资%' AND category IN ('全体', '地区') "
                "ORDER BY year DESC LIMIT 12"
            )
        ).fetchall()
    except Exception:
        logger.exception("market_data 查询失败")
        rows = []

    if rows:
        latest_year = max(r[5] for r in rows)
        national = [r for r in rows if r[2] is None and r[5] == latest_year]
        regions = [r for r in rows if r[2] is not None and r[5] == latest_year]
        if national:
            r0 = national[0]
            stats["metrics"].append(
                {
                    "label": f"全国城镇非私营单位年平均工资（{latest_year}）",
                    "value": int(r0[3]),
                    "unit": r0[4] or "元/年",
                    "sample_size": None,
                    "source": f"{r0[6]}（官方统计）",
                    "source_url": r0[7],
                    "direction": "anchor",
                }
            )
        if regions:
            vals = sorted(r[3] for r in regions)
            stats["metrics"].append(
                {
                    "label": f"分地区年平均工资（{latest_year}，{len(vals)} 地区）",
                    "p25": int(_percentile(vals, 0.25)),
                    "p50": int(_percentile(vals, 0.5)),
                    "p75": int(_percentile(vals, 0.75)),
                    "unit": "元/年",
                    "sample_size": len(vals),
                    "source": f"{regions[0][6]}（官方统计）",
                    "source_url": regions[0][7],
                    "direction": "anchor",
                }
            )
        stats["data_note"] = "就业薪资锚点为国家统计局官方口径；个体差异远大于地区差异，此处只作量级参照"

    return stats


# ----------------------------------------------------------------------
# 主入口：路径推演
# ----------------------------------------------------------------------


def simulate_paths(
    db: Session, paths: list[dict[str, Any]], engine_input: dict[str, Any] | None = None
) -> dict[str, Any]:
    """对 1-3 条路径做真数据推演。每条输出：分布指标+你的位置+引擎结论+诚实缺口。

    engine_input 非空（含 major 等）时，同时调用 path_decision_engine.generate_decision
    获取三线权威结论（条件包过滤/岗位级关联/劝退阈值/来源闸——继承全部纪律，不另起炉灶）。
    """
    results = []
    for p in paths:
        path_type = p.get("path_type", "career")
        est = p.get("estimated_score")
        out: dict[str, Any] = {
            "name": p.get("name") or path_type,
            "path_type": path_type,
            "target": p.get("target"),
            "city": p.get("city"),
            "estimated_score": est,
            "metrics": [],
            "your_position": None,
            "honest_gaps": [],
            "disclaimer": "以上为门槛/竞争强度的历史分布位置，不等于录取或求职成功概率",
        }

        if path_type.startswith("grad"):
            tier = p.get("target") or "985"
            stats = _grad_stats(db, tier)
            out["metrics"] = stats["metrics"]
            out["sample_note"] = stats["sample_note"]
            if stats.get("carding_rate"):
                out["carding_rate"] = stats["carding_rate"]
            # 你的位置：预估分 vs 复试线分布
            for m in stats["metrics"]:
                if m.get("direction") == "your_score" and est:
                    dist = m.get("distribution") or []
                    pct = _percentile_of_score(dist, float(est))
                    out["your_position"] = {
                        "metric": f"你的预估分 {est} vs {tier} 层次复试线分布",
                        "percentile": pct,
                        "position_word": _pos_word(pct),
                        "ref_p50": m["p50"],
                    }
            if not stats["metrics"]:
                out["honest_gaps"].append(
                    f"{tier} 层次样本不足（N<{_MIN_SAMPLE}），暂无法给出分布参照——试试 985 或 211 层次"
                )
            out["honest_gaps"].append("报录比/复试线为门槛侧数据，无法反映报考热度年度波动")

        elif path_type.startswith("civil"):
            cluster = p.get("target") or None
            stats = _civil_stats(db, cluster)
            out["metrics"] = stats["metrics"]
            out["clusters"] = stats["clusters"]
            out["data_note"] = stats["data_note"]
            years = stats.get("years") or []
            out["sample_note"] = (
                f"国考进面线 N={sum(c['count'] for c in stats['clusters'].values())} 条"
                f"（{min(years) if years else ''} 年{f'，含 {len(years)} 个年度' if len(years) > 1 else '单批次'}口径，"
                "按系统簇分层避免量纲混淆）"
            )
            for m in stats["metrics"]:
                if m.get("direction") == "your_score" and est:
                    dist = m.get("distribution") or []
                    pct = _percentile_of_score(dist, float(est))
                    out["your_position"] = {
                        "metric": f"你的模考分 {est} vs 该系统进面线分布",
                        "percentile": pct,
                        "position_word": _pos_word(pct),
                        "ref_p50": m["p50"],
                    }
            if not stats["metrics"]:
                out["honest_gaps"].append(
                    "该系统簇样本不足或未选择目标系统——请选择一个系统（公安/边检、税务/统计/海事、中央部委）"
                )
            out["honest_gaps"].append("进面线是录取者最小值（极值统计），进面≠录用，面试还有一道关")

        else:  # career
            stats = _career_stats(db)
            out["metrics"] = stats["metrics"]
            out["data_note"] = stats.get("data_note")
            if not stats["metrics"]:
                out["honest_gaps"].append("暂无官方薪资锚点数据")
            out["honest_gaps"].append(
                "个体薪资差异远大于统计口径差异（行业/公司/个人能力主导），本模块只提供量级锚点不做个体预测"
            )

        results.append(out)

    payload: dict[str, Any] = {
        "paths": results,
        "method_note": (
            "本工具只呈现真实历史分布与你的位置，不做未来预测——每个数字可展开查看样本量与来源；"
            "样本不足的维度会如实说明而不是编造"
        ),
    }

    # 引擎复用层：带专业输入时叠加三路聚合引擎的权威结论（劝退纪律/条件包/岗位级关联）
    if engine_input and engine_input.get("major"):
        try:
            from app.services.path_decision_engine import generate_decision

            decision = generate_decision(
                db,
                major=engine_input["major"],
                region=engine_input.get("region"),
                school_tier=engine_input.get("school_tier"),
                graduation_year=engine_input.get("graduation_year"),
                estimated_score=engine_input.get("estimated_score"),
                kaoyan_estimated_score=engine_input.get("kaoyan_estimated_score"),
            )
            payload["engine_analysis"] = {
                "recommendation": decision.get("recommendation"),
                "metrics": decision.get("metrics", []),
                "has_discourage_cards": any(
                    "劝退" in str(m.get("risk_level", "")) + str(m.get("remark", ""))
                    for m in decision.get("metrics", [])
                ),
                "source": "path_decision_engine（三路聚合决策引擎）",
            }
        except Exception:
            logger.exception("engine_analysis 调用失败，降级为纯分布层")
            payload["engine_analysis"] = None

    return payload
