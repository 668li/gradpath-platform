# backend/app/services/assessment_service.py
"""职业测评服务层 — 支持 4 种测评体系。

- 霍兰德职业兴趣测评（48 题，6 维度 R/I/A/S/E/C）
- MBTI 16 型人格测试（40 题，4 维度 E/I、S/N、T/F、J/P）
- 大五人格 OCEAN 测评（50 题，5 维度 O/C/E/A/N，Likert 5 级）
- DISC 行为风格测评（24 题，4 维度 D/I/S/C）

题目内置在 `app/services/assessment_data/` 下，无需数据库表。
提交答案后按测评类型调用对应计算函数，生成结果编码、摘要与推荐方向。
"""
from collections import Counter

from app.services.assessment_data.big_five_questions import (
    BIG_FIVE_DESCRIPTIONS,
    BIG_FIVE_ITEM_DIMENSIONS,
    BIG_FIVE_QUESTIONS,
)
from app.services.assessment_data.disc_questions import (
    DISC_QUESTIONS,
    DISC_TYPES,
)
from app.services.assessment_data.holland_questions import (
    HOLLAND_DESCRIPTIONS,
    HOLLAND_QUESTIONS,
)
from app.services.assessment_data.mbti_questions import (
    MBTI_QUESTIONS,
    MBTI_TYPES,
)

# ----------------------------------------------------------------------
# 向后兼容：保留 HOLLAND_QUESTIONS 顶级导出
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# 霍兰德测评结果计算
# ----------------------------------------------------------------------
def calculate_holland_result(answers: dict) -> dict:
    """计算霍兰德测评结果。answers = {"q1": "R", "q2": "I", ...}

    统计各维度出现次数，取前三高维度拼接为 result_code，
    并汇总推荐方向（去重保留顺序，最多 6 个）。

    Returns:
        {"result_code", "result_summary", "recommended_directions", "scores"}
    """
    scores = Counter(answers.values())
    # 取前三高的维度
    top3 = [code for code, _ in scores.most_common(3)]
    result_code = "".join(top3)

    # 生成描述
    parts = []
    directions = []
    for code in top3:
        info = HOLLAND_DESCRIPTIONS.get(code, {})
        parts.append(f"{info.get('name', code)}({code})：{info.get('desc', '')}")
        directions.extend(info.get('directions', []))

    summary = "你的职业兴趣类型为 " + result_code + "。\n" + "；".join(parts)

    # 去重保留推荐方向顺序
    seen = set()
    unique_directions = []
    for d in directions:
        if d not in seen:
            seen.add(d)
            unique_directions.append(d)

    return {
        "result_code": result_code,
        "result_summary": summary,
        "recommended_directions": unique_directions[:6],
        "scores": dict(scores),
    }


# ----------------------------------------------------------------------
# MBTI 测评结果计算
# ----------------------------------------------------------------------
def calculate_mbti_result(answers: dict) -> dict:
    """计算 MBTI 测评结果。answers = {"mbti_q1": "E", "mbti_q2": "I", ...}

    统计 4 维度（E/I、S/N、T/F、J/P）字母出现次数，每维度取得分较高者，
    拼接为 16 型代码（如 "INTJ"）。

    Returns:
        {"result_code", "result_summary", "recommended_directions", "scores"}
    """
    counts = Counter(answers.values())

    # 4 个维度，每维度取得分较高者（平局时取第一极）
    dimension_pairs = [("E", "I"), ("S", "N"), ("T", "F"), ("J", "P")]
    result_chars = []
    for first, second in dimension_pairs:
        if counts.get(first, 0) >= counts.get(second, 0):
            result_chars.append(first)
        else:
            result_chars.append(second)
    result_code = "".join(result_chars)

    type_info = MBTI_TYPES.get(result_code, {})
    name = type_info.get("name", "")
    description = type_info.get("description", "")
    summary = (
        f"你的 MBTI 人格类型为 {result_code}"
        + (f"（{name}）" if name else "")
        + f"。\n{description}"
    )

    # 推荐职业方向
    directions = list(type_info.get("careers", []))

    # 各字母得分
    scores = {}
    for first, second in dimension_pairs:
        scores[first] = counts.get(first, 0)
        scores[second] = counts.get(second, 0)

    return {
        "result_code": result_code,
        "result_summary": summary,
        "recommended_directions": directions[:6],
        "scores": scores,
    }


