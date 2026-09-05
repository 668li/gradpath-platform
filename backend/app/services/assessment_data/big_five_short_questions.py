# backend/app/services/assessment_data/big_five_short_questions.py
"""大五人格 OCEAN 短版题库（10 题）。

Book 2（2026-09-05）拍板：每维度 2 题、共 10 题，与 50 题版并存。
定位不是精细人格画像，而是给学习计划喂真实信号（自律/社交学习偏好等），
结果只作低分辨率参考——摘要里如实标注。

- O 开放性 (Openness)              — bfs_q1 ~ bfs_q2
- C 尽责性 (Conscientiousness)     — bfs_q3 ~ bfs_q4
- E 外向性 (Extraversion)          — bfs_q5 ~ bfs_q6
- A 宜人性 (Agreeableness)         — bfs_q7 ~ bfs_q8
- N 神经质 (Neuroticism)           — bfs_q9 ~ bfs_q10

每题 5 级 Likert 量表（1=非常不同意 … 5=非常同意），全部为正向陈述，
与 50 题版口径一致；answers 形如 {"bfs_q1": "4", ...}。
"""

from app.services.assessment_data.big_five_questions import LIKERT_OPTIONS

BFS_ITEM_DIMENSIONS: dict[str, str] = {}


def _q(qid: str, dimension: str, text: str) -> dict:
    """构造一道 Likert 题目，并登记短版权限归属。"""
    BFS_ITEM_DIMENSIONS[qid] = dimension
    return {"id": qid, "question": text, "options": LIKERT_OPTIONS}


BIG_FIVE_SHORT_QUESTIONS = [
    # ---------- O 开放性 ----------
    _q("bfs_q1", "O", "我喜欢接触与专业无关的新知识、新想法。"),
    _q("bfs_q2", "O", "我愿意用和大多数人不一样的方法解决问题。"),
    # ---------- C 尽责性 ----------
    _q("bfs_q3", "C", "我会给自己的学习任务定截止时间并遵守。"),
    _q("bfs_q4", "C", "即使没有外部监督，我也能坚持按计划学习。"),
    # ---------- E 外向性 ----------
    _q("bfs_q5", "E", "和大家一起讨论学习让我更有干劲。"),
    _q("bfs_q6", "E", "我乐于主动向别人请教，或分享自己的理解。"),
    # ---------- A 宜人性 ----------
    _q("bfs_q7", "A", "我愿意花时间帮同学解答问题，哪怕对自己没有直接好处。"),
    _q("bfs_q8", "A", "讨论出现分歧时，我会先试着理解对方的立场。"),
    # ---------- N 神经质 ----------
    _q("bfs_q9", "N", "考试或截止日期临近时，我常感到明显的焦虑。"),
    _q("bfs_q10", "N", "我常担心自己的努力得不到应有的结果。"),
]
