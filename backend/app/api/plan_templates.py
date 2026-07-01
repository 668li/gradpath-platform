"""职业规划模板 — 常见职业路径预设，用户可一键创建。"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/plan-templates", tags=["规划模板"])

# 内置模板（代码定义，不需要数据库表）
TEMPLATES = [
    {
        "id": "backend_dev",
        "name": "大厂后端开发",
        "icon": "🔧",
        "description": "面向计算机专业学生，目标进入一线大厂后端开发岗位",
        "goal_text": "进入一线大厂做后端开发工程师",
        "timeline_months": 12,
        "milestones": [
            {"title": "巩固计算机基础", "description": "数据结构、操作系统、计算机网络、数据库原理", "status": "pending"},
            {"title": "精通一门后端语言", "description": "Java/Go/Python 任选其一，深入理解并发、IO、内存管理", "status": "pending"},
            {"title": "掌握主流框架", "description": "Spring Boot / Gin / Django 等，能独立开发完整项目", "status": "pending"},
            {"title": "数据库与中间件", "description": "MySQL、Redis、Kafka、ElasticSearch 实战", "status": "pending"},
            {"title": "分布式与微服务", "description": "分布式锁、一致性、服务治理、容器化部署", "status": "pending"},
            {"title": "项目经验积累", "description": "2-3 个高质量项目，含至少 1 个高并发场景", "status": "pending"},
            {"title": "面试准备", "description": "八股文、算法题（LeetCode 300+）、系统设计", "status": "pending"},
            {"title": "投递与面试", "description": "暑期实习 → 秋招，多轮面试复盘", "status": "pending"},
        ],
    },
    {
        "id": "frontend_dev",
        "name": "前端开发工程师",
        "icon": "🎨",
        "description": "面向前端方向，涵盖 React/Vue 生态与工程化",
        "goal_text": "成为合格的前端开发工程师",
        "timeline_months": 10,
        "milestones": [
            {"title": "HTML/CSS/JS 基础", "description": "语义化标签、Flex/Grid 布局、ES6+ 特性", "status": "pending"},
            {"title": "TypeScript", "description": "类型系统、泛型、工具类型", "status": "pending"},
            {"title": "React 核心", "description": "Hooks、组件设计、状态管理、性能优化", "status": "pending"},
            {"title": "工程化工具链", "description": "Webpack/Vite、ESLint、CI/CD", "status": "pending"},
            {"title": "全栈拓展", "description": "Next.js SSR/SSG、Node.js BFF 层", "status": "pending"},
            {"title": "项目实战", "description": "2-3 个完整项目，含性能优化案例", "status": "pending"},
            {"title": "面试准备", "description": "JS 原理、浏览器原理、手写代码、框架源码", "status": "pending"},
        ],
    },
    {
        "id": "grad_school",
        "name": "考研上岸",
        "icon": "🎓",
        "description": "计算机考研全流程规划，含择校、初试、复试",
        "goal_text": "成功考研上岸目标院校",
        "timeline_months": 12,
        "milestones": [
            {"title": "择校与专业选择", "description": "评估自身实力，确定目标院校和专业方向", "status": "pending"},
            {"title": "数学一轮复习", "description": "高数、线代、概率论基础过一遍", "status": "pending"},
            {"title": "英语真题精读", "description": "近10年真题逐篇精读，积累词汇", "status": "pending"},
            {"title": "专业课一轮", "description": "数据结构、组成原理、操作系统、计算机网络", "status": "pending"},
            {"title": "数学强化", "description": "专题训练、真题模拟", "status": "pending"},
            {"title": "专业课强化", "description": "真题分析、高频考点突破", "status": "pending"},
            {"title": "政治冲刺", "description": "马原、毛中特、史纲、思修、时政", "status": "pending"},
            {"title": "模拟考试", "description": "全科模拟，查漏补缺", "status": "pending"},
            {"title": "初试", "description": "参加全国统考", "status": "pending"},
            {"title": "复试准备", "description": "机试、面试、英语口语", "status": "pending"},
        ],
    },
    {
        "id": "product_manager",
        "name": "产品经理",
        "icon": "📊",
        "description": "从 0 到 1 成为互联网产品经理",
        "goal_text": "成为合格的互联网产品经理",
        "timeline_months": 8,
        "milestones": [
            {"title": "产品思维建立", "description": "用户研究、需求分析、竞品分析方法论", "status": "pending"},
            {"title": "产品文档能力", "description": "PRD、需求文档、流程图、原型设计", "status": "pending"},
            {"title": "数据分析基础", "description": "SQL、数据埋点、A/B 测试、指标体系", "status": "pending"},
            {"title": "项目协作", "description": "敏捷开发、跨团队沟通、项目推进", "status": "pending"},
            {"title": "产品实战", "description": "独立负责一个功能模块的完整生命周期", "status": "pending"},
            {"title": "面试准备", "description": "产品案例、行业理解、逻辑表达", "status": "pending"},
        ],
    },
    {
        "id": "data_scientist",
        "name": "数据科学家",
        "icon": "🤖",
        "description": "机器学习与数据科学方向",
        "goal_text": "成为数据科学家/算法工程师",
        "timeline_months": 14,
        "milestones": [
            {"title": "数学基础", "description": "线性代数、概率统计、微积分复习", "status": "pending"},
            {"title": "Python 数据栈", "description": "NumPy、Pandas、Matplotlib、Scikit-learn", "status": "pending"},
            {"title": "机器学习经典", "description": "监督/无监督学习、特征工程、模型评估", "status": "pending"},
            {"title": "深度学习", "description": "PyTorch/TensorFlow、CNN、RNN、Transformer", "status": "pending"},
            {"title": "项目实战", "description": "Kaggle 竞赛 + 1-2 个端到端项目", "status": "pending"},
            {"title": "论文阅读", "description": "跟进顶会最新论文，复现经典模型", "status": "pending"},
            {"title": "面试准备", "description": "算法题、ML 八股、系统设计、论文讲解", "status": "pending"},
        ],
    },
    {
        "id": "abroad_study",
        "name": "留学申请",
        "icon": "✈️",
        "description": "CS 留学申请全流程规划",
        "goal_text": "成功申请海外名校 CS 硕士项目",
        "timeline_months": 18,
        "milestones": [
            {"title": "标化考试", "description": "TOEFL 100+ / IELTS 7.0+、GRE 320+", "status": "pending"},
            {"title": "GPA 维护", "description": "保持专业课 GPA 3.5+", "status": "pending"},
            {"title": "科研经历", "description": "进实验室、发论文或参与导师项目", "status": "pending"},
            {"title": "实习经历", "description": "1-2 段大厂或知名企业实习", "status": "pending"},
            {"title": "选校定位", "description": "冲刺/匹配/保底三档选校方案", "status": "pending"},
            {"title": "文书撰写", "description": "PS、CV、推荐信", "status": "pending"},
            {"title": "网申与面试", "description": "提交申请、准备面试", "status": "pending"},
        ],
    },
]


@router.get("")
def list_templates():
    """列出所有规划模板。"""
    return TEMPLATES


@router.get("/{template_id}")
def get_template(template_id: str):
    """获取单个模板详情。"""
    for t in TEMPLATES:
        if t["id"] == template_id:
            return t
    from fastapi import HTTPException, status
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
