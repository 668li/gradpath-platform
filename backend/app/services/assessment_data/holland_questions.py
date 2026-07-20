# backend/app/services/assessment_data/holland_questions.py
"""霍兰德职业兴趣测评题库。

霍兰德 6 维度：R(实际型)、I(研究型)、A(艺术型)、S(社会型)、E(企业型)、C(常规型)。
共 48 题，每维度 8 题；每题 2 个选项分别对应不同维度。
题目 id 格式：q1 ~ q48。
"""

# ----------------------------------------------------------------------
# 题目（每题 2 个选项，分别对应不同维度）
# ----------------------------------------------------------------------
HOLLAND_QUESTIONS = [
    # ---------- 原 12 题 ----------
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
    # ---------- 扩展 36 题 ----------
    {"id": "q13", "question": "你更愿意承担哪种类型的项目？", "options": [
        {"value": "R", "label": "搭建原型、调试硬件、动手实现"},
        {"value": "S", "label": "组织团队活动、关心成员状态"},
    ]},
    {"id": "q14", "question": "下列哪种工作节奏更让你舒适？", "options": [
        {"value": "I", "label": "能长时间沉浸钻研一个问题"},
        {"value": "E", "label": "节奏紧凑、不断推动外部协作"},
    ]},
    {"id": "q15", "question": "你更欣赏怎样的产出？", "options": [
        {"value": "A", "label": "有独特审美与创意表达的作品"},
        {"value": "C", "label": "规范、可复用、文档齐全的交付物"},
    ]},
    {"id": "q16", "question": "在陌生环境中，你更可能做的是？", "options": [
        {"value": "R", "label": "先动手摸清工具和操作流程"},
        {"value": "I", "label": "先观察并思考背后的原理与规律"},
    ]},
    {"id": "q17", "question": "团队遇到分歧时，你更倾向于？", "options": [
        {"value": "S", "label": "倾听各方诉求，促成共识"},
        {"value": "E", "label": "果断拍板，明确方向并推动执行"},
    ]},
    {"id": "q18", "question": "你更喜欢的汇报方式是？", "options": [
        {"value": "A", "label": "用故事和视觉化方式呈现"},
        {"value": "C", "label": "用数据表格和结构化文档呈现"},
    ]},
    {"id": "q19", "question": "你更愿意在哪种场景发挥影响力？", "options": [
        {"value": "R", "label": "用实际产品和成果说话"},
        {"value": "A", "label": "用创意作品和审美打动他人"},
    ]},
    {"id": "q20", "question": "面对不确定性，你更可能？", "options": [
        {"value": "I", "label": "搜集资料、推演各种可能性"},
        {"value": "C", "label": "建立流程、风险评估与备选方案"},
    ]},
    {"id": "q21", "question": "你更愿意被如何评价？", "options": [
        {"value": "S", "label": "温暖可靠、值得信赖的伙伴"},
        {"value": "E", "label": "有魄力、能带领大家拿下目标的人"},
    ]},
    {"id": "q22", "question": "你更享受哪种成就感来源？", "options": [
        {"value": "R", "label": "亲手做出能用的东西"},
        {"value": "I", "label": "想清楚一个复杂的难题"},
    ]},
    {"id": "q23", "question": "你更看重学习的哪种价值？", "options": [
        {"value": "A", "label": "拓展表达与创作的边界"},
        {"value": "C", "label": "积累可复用的体系与方法"},
    ]},
    {"id": "q24", "question": "下列哪种反馈更能激励你？", "options": [
        {"value": "S", "label": "你让团队氛围变得更好了"},
        {"value": "E", "label": "你让项目取得了关键突破"},
    ]},
    {"id": "q25", "question": "你更愿意花时间打磨什么？", "options": [
        {"value": "R", "label": "工具、设备、动手操作的细节"},
        {"value": "S", "label": "他人成长路径与沟通方式"},
    ]},
    {"id": "q26", "question": "你更享受哪种工作产出？", "options": [
        {"value": "I", "label": "一份有深度的研究报告或论文"},
        {"value": "E", "label": "一项达成商业目标的合作或合同"},
    ]},
    {"id": "q27", "question": "你更希望被赋予什么权限？", "options": [
        {"value": "A", "label": "自由探索创意方向的实验权"},
        {"value": "C", "label": "制定标准与规则的规范化权"},
    ]},
    {"id": "q28", "question": "面对突发问题，你的第一反应是？", "options": [
        {"value": "R", "label": "直接动手尝试解决"},
        {"value": "I", "label": "先分析根因再下手"},
    ]},
    {"id": "q29", "question": "你更擅长处理哪种关系？", "options": [
        {"value": "S", "label": "一对一的情感支持与陪伴"},
        {"value": "E", "label": "一对多的资源整合与利益协调"},
    ]},
    {"id": "q30", "question": "你更喜欢的输出形式是？", "options": [
        {"value": "A", "label": "视觉化、有故事感的作品"},
        {"value": "C", "label": "结构化、可追溯的规范文档"},
    ]},
    {"id": "q31", "question": "你更愿意承担的责任是？", "options": [
        {"value": "R", "label": "保证产品功能可用、稳定运行"},
        {"value": "A", "label": "保证产品有独特体验与表达"},
    ]},
    {"id": "q32", "question": "你更看重的成长方式是？", "options": [
        {"value": "I", "label": "在某一领域不断深耕、突破边界"},
        {"value": "C", "label": "在体系化流程中持续优化与精进"},
    ]},
    {"id": "q33", "question": "你更愿意被信任什么？", "options": [
        {"value": "S", "label": "处理团队冲突、安抚成员情绪"},
        {"value": "E", "label": "推动跨部门协作、达成关键目标"},
    ]},
    {"id": "q34", "question": "下列哪种状态更接近你的理想？", "options": [
        {"value": "R", "label": "亲手把想法变成可用的实物"},
        {"value": "I", "label": "把模糊的问题研究清楚"},
    ]},
    {"id": "q35", "question": "你更喜欢的协作方式是？", "options": [
        {"value": "A", "label": "和创作者一起头脑风暴"},
        {"value": "C", "label": "和执行者一起落实细节清单"},
    ]},
    {"id": "q36", "question": "面对新工具，你更可能？", "options": [
        {"value": "S", "label": "组队一起学，互相帮助"},
        {"value": "E", "label": "学完后牵头推广给团队"},
    ]},
    {"id": "q37", "question": "你更愿意做哪种决策？", "options": [
        {"value": "R", "label": "关于实现方式与技术选型"},
        {"value": "A", "label": "关于风格定位与创意方向"},
    ]},
    {"id": "q38", "question": "你更享受哪种解决问题的方式？", "options": [
        {"value": "I", "label": "用理论与模型去解释现象"},
        {"value": "C", "label": "用流程与清单去避免出错"},
    ]},
    {"id": "q39", "question": "你更愿意被记住的贡献是？", "options": [
        {"value": "S", "label": "帮助过很多人成长"},
        {"value": "E", "label": "推动过重要项目落地"},
    ]},
    {"id": "q40", "question": "你更重视的环境特质是？", "options": [
        {"value": "R", "label": "务实、能动手、看重结果"},
        {"value": "I", "label": "理性、爱钻研、鼓励探索"},
    ]},
    {"id": "q41", "question": "你更欣赏的领导风格是？", "options": [
        {"value": "A", "label": "鼓励创意、给团队自由空间"},
        {"value": "C", "label": "规则清晰、按部就班推进"},
    ]},
    {"id": "q42", "question": "你更愿意在哪种团队中工作？", "options": [
        {"value": "S", "label": "氛围温暖、互相关心的团队"},
        {"value": "E", "label": "目标明确、节奏紧凑的团队"},
    ]},
    {"id": "q43", "question": "你更看重的产品价值是？", "options": [
        {"value": "R", "label": "稳定可靠、性能优秀"},
        {"value": "A", "label": "独特审美、令人惊艳"},
    ]},
    {"id": "q44", "question": "你更享受的钻研方式是？", "options": [
        {"value": "I", "label": "啃论文、追原理、做实验"},
        {"value": "C", "label": "梳理文档、整理规范、做沉淀"},
    ]},
    {"id": "q45", "question": "你更愿意在什么场景发挥专长？", "options": [
        {"value": "S", "label": "辅导新人、解答他人困惑"},
        {"value": "E", "label": "对外谈判、争取资源"},
    ]},
    {"id": "q46", "question": "下列哪种状态更让你有动力？", "options": [
        {"value": "R", "label": "看到自己亲手做的东西被用起来"},
        {"value": "I", "label": "想通一个别人没想清楚的难题"},
    ]},
    {"id": "q47", "question": "你更看重工作中哪种自由？", "options": [
        {"value": "A", "label": "表达和创作的自由"},
        {"value": "C", "label": "在清晰规则下稳定推进的自由"},
    ]},
    {"id": "q48", "question": "你更希望被人依赖的是？", "options": [
        {"value": "S", "label": "情绪支持与关系协调"},
        {"value": "E", "label": "目标推进与资源调度"},
    ]},
]

# ----------------------------------------------------------------------
# 6 维度描述（保留与原文件一致，含 directions 推荐方向）
# ----------------------------------------------------------------------
HOLLAND_DESCRIPTIONS = {
    "R": {"name": "实际型", "desc": "喜欢动手操作，注重实践和具体成果", "directions": ["后端开发", "运维工程师", "嵌入式开发", "硬件工程师"]},
    "I": {"name": "研究型", "desc": "善于分析推理，喜欢探索和解决复杂问题", "directions": ["算法工程师", "数据科学家", "科研人员", "安全研究"]},
    "A": {"name": "艺术型", "desc": "富有创造力，追求自由表达和审美", "directions": ["前端开发", "UI/UX设计", "产品经理", "创意设计"]},
    "S": {"name": "社会型", "desc": "乐于助人，善于沟通和协调人际关系", "directions": ["产品经理", "项目管理", "技术顾问", "教育培训"]},
    "E": {"name": "企业型", "desc": "具有领导力，善于说服和推动团队达成目标", "directions": ["产品经理", "创业", "项目管理", "商业分析"]},
    "C": {"name": "常规型", "desc": "做事有条理，注重细节和规则", "directions": ["测试工程师", "数据分析师", "财务技术", "运维自动化"]},
}
