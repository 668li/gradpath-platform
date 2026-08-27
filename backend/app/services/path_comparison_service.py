"""多路径 What-If 对比服务层 — 生成量化指标 + 综合建议。

为每条路径生成 5 维量化指标（收入 / 风险 / 成长性 / 时间成本 / 匹配度），
并对比所有路径给出「如果追求 X，推荐 Y」的条件式建议。

预设数据覆盖 6 种常见路径：
- kaoyan          考研深造
- employment      直接就业
- civil_service   考公
- big_tech        跳槽大厂
- startup         创业
- phd_abroad      出国读博

匹配度：若用户有 holland 测评结果，按 RIASEC 维度与路径特征计算；
没有则给中性默认值（match_score=60, 通用说明）。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.path_comparison import PathComparison

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 6 种常见路径预设数据
# ----------------------------------------------------------------------
# 字段说明：
# - income_1y/3y/5y: 1/3/5 年预期收入区间（参考一线/新一线城市中位数）
# - risk_level: low / medium / high
# - risk_description: 风险说明
# - growth_score: 1-10 行业前景与晋升空间综合评分
# - time_cost_months: 准备/求职/适应期月数
# - default_match_score: 用户无测评时的中性匹配度
# - holland_match: 该路径强匹配的 RIASEC 维度，用于匹配度计算
# - pros / cons: 优势 / 劣势要点
# ----------------------------------------------------------------------
PATH_PRESETS: dict[str, dict[str, Any]] = {
    "kaoyan": {
        "label": "考研深造",
        "income_1y": "0-5万",
        "income_3y": "15-25万",
        "income_5y": "25-40万",
        "risk_level": "high",
        "risk_description": "考研录取率<30%，备考失败将损失 1 年时间；学历贬值与就业市场不确定性增加。",
        "growth_score": 7,
        "time_cost_months": 12,
        "default_match_score": 65,
        "holland_match": ["I", "C"],
        "pros": [
            "学历提升带来起薪溢价与岗位筛选优势",
            "可跨专业转换方向，扩大职业选择面",
            "名校资源、校友网络与导师人脉长期受益",
        ],
        "cons": [
            "备考周期长，机会成本显著",
            "研究生阶段学术压力与项目压力并存",
            "若所选方向就业转冷，3 年后可能面临供需失衡",
        ],
    },
    "employment": {
        "label": "直接就业",
        "income_1y": "8-15万",
        "income_3y": "15-25万",
        "income_5y": "20-35万",
        "risk_level": "medium",
        "risk_description": "就业竞争激烈，应届生岗位供需失衡；试用期淘汰与 35 岁焦虑需提前规划。",
        "growth_score": 6,
        "time_cost_months": 3,
        "default_match_score": 60,
        "holland_match": ["R", "E", "S"],
        "pros": [
            "立即获得现金流，积累实战经验",
            "提前进入职场赛道，建立行业人脉",
            "可通过跳槽快速调整方向",
        ],
        "cons": [
            "起薪与岗位天花板受限，需通过跳槽突破",
            "行业周期波动直接影响稳定性",
            "若未持续学习，3-5 年后易遇瓶颈",
        ],
    },
    "civil_service": {
        "label": "考公",
        "income_1y": "6-10万",
        "income_3y": "10-15万",
        "income_5y": "15-22万",
        "risk_level": "medium",
        "risk_description": "国考录取率 1-3%，省考 3-5%；岗位分配不确定，调动困难。",
        "growth_score": 4,
        "time_cost_months": 9,
        "default_match_score": 55,
        "holland_match": ["C", "S"],
        "pros": [
            "体制内稳定，福利保障完善",
            "社会地位较高，工作强度可控",
            "退休待遇优于市场化岗位",
        ],
        "cons": [
            "薪资增长缓慢，晋升论资排辈",
            "职业天花板明显，转行成本高",
            "需适应体制文化与人际关系",
        ],
    },
    "big_tech": {
        "label": "跳槽大厂",
        "income_1y": "20-35万",
        "income_3y": "35-55万",
        "income_5y": "50-80万",
        "risk_level": "medium",
        "risk_description": "大厂面试 5-7 轮，岗位竞争 50:1 起；裁员周期与业务调整频繁。",
        "growth_score": 9,
        "time_cost_months": 4,
        "default_match_score": 62,
        "holland_match": ["R", "I", "E"],
        "pros": [
            "起薪显著高于行业均值，期权 / 股票潜在收益",
            "技术栈先进，与顶尖同事共事",
            "履历溢价明显，后续跳槽议价空间大",
        ],
        "cons": [
            "996 / 大小周工作强度大，健康风险高",
            "35 岁危机与裁员周期需提前对冲",
            "晋升通道拥挤，绩效考核压力持续",
        ],
    },
    "startup": {
        "label": "创业",
        "income_1y": "0-10万",
        "income_3y": "0-50万",
        "income_5y": "0-200万",
        "risk_level": "high",
        "risk_description": "初创 3 年存活率<10%，现金流断裂与团队分裂是主要风险；个人财务连带责任。",
        "growth_score": 10,
        "time_cost_months": 6,
        "default_match_score": 50,
        "holland_match": ["E", "A", "I"],
        "pros": [
            "上限极高，成功后回报远超打工",
            "全方位锻炼产品 / 商业 / 管理能力",
            "可自主选择方向与团队文化",
        ],
        "cons": [
            "失败率高，3 年内大概率清零",
            "现金流压力大，需自担法律与财务风险",
            "工作生活平衡几乎不存在",
        ],
    },
    "phd_abroad": {
        "label": "出国读博",
        "income_1y": "10-20万",
        "income_3y": "15-30万",
        "income_5y": "30-60万",
        "risk_level": "high",
        "risk_description": "申请周期 1-2 年，奖学金竞争激烈；博士延期率 50%+，回国就业市场适配不确定。",
        "growth_score": 8,
        "time_cost_months": 18,
        "default_match_score": 58,
        "holland_match": ["I", "A"],
        "pros": [
            "海外学术训练与科研资源深度积累",
            "海外博士回国可走人才引进通道",
            "学术圈人脉与国际视野长期受益",
        ],
        "cons": [
            "申请周期长，准备成本高",
            "博士延期与心理健康压力需提前预案",
            "回国就业若方向不匹配，3-5 年适应期",
        ],
    },
}

# path_type 中文标签
PATH_LABELS: dict[str, str] = {k: v["label"] for k, v in PATH_PRESETS.items()}


# ----------------------------------------------------------------------
# Holland 维度含义（用于匹配度计算与说明）
# ----------------------------------------------------------------------
_HOLLAND_NAMES = {
    "R": "实际型（动手操作）",
    "I": "研究型（分析推理）",
    "A": "艺术型（创造表达）",
    "S": "社会型（沟通协作）",
    "E": "企业型（领导推动）",
    "C": "常规型（条理细节）",
}


# ----------------------------------------------------------------------
# generate_comparison: 主入口
# ----------------------------------------------------------------------
def generate_comparison(
    paths: list[dict[str, str]],
    user_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """为多条路径生成量化对比指标 + 综合建议。

    Args:
        paths: [{"path_type": "kaoyan", "target_role": "后端开发"}, ...]
        user_context: 可选，含 holland_code / recommended_directions 等

    Returns:
        {
            "metrics": [PathMetrics dict, ...],
            "recommendation": "综合建议文本",
            "user_context": dict,  # 实际使用的上下文
        }
    """
    holland_code = (user_context or {}).get("holland_code") or ""
    recommended_directions = (user_context or {}).get("recommended_directions") or []

    metrics: list[dict[str, Any]] = []
    for p in paths:
        path_type = p.get("path_type", "")
        target_role = p.get("target_role", "")
        preset = PATH_PRESETS.get(path_type)
        if preset is None:
            # 未知 path_type 兜底为 employment
            preset = PATH_PRESETS["employment"]
            path_type = "employment"

        match_score, match_desc = _compute_match_score(
            preset, holland_code, recommended_directions, target_role
        )

        metrics.append(
            {
                "path_type": path_type,
                "target_role": target_role,
                "income_1y": preset["income_1y"],
                "income_3y": preset["income_3y"],
                "income_5y": preset["income_5y"],
                "risk_level": preset["risk_level"],
                "risk_description": preset["risk_description"],
                "growth_score": preset["growth_score"],
                "time_cost_months": preset["time_cost_months"],
                "match_score": match_score,
                "match_description": match_desc,
                "pros": list(preset["pros"]),
                "cons": list(preset["cons"]),
            }
        )

    recommendation = get_recommendation(metrics, holland_code)

    return {
        "metrics": metrics,
        "recommendation": recommendation,
        "user_context": {
            "holland_code": holland_code,
            "recommended_directions": recommended_directions,
        },
    }


# ----------------------------------------------------------------------
# 匹配度计算
# ----------------------------------------------------------------------
def _compute_match_score(
    preset: dict[str, Any],
    holland_code: str,
    recommended_directions: list[str],
    target_role: str,
) -> tuple[int, str]:
    """计算路径与用户画像的匹配度。

    - 无 holland_code：返回 preset.default_match_score + 通用说明
    - 有 holland_code：取交集维度 * 加权 + target_role 命中推荐方向加 10
    """
    if not holland_code:
        return preset["default_match_score"], "暂无测评数据，按行业默认匹配度估算。"

    # 用户 top3 维度集合（取前 3 个字母）
    user_dims = set(holland_code[:3].upper())
    path_dims = set(preset["holland_match"])
    intersect = user_dims & path_dims

    # 基础分：每个匹配维度 +15，上限 70
    base = min(70, 30 + len(intersect) * 15)

    # target_role 命中推荐方向 +10
    role_hit = False
    if target_role and recommended_directions:
        for d in recommended_directions:
            if target_role in d or d in target_role:
                role_hit = True
                break
    if role_hit:
        base = min(100, base + 10)

    # 说明文本
    if intersect:
        dim_desc = "、".join(_HOLLAND_NAMES.get(d, d) for d in sorted(intersect))
        desc = f"你的霍兰德代码 {holland_code} 与本路径在 {dim_desc} 维度匹配。"
    else:
        desc = f"你的霍兰德代码 {holland_code} 与本路径特征重合度较低，需审慎评估。"

    if role_hit:
        desc += "目标角色与测评推荐方向一致，匹配度进一步提升。"

    return base, desc


# ----------------------------------------------------------------------
# get_recommendation: 生成自然语言综合建议
# ----------------------------------------------------------------------
def get_recommendation(metrics: list[dict[str, Any]], holland_code: str = "") -> str:
    """对比所有路径的各维度，生成「如果追求 X，推荐 Y」的条件式建议。

    不替用户决定，而是从 5 个维度（收入 / 风险 / 成长 / 时间 / 匹配度）
    各自给出最优路径，最后给出综合权衡提示。
    """
    if not metrics:
        return "暂无对比数据。"

    # 维度最优路径
    best_income = _pick_best_income(metrics)
    lowest_risk = _pick_lowest_risk(metrics)
    highest_growth = _pick_highest_growth(metrics)
    lowest_time = _pick_lowest_time(metrics)
    highest_match = _pick_highest_match(metrics)

    lines: list[str] = []
    if best_income:
        lines.append(
            f"如果追求收入上限，推荐 {best_income['target_role']}（{PATH_LABELS.get(best_income['path_type'], best_income['path_type'])}）："
            f"5 年预期 {best_income['income_5y']}。"
        )
    if lowest_risk:
        risk_zh = {"low": "低风险", "medium": "中风险", "high": "高风险"}.get(
            lowest_risk["risk_level"], lowest_risk["risk_level"]
        )
        lines.append(
            f"如果追求稳定低风险，推荐 {lowest_risk['target_role']}（{PATH_LABELS.get(lowest_risk['path_type'], lowest_risk['path_type'])}）："
            f"{risk_zh}，{lowest_risk['risk_description']}"
        )
    if highest_growth:
        lines.append(
            f"如果追求成长性，推荐 {highest_growth['target_role']}（{PATH_LABELS.get(highest_growth['path_type'], highest_growth['path_type'])}）："
            f"成长性 {highest_growth['growth_score']}/10。"
        )
    if lowest_time:
        lines.append(
            f"如果时间成本敏感，推荐 {lowest_time['target_role']}（{PATH_LABELS.get(lowest_time['path_type'], lowest_time['path_type'])}）："
            f"准备期约 {lowest_time['time_cost_months']} 个月。"
        )
    if highest_match:
        lines.append(
            f"如果追求与个人画像匹配，推荐 {highest_match['target_role']}（{PATH_LABELS.get(highest_match['path_type'], highest_match['path_type'])}）："
            f"匹配度 {highest_match['match_score']}/100。{highest_match['match_description']}"
        )

    # 综合权衡提示
    lines.append(
        "建议结合你的现实约束（财务缓冲、家庭支持、个人偏好）从上述路径中选 1-2 条做深度分析，"
        "并保留 1 条作为备选。可在「决策实验室」中对所选路径做进一步权衡。"
    )

    if holland_code:
        lines.append(f"参考：你的霍兰德代码为 {holland_code}，匹配度已据此计算。")

    return "\n".join(lines)


def _pick_best_income(metrics: list[dict[str, Any]]) -> dict[str, Any] | None:
    """选 5 年收入上限最高的路径（按区间上限整数比较）。"""

    def _upper(s: str) -> int:
        # "20-35万" → 35
        try:
            tail = s.split("-")[-1]
            return int("".join(c for c in tail if c.isdigit()))
        except Exception:
            return 0

    if not metrics:
        return None
    return max(metrics, key=lambda m: _upper(m.get("income_5y", "")))


def _pick_lowest_risk(metrics: list[dict[str, Any]]) -> dict[str, Any] | None:
    order = {"low": 0, "medium": 1, "high": 2}
    if not metrics:
        return None
    return min(metrics, key=lambda m: order.get(m.get("risk_level", "high"), 2))


def _pick_highest_growth(metrics: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not metrics:
        return None
    return max(metrics, key=lambda m: m.get("growth_score", 0))


def _pick_lowest_time(metrics: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not metrics:
        return None
    return min(metrics, key=lambda m: m.get("time_cost_months", 999))


def _pick_highest_match(metrics: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not metrics:
        return None
    return max(metrics, key=lambda m: m.get("match_score", 0))


# ----------------------------------------------------------------------
# 用户上下文构建
# ----------------------------------------------------------------------
def build_user_context(db: Session, user_id) -> dict[str, Any]:
    """从用户最新测评结果构建上下文。

    Returns:
        {"holland_code": "RIA", "recommended_directions": [...]}
        若无测评，返回空 dict。
    """
    assessment = (
        db.query(Assessment)
        .filter(Assessment.user_id == user_id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if assessment is None:
        return {}
    return {
        "holland_code": assessment.result_code,
        "recommended_directions": list(assessment.recommended_directions or []),
        "assessment_type": assessment.assessment_type,
    }


# ----------------------------------------------------------------------
# 持久化
# ----------------------------------------------------------------------
def save_comparison(
    db: Session,
    user_id,
    paths: list[dict[str, str]],
    comparison_result: dict[str, Any],
    user_context: dict[str, Any] | None = None,
) -> PathComparison:
    """保存一次对比记录并返回。"""
    record = PathComparison(
        user_id=user_id,
        paths=paths,
        comparison_result=comparison_result,
        user_context=user_context,
        recommendation=comparison_result.get("recommendation", ""),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_history(db: Session, user_id) -> list[PathComparison]:
    """获取用户的历史对比记录（按时间倒序）。"""
    return (
        db.query(PathComparison)
        .filter(PathComparison.user_id == user_id)
        .order_by(PathComparison.created_at.desc())
        .all()
    )


def submit_outcome(
    db: Session, record_id: str, user_id, payload: dict[str, Any]
) -> PathComparison | None:
    """写入结果回传字段（决策飞轮闭环）。

    记录不存在或不属于该用户时返回 None（由调用方转 404）。
    """
    record = (
        db.query(PathComparison)
        .filter(PathComparison.id == record_id, PathComparison.user_id == user_id)
        .first()
    )
    if record is None:
        return None
    record.selected_path = payload.get("selected_path")
    record.selected_label = payload.get("selected_label")
    record.outcome_status = payload.get("outcome_status")
    record.actual_outcome = payload.get("actual_outcome")
    record.satisfaction = payload.get("satisfaction")
    record.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record


def to_response(record: PathComparison) -> dict[str, Any]:
    """将 PathComparison ORM 实例转为 API 响应 dict。"""
    result = record.comparison_result or {}
    return {
        "id": str(record.id),
        "metrics": result.get("metrics", []),
        "recommendation": record.recommendation or result.get("recommendation", ""),
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
