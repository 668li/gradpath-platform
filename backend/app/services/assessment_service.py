# backend/app/services/assessment_service.py
"""职业测评服务层 — 霍兰德职业兴趣测评。

霍兰德 6 维度：R(实际型)、I(研究型)、A(艺术型)、S(社会型)、E(企业型)、C(常规型)。
题目内置在代码中，无需数据库表；提交答案后计算 top 3 维度并生成推荐方向。
"""
from collections import Counter

# ----------------------------------------------------------------------
# 霍兰德测评题目（每题 2 个选项，分别对应不同维度）
# ----------------------------------------------------------------------
HOLLAND_QUESTIONS = [
    {"id": "q1", "question": "你更喜欢做哪种活动？", "options": [
        {"value": "R", "label": "修理机械或动手制作物品"},
        {"value": "S", "label": "帮助他人解决心理或情感问题"},
    ]},
    {"id": "q2", "question": "你更愿意参加哪种课程？", "options": [
        {"value": "I", "label": "科学研究或数据分析课程"},
        {"value": "E", "label": "商业管理或创业课程"},
    ]},
    {"id": "q3", "question": "哪种工作环境更吸引你？", "options": [
        {"value": "A", "label": "创意工作室或设计公司"},
        {"value": "C", "label": "结构化的办公室或金融机构"},
    ]},
    {"id": "q4", "question": "你更擅长哪类任务？", "options": [
        {"value": "R", "label": "操作工具、设备或机器"},
        {"value": "I", "label": "分析复杂问题或理论"},
    ]},
    {"id": "q5", "question": "哪种角色更适合你？", "options": [
        {"value": "S", "label": "团队中的协调者和支持者"},
        {"value": "E", "label": "团队中的领导者和决策者"},
    ]},
    {"id": "q6", "question": "你的理想周末更接近？", "options": [
        {"value": "A", "label": "看展览、写创作、做手工"},
        {"value": "C", "label": "整理计划、做预算、读书"},
    ]},
    {"id": "q7", "question": "你更看重工作的哪个方面？", "options": [
        {"value": "R", "label": "能看到实际的、有形的成果"},
        {"value": "A", "label": "能自由表达创意和想法"},
    ]},
    {"id": "q8", "question": "面对新项目，你更倾向于？", "options": [
        {"value": "I", "label": "深入研究原理和可行性"},
        {"value": "C", "label": "制定详细计划和流程"},
    ]},
    {"id": "q9", "question": "哪种社交场景更让你舒适？", "options": [
        {"value": "S", "label": "一对一深度交流，帮助他人"},
        {"value": "E", "label": "在团队中发言、说服和影响他人"},
    ]},
    {"id": "q10", "question": "你认为自己的优势是？", "options": [
        {"value": "R", "label": "动手能力强，实践能力突出"},
        {"value": "I", "label": "逻辑思维强，善于分析推理"},
    ]},
    {"id": "q11", "question": "你更享受哪种学习方式？", "options": [
        {"value": "A", "label": "通过创作和实验来学习"},
        {"value": "C", "label": "通过系统化课程和笔记来学习"},
    ]},
    {"id": "q12", "question": "哪种成就感更让你满足？", "options": [
        {"value": "S", "label": "看到他人因你的帮助而成长"},
        {"value": "E", "label": "带领团队完成了一个挑战性目标"},
    ]},
]

HOLLAND_DESCRIPTIONS = {
    "R": {"name": "实际型", "desc": "喜欢动手操作，注重实践和具体成果", "directions": ["后端开发", "运维工程师", "嵌入式开发", "硬件工程师"]},
    "I": {"name": "研究型", "desc": "善于分析推理，喜欢探索和解决复杂问题", "directions": ["算法工程师", "数据科学家", "科研人员", "安全研究"]},
    "A": {"name": "艺术型", "desc": "富有创造力，追求自由表达和审美", "directions": ["前端开发", "UI/UX设计", "产品经理", "创意设计"]},
    "S": {"name": "社会型", "desc": "乐于助人，善于沟通和协调人际关系", "directions": ["产品经理", "项目管理", "技术顾问", "教育培训"]},
    "E": {"name": "企业型", "desc": "具有领导力，善于说服和推动团队达成目标", "directions": ["产品经理", "创业", "项目管理", "商业分析"]},
    "C": {"name": "常规型", "desc": "做事有条理，注重细节和规则", "directions": ["测试工程师", "数据分析师", "财务技术", "运维自动化"]},
}


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
