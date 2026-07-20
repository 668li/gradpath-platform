# backend/app/services/assessment_data/disc_questions.py
"""DISC 行为风格测评题库。

4 个维度：
- D 支配型 (Dominance)          — 直接、果断、目标导向
- I 影响型 (Influence)          — 热情、社交、表达力强
- S 稳健型 (Steadiness)         — 耐心、支持、稳定
- C 谨慎型 (Conscientiousness)  — 精确、分析、注重细节

共 24 题，每题 4 个选项分别对应 D / I / S / C。
标准 DISC 做法是：用户从每题 4 个选项中选出"最符合"与"最不符合"自己的一项。
为兼容统一 answers: dict[str, str] 的 schema，本实现将"最符合"的字母存入 answers：
    answers = {"disc_q1": "D", "disc_q2": "I", ...}
计算函数统计 D/I/S/C 维度出现次数，取最高的作为 result_code。
"""

# ----------------------------------------------------------------------
# 题目（每题 4 个选项 value 分别为 D/I/S/C，顺序按 D-I-S-C 固定）
# ----------------------------------------------------------------------
DISC_QUESTIONS = [
    {"id": "disc_q1", "question": "面对一个新任务，你最自然的反应是？", "options": [
        {"value": "D", "label": "直接定目标，立刻动手推进"},
        {"value": "I", "label": "找大家聊聊，把人凑齐再开干"},
        {"value": "S", "label": "先了解清楚节奏，配合团队推进"},
        {"value": "C", "label": "先把流程和细节梳理清楚再开始"},
    ]},
    {"id": "disc_q2", "question": "在团队讨论中，你最常做的是？", "options": [
        {"value": "D", "label": "推动结论，避免空谈"},
        {"value": "I", "label": "活跃气氛，激发想法"},
        {"value": "S", "label": "倾听他人，调和分歧"},
        {"value": "C", "label": "记录要点，核对事实"},
    ]},
    {"id": "disc_q3", "question": "面对冲突，你的第一反应是？", "options": [
        {"value": "D", "label": "正面交锋，亮明立场"},
        {"value": "I", "label": "用沟通化解，缓和情绪"},
        {"value": "S", "label": "尽量退让，维护关系"},
        {"value": "C", "label": "用事实和规则厘清是非"},
    ]},
    {"id": "disc_q4", "question": "你的工作节奏更接近？", "options": [
        {"value": "D", "label": "快、猛、追求突破"},
        {"value": "I", "label": "灵活多变、跟随热情"},
        {"value": "S", "label": "稳定持续、按部就班"},
        {"value": "C", "label": "严谨细致、追求准确"},
    ]},
    {"id": "disc_q5", "question": "面对一项决策，你最看重？", "options": [
        {"value": "D", "label": "结果与效率"},
        {"value": "I", "label": "大家的认同感"},
        {"value": "S", "label": "团队是否适应"},
        {"value": "C", "label": "依据是否充分"},
    ]},
    {"id": "disc_q6", "question": "在压力下，你更可能？", "options": [
        {"value": "D", "label": "更急更猛，目标驱动"},
        {"value": "I", "label": "找人倾诉，转移注意"},
        {"value": "S", "label": "默默承担，维持稳定"},
        {"value": "C", "label": "埋头分析，寻找方案"},
    ]},
    {"id": "disc_q7", "question": "你最喜欢的领导风格是？", "options": [
        {"value": "D", "label": "授权放权，看结果"},
        {"value": "I", "label": "鼓舞激励，氛围好"},
        {"value": "S", "label": "稳定支持，节奏稳"},
        {"value": "C", "label": "标准清晰，讲规则"},
    ]},
    {"id": "disc_q8", "question": "做汇报时你更倾向于？", "options": [
        {"value": "D", "label": "直接给结论和行动项"},
        {"value": "I", "label": "讲生动的故事和案例"},
        {"value": "S", "label": "把过程和团队贡献讲清楚"},
        {"value": "C", "label": "用数据和图表支撑结论"},
    ]},
    {"id": "disc_q9", "question": "面对一项改变，你的态度更接近？", "options": [
        {"value": "D", "label": "迫不及待想推动"},
        {"value": "I", "label": "觉得新鲜有趣，愿意试"},
        {"value": "S", "label": "先观察影响，再适应"},
        {"value": "C", "label": "评估风险，再决定"},
    ]},
    {"id": "disc_q10", "question": "你最不喜欢的工作场景是？", "options": [
        {"value": "D", "label": "拖拖拉拉、议而不决"},
        {"value": "I", "label": "气氛冷清、没有互动"},
        {"value": "S", "label": "变化太快、人心惶惶"},
        {"value": "C", "label": "规则不清、糊里糊涂"},
    ]},
    {"id": "disc_q11", "question": "你最希望被同事评价为？", "options": [
        {"value": "D", "label": "有魄力、能扛事"},
        {"value": "I", "label": "热情、好相处"},
        {"value": "S", "label": "靠谱、可信赖"},
        {"value": "C", "label": "专业、严谨"},
    ]},
    {"id": "disc_q12", "question": "面对一个复杂问题，你倾向于？", "options": [
        {"value": "D", "label": "先做决定，再调整"},
        {"value": "I", "label": "拉人讨论，碰撞想法"},
        {"value": "S", "label": "稳妥推进，逐步化解"},
        {"value": "C", "label": "拆解要素，逐项分析"},
    ]},
    {"id": "disc_q13", "question": "你最看重的团队特质是？", "options": [
        {"value": "D", "label": "战斗力强、能拿结果"},
        {"value": "I", "label": "氛围融洽、互动活跃"},
        {"value": "S", "label": "稳定协作、互相信任"},
        {"value": "C", "label": "标准清晰、流程规范"},
    ]},
    {"id": "disc_q14", "question": "你最自然的工作启动方式是？", "options": [
        {"value": "D", "label": "定目标、分任务、马上开干"},
        {"value": "I", "label": "约大家开会、动员气氛"},
        {"value": "S", "label": "确认分工、平稳启动"},
        {"value": "C", "label": "列出清单、制定标准"},
    ]},
    {"id": "disc_q15", "question": "面对批评，你的反应更接近？", "options": [
        {"value": "D", "label": "据理力争，捍卫立场"},
        {"value": "I", "label": "先回应情绪，再说事情"},
        {"value": "S", "label": "默默接受，避免冲突"},
        {"value": "C", "label": "核对事实，澄清对错"},
    ]},
    {"id": "disc_q16", "question": "你最享受的成就感来自？", "options": [
        {"value": "D", "label": "拿下挑战性目标"},
        {"value": "I", "label": "获得大家的认可与喜爱"},
        {"value": "S", "label": "团队稳定、大家都好"},
        {"value": "C", "label": "把事情做对、做到位"},
    ]},
    {"id": "disc_q17", "question": "你处理信息时更倾向于？", "options": [
        {"value": "D", "label": "只看关键结论"},
        {"value": "I", "label": "听人讲比看报告更高效"},
        {"value": "S", "label": "完整了解背景与上下文"},
        {"value": "C", "label": "仔细核对每一条数据"},
    ]},
    {"id": "disc_q18", "question": "面对一项新规，你最在意？", "options": [
        {"value": "D", "label": "是否影响效率与结果"},
        {"value": "I", "label": "是否影响大家的关系和氛围"},
        {"value": "S", "label": "是否平稳、能否落地"},
        {"value": "C", "label": "是否合理、是否可量化"},
    ]},
    {"id": "disc_q19", "question": "你最常用的沟通方式是？", "options": [
        {"value": "D", "label": "简短直接、结果导向"},
        {"value": "I", "label": "热情生动、富于表情"},
        {"value": "S", "label": "温和耐心、注重倾听"},
        {"value": "C", "label": "条理清晰、数据支撑"},
    ]},
    {"id": "disc_q20", "question": "面对一个新成员加入团队，你的反应是？", "options": [
        {"value": "D", "label": "直接给他派任务、看产出"},
        {"value": "I", "label": "热情欢迎、主动介绍大家"},
        {"value": "S", "label": "帮他慢慢融入、关心适应"},
        {"value": "C", "label": "把规则与流程交代清楚"},
    ]},
    {"id": "disc_q21", "question": "你最看重的执行力体现在？", "options": [
        {"value": "D", "label": "速度与突破"},
        {"value": "I", "label": "号召力与感染力"},
        {"value": "S", "label": "持续与稳定"},
        {"value": "C", "label": "准确与规范"},
    ]},
    {"id": "disc_q22", "question": "你最不擅长的场景是？", "options": [
        {"value": "D", "label": "需要长期耐心、慢工出细活"},
        {"value": "I", "label": "长期独自埋头、缺少互动"},
        {"value": "S", "label": "高频冲突、需要正面交锋"},
        {"value": "C", "label": "高度模糊、需要即兴发挥"},
    ]},
    {"id": "disc_q23", "question": "你认为好项目的标志是？", "options": [
        {"value": "D", "label": "目标达成、突破常规"},
        {"value": "I", "label": "团队愉快、氛围热烈"},
        {"value": "S", "label": "节奏稳定、协作顺畅"},
        {"value": "C", "label": "质量过硬、零失误"},
    ]},
    {"id": "disc_q24", "question": "你最希望在工作中获得？", "options": [
        {"value": "D", "label": "掌控权与成就感"},
        {"value": "I", "label": "认可、关注与人脉"},
        {"value": "S", "label": "安全感与归属感"},
        {"value": "C", "label": "专业感与确定性"},
    ]},
]