# ----------------------------------------------------------------------
# 大五人格测评结果计算
# ----------------------------------------------------------------------
def calculate_big_five_result(answers: dict) -> dict:
    """计算大五人格测评结果。answers = {"bf_q1": "4", "bf_q2": "3", ...}

    每维度 10 题，计算各维度均分（保留 2 位小数）。
    result_code 形如 "O4C5E3A4N2"（每维度字母 + 四舍五入整数分）。
    推荐方向取均分最高的 2 个维度的推荐职业合并去重。

    Returns:
        {"result_code", "result_summary", "recommended_directions", "scores"}
    """
    dim_scores: dict[str, list[int]] = {"O": [], "C": [], "E": [], "A": [], "N": []}
    for qid, score_value in answers.items():
        dim = BIG_FIVE_ITEM_DIMENSIONS.get(qid)
        if not dim:
            continue
        try:
            score = int(score_value)
        except (ValueError, TypeError):
            continue
        if 1 <= score <= 5:
            dim_scores[dim].append(score)

    # 各维度均分
    avg_scores: dict[str, float] = {}
    for dim, score_list in dim_scores.items():
        if score_list:
            avg_scores[dim] = round(sum(score_list) / len(score_list), 2)
        else:
            avg_scores[dim] = 0.0

    # result_code：OCEAN 顺序 + 整数分
    result_code = "".join(
        f"{dim}{int(round(avg_scores[dim]))}" for dim in ["O", "C", "E", "A", "N"]
    )

    # 推荐方向：取均分最高的 2 个维度
    sorted_dims = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
    directions = []
    for dim, _ in sorted_dims[:2]:
        info = BIG_FIVE_DESCRIPTIONS.get(dim, {})
        directions.extend(info.get("careers", []))

    seen = set()
    unique_directions = []
    for d in directions:
        if d not in seen:
            seen.add(d)
            unique_directions.append(d)

    # 摘要
    parts = []
    for dim in ["O", "C", "E", "A", "N"]:
        info = BIG_FIVE_DESCRIPTIONS.get(dim, {})
        parts.append(f"{info.get('name', dim)}：{avg_scores[dim]} 分")
    summary = f"你的大五人格测评结果为 {result_code}。\n" + "；".join(parts)

    return {
        "result_code": result_code,
        "result_summary": summary,
        "recommended_directions": unique_directions[:6],
        "scores": avg_scores,
    }


# ----------------------------------------------------------------------
# DISC 测评结果计算
# ----------------------------------------------------------------------
def calculate_disc_result(answers: dict) -> dict:
    """计算 DISC 测评结果。answers = {"disc_q1": "D", "disc_q2": "I", ...}

    统计 D/I/S/C 维度出现次数，取得分最高的作为主类型 result_code。
    平局时按 D > I > S > C 顺序取靠前者。

    Returns:
        {"result_code", "result_summary", "recommended_directions", "scores"}
    """
    scores = Counter(answers.values())

    # 取得主类型：按 D/I/S/C 顺序遍历，找最高分（保证平局顺序稳定）
    order = ["D", "I", "S", "C"]
    if not scores:
        result_code = "D"
    else:
        max_count = max(scores.get(c, 0) for c in order)
        result_code = next(c for c in order if scores.get(c, 0) == max_count)

    type_info = DISC_TYPES.get(result_code, {})
    name = type_info.get("name", "")
    description = type_info.get("description", "")
    summary = (
        f"你的 DISC 行为风格主类型为 {result_code}"
        + (f"（{name}）" if name else "")
        + f"。\n{description}"
    )

    # 推荐方向
    directions = list(type_info.get("careers", []))

    # 各维度得分
    scores_out = {c: scores.get(c, 0) for c in order}

    return {
        "result_code": result_code,
        "result_summary": summary,
        "recommended_directions": directions[:6],
        "scores": scores_out,
    }


# ----------------------------------------------------------------------
# 测评题库与计算器总入口
# ----------------------------------------------------------------------
ASSESSMENT_QUESTIONS = {
    "holland": HOLLAND_QUESTIONS,
    "mbti": MBTI_QUESTIONS,
    "big_five": BIG_FIVE_QUESTIONS,
    "disc": DISC_QUESTIONS,
}

ASSESSMENT_CALCULATORS = {
    "holland": calculate_holland_result,
    "mbti": calculate_mbti_result,
    "big_five": calculate_big_five_result,
    "disc": calculate_disc_result,
}