# ----------------------------------------------------------------------
# 4 种 DISC 类型描述
# ----------------------------------------------------------------------
DISC_TYPES = {
    "D": {
        "name": "支配型 (Dominance)",
        "description": "目标导向、果断直接、敢于挑战，喜欢掌控局面并推动结果达成。节奏快、效率高，但需注意倾听他人与控制脾气。",
        "workplace_tips": [
            "在拍板前多倾听一线信息，避免过早下结论",
            "对节奏较慢的同事多留缓冲时间",
            "把'为什么做'讲清楚，而不只是'必须做'",
            "学会授权而非亲力亲为，关注团队成长",
        ],
        "careers": ["创业", "项目管理", "销售总监", "战略咨询", "投资管理", "运营负责人"],
    },
    "I": {
        "name": "影响型 (Influence)",
        "description": "热情、善于表达、人际感染力强，乐于与人互动并影响他人。氛围活跃、人脉广，但需关注细节与执行落地。",
        "workplace_tips": [
            "用清单和日程管理把热情转化为持续产出",
            "在关键决策上多核对事实与数据",
            "学会独处与深度思考，平衡社交消耗",
            "把'关系好'转化为'目标对齐'，避免被情绪牵着走",
        ],
        "careers": ["市场运营", "品牌营销", "公关", "销售", "内容创作", "活动策划"],
    },
    "S": {
        "name": "稳健型 (Steadiness)",
        "description": "耐心、可靠、注重和谐与协作，是团队的稳定器。执行力持续、忠诚度高，但面对快速变化与冲突时需要更多支持。",
        "workplace_tips": [
            "主动表达自己的需求与边界，避免过度迁就",
            "在变化中提前为自己留出适应时间",
            "敢于在关键场合表态，不要总做'和事佬'",
            "建立个人节奏，避免被他人事务打乱",
        ],
        "careers": ["人力资源", "客户成功", "教育培训", "项目管理", "运维工程师", "医疗护理"],
    },
    "C": {
        "name": "谨慎型 (Conscientiousness)",
        "description": "严谨、精确、注重规则与质量，善于分析问题并制定标准。专业可靠，但在模糊与高压下需要适度灵活。",
        "workplace_tips": [
            "为'差不多就行'的场景留出弹性，避免过度完美主义",
            "学会在信息不全时做出可调整的判断",
            "多关注人本身，而不只是流程与数据",
            "把'我看到了风险'转化为'这是我的建议'",
        ],
        "careers": ["测试工程师", "财务", "审计", "法务合规", "风控", "数据分析师"],
    },
}
