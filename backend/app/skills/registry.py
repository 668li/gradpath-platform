"""Skill 注册表 — 管理项目专用 skill 的元信息。

每个 skill 包含：名称、描述、触发词、使用场景、能力边界。
前端通过 API 查询注册表，展示可用 skill 列表。
"""
from dataclasses import dataclass, field
from typing import Optional

from app.skills.base import BaseSkill


@dataclass
class SkillInfo:
    """Skill 元信息。"""

    code: str
    name: str
    display_name: str
    description: str
    trigger_words: list[str]
    use_cases: list[str]
    capabilities: list[str]
    limitations: list[str]
    category: str  # builder / advisor / generator
    icon: str = "code"
    is_active: bool = True
    skill_path: Optional[str] = None


# ===== 项目专用 Skill =====
_SKILLS: list[SkillInfo] = [
    SkillInfo(
        code="api-endpoint-builder",
        name="api-endpoint-builder",
        display_name="API 端点构建器",
        description="快速生成 FastAPI CRUD 模块（Model + Schema + Router + 前端类型 + API 封装），输入实体名+字段定义即可生成完整模块。",
        trigger_words=["新增模块", "生成CRUD", "创建接口", "快速建表"],
        use_cases=[
            "新增一个数据模块（如院校对比、学习计划、模考记录）",
            "快速搭建 MVP 功能",
            "标准化 API 结构",
        ],
        capabilities=[
            "自动生成 SQLAlchemy Model",
            "自动生成 Pydantic Schema",
            "自动生成 FastAPI CRUD 路由",
            "自动生成前端 TypeScript 类型",
            "自动生成前端 API 封装函数",
        ],
        limitations=["复杂业务逻辑需手动设计", "不用于第三方 API 集成"],
        category="builder",
        icon="code",
        skill_path="d:\\职业规划\\skills\\api-endpoint-builder",
    ),
    SkillInfo(
        code="community-content-generator",
        name="community-content-generator",
        display_name="社区内容生成器",
        description="批量生成考研社区内容（经验贴 + 问答），自动打标签、分配分类、模拟浏览/点赞数，保证数据一致性。",
        trigger_words=["生成社区内容", "补充经验贴", "批量生成问答", "社区补量"],
        use_cases=[
            "社区内容不足，需要快速补量",
            "按特定主题批量生成内容",
            "生成符合数据模型的种子数据",
        ],
        capabilities=[
            "按院校/专业/阶段生成经验贴",
            "批量生成 Q&A 问答",
            "自动打标签和分类",
            "模拟浏览/点赞数",
            "保证数据一致性",
        ],
        limitations=["不用于单条内容创作", "不用于用户 UGC 内容"],
        category="generator",
        icon="users",
        skill_path="d:\\职业规划\\skills\\community-content-generator",
    ),
    SkillInfo(
        code="data-crawler-builder",
        name="data-crawler-builder",
        display_name="数据爬虫构建器",
        description="生成考研数据爬虫脚本，基于 BaseCrawler 模式，支持研招网、导师评价网等数据源，内置反爬策略。",
        trigger_words=["写个爬虫", "抓取网站", "新增数据源", "爬取数据"],
        use_cases=[
            "需要新增数据源（如某个院校的导师信息）",
            "现有爬虫覆盖不足，需要扩展",
            "从特定网站批量采集数据",
        ],
        capabilities=[
            "生成符合项目架构的爬虫",
            "自动去重入库",
            "内置反爬策略（UA轮换、请求间隔、重试）",
            "支持研招网、导师评价网等数据源",
        ],
        limitations=["不用于通用爬虫", "不用于实时数据采集", "不破解反爬机制"],
        category="builder",
        icon="database",
        skill_path="d:\\职业规划\\skills\\data-crawler-builder",
    ),
    SkillInfo(
        code="frontend-page-builder",
        name="frontend-page-builder",
        display_name="前端页面构建器",
        description="快速生成前端页面（列表页/详情页/表单页/仪表板），内置空状态、加载骨架、错误边界、分页等通用逻辑。",
        trigger_words=["新建页面", "生成列表页", "做个详情页", "加个表单页"],
        use_cases=[
            "需要新增一个功能页面",
            "快速搭建 MVP 界面",
            "标准化页面结构",
        ],
        capabilities=[
            "生成列表页（含搜索/筛选/分页）",
            "生成详情页",
            "生成表单页（含验证）",
            "生成仪表板",
            "内置空状态、加载骨架、错误边界",
        ],
        limitations=["不用于复杂交互逻辑", "不用于第三方组件集成"],
        category="builder",
        icon="layout",
        skill_path="d:\\职业规划\\skills\\frontend-page-builder",
    ),
    SkillInfo(
        code="kaoyan-advisor",
        name="kaoyan-advisor",
        display_name="考研智能顾问",
        description="扮演资深考研规划师，根据用户背景给出个性化择校建议，解读分数线趋势、报录比、调剂信息，内置暗知识体系。",
        trigger_words=["帮我选学校", "我能考什么", "择校建议", "考研规划"],
        use_cases=[
            "用户需要择校建议",
            "解读分数线和报录比",
            "评估竞争力等级",
            "生成冲/稳/保三档推荐",
        ],
        capabilities=[
            "收集用户背景（本科层次/GPA/目标）",
            "评估竞争力等级（S/A/B/C/D）",
            "生成冲/稳/保三档院校推荐",
            "解读分数线趋势",
            "主动提醒暗知识和常见误区",
        ],
        limitations=["不用于具体科目复习指导", "不用于心理疏导"],
        category="advisor",
        icon="graduation-cap",
        skill_path="d:\\职业规划\\skills\\kaoyan-advisor",
    ),
    SkillInfo(
        code="seed-data-generator",
        name="seed-data-generator",
        display_name="种子数据生成器",
        description="生成种子数据脚本，支持导师/院校/分数线/经验贴/问答等多种实体，保证数据一致性，支持批量注入和幂等执行。",
        trigger_words=["生成种子数据", "补充数据", "注入测试数据", "数据补量"],
        use_cases=[
            "新项目初始化，需要测试数据",
            "数据量不足，需要快速补量",
            "演示/测试环境搭建",
        ],
        capabilities=[
            "生成导师数据（含研究方向/联系方式）",
            "生成院校情报数据",
            "生成分数线数据",
            "生成经验贴和问答",
            "保证数据一致性（导师-院校-专业关联正确）",
            "支持幂等执行",
        ],
        limitations=["不用于真实数据爬取", "不用于用户 UGC"],
        category="generator",
        icon="seed",
        skill_path="d:\\职业规划\\skills\\seed-data-generator",
    ),
    SkillInfo(
        code="career_planning",
        name="career_planning",
        display_name="职业规划",
        description="根据用户背景制定职业规划，生成里程碑和时间线。",
        trigger_words=["职业规划", "制定计划", "职业发展", "规划", "路径", "怎么进", "如何准备", "目标", "进大厂", "career plan", "career"],
        use_cases=["用户需要职业规划", "生成里程碑和时间线"],
        capabilities=["分析用户背景", "生成职业规划", "生成里程碑"],
        limitations=["不用于具体简历优化"],
        category="advisor",
        icon="target",
    ),
    SkillInfo(
        code="grad_school_planning",
        name="grad_school_planning",
        display_name="考研规划",
        description="根据用户背景制定考研规划，生成择校建议和备考计划。",
        trigger_words=["考研规划", "择校建议", "备考计划", "考研", "保研", "研究生", "读研", "学硕", "专硕", "硕士"],
        use_cases=["用户需要考研规划", "生成择校建议"],
        capabilities=["分析用户背景", "生成考研规划", "生成择校建议"],
        limitations=["不用于具体科目复习指导"],
        category="advisor",
        icon="graduation-cap",
    ),
    SkillInfo(
        code="career_transition",
        name="career_transition",
        display_name="职业转型",
        description="帮助用户规划职业转型路径，分析转行可行性。",
        trigger_words=["职业转型", "转行", "换工作", "转行到"],
        use_cases=["用户需要转行建议", "分析转行可行性"],
        capabilities=["分析转行可行性", "生成转型路径", "评估技能差距"],
        limitations=["不用于具体面试指导"],
        category="advisor",
        icon="refresh-cw",
    ),
    SkillInfo(
        code="resume_diagnosis",
        name="resume_diagnosis",
        display_name="简历诊断",
        description="分析用户简历，提供优化建议。",
        trigger_words=["简历诊断", "优化简历", "简历分析"],
        use_cases=["用户需要简历优化建议", "分析简历质量"],
        capabilities=["分析简历内容", "提供优化建议", "评估简历质量"],
        limitations=["不用于具体面试指导"],
        category="advisor",
        icon="file-text",
    ),
    SkillInfo(
        code="industry_analyzer",
        name="industry_analyzer",
        display_name="行业分析",
        description="分析行业趋势和就业前景，提供行业洞察。",
        trigger_words=["行业分析", "行业趋势", "行业前景", "industry", "就业分析"],
        use_cases=["用户需要行业分析", "了解行业趋势", "评估行业前景"],
        capabilities=["分析行业趋势", "评估就业前景", "提供行业洞察", "对比行业差异"],
        limitations=["不用于具体职业规划", "不用于薪资谈判"],
        category="advisor",
        icon="bar-chart",
    ),
    SkillInfo(
        code="interview_simulation",
        name="interview_simulation",
        display_name="面试模拟",
        description="模拟面试场景，生成针对性面试题与答题思路。",
        trigger_words=["面试模拟", "模拟面试", "面试准备"],
        use_cases=["用户需要面试准备", "模拟面试场景"],
        capabilities=["生成面试题", "提供答题思路", "模拟面试场景"],
        limitations=["不用于真实面试"],
        category="advisor",
        icon="mic",
    ),
    SkillInfo(
        code="salary_negotiation",
        name="salary_negotiation",
        display_name="薪资谈判助手",
        description="帮助用户准备薪资谈判策略，分析市场行情，制定谈判方案",
        trigger_words=["薪资谈判", "谈薪", "工资谈判", "薪资", "salary", "negotiation"],
        use_cases=["用户需要薪资谈判建议", "分析市场行情", "制定谈判策略"],
        capabilities=["分析市场薪资行情", "制定谈判策略", "评估谈判风险", "提供非薪资福利建议"],
        limitations=["不用于具体劳动合同审查", "不用于劳动法咨询"],
        category="advisor",
        icon="dollar-sign",
    ),
    SkillInfo(
        code="learning_plan_generator",
        name="learning_plan_generator",
        display_name="学习计划生成器",
        description="根据用户目标生成详细的学习计划和时间表",
        trigger_words=["学习计划", "制定计划", "学习安排", "备考计划"],
        use_cases=["用户需要制定学习计划", "生成阶段性学习安排", "制定备考时间表"],
        capabilities=["生成分阶段学习计划", "设定学习里程碑", "推荐学习资源", "规划每日学习时长"],
        limitations=["不用于具体学科知识讲解", "不用于心理疏导"],
        category="advisor",
        icon="calendar",
    ),
    SkillInfo(
        code="interview_coach",
        name="interview_coach",
        display_name="面试教练",
        description="提供面试技巧指导、常见问题解析、面试心态调整建议",
        trigger_words=["面试技巧", "面试准备", "面试心态", "面试指导", "interview coach"],
        use_cases=["用户需要面试技巧指导", "面试心态调整", "面试常见问题解析"],
        capabilities=["提供面试技巧指导", "解析常见面试问题", "调整面试心态", "生成面试准备清单"],
        limitations=["不用于具体模拟面试", "不用于真实面试"],
        category="advisor",
        icon="message-circle",
    ),
    SkillInfo(
        code="resume_optimizer",
        name="resume_optimizer",
        display_name="简历优化器",
        description="分析用户简历内容，提供优化建议和改进方案",
        trigger_words=["简历优化", "简历分析", "优化简历", "简历检查", "resume"],
        use_cases=["用户需要简历优化", "分析简历质量并改进"],
        capabilities=["分析简历内容", "提供优化建议", "评估简历质量", "生成改进方案"],
        limitations=["不用于具体面试指导", "不用于求职信撰写"],
        category="advisor",
        icon="file-text",
    ),
    SkillInfo(
        code="user_referral",
        name="user_referral",
        display_name="用户推荐助手",
        description="帮助用户生成推荐链接，追踪推荐效果，提供推荐奖励",
        trigger_words=["推荐朋友", "邀请好友", "推荐链接", "user referral", "邀请注册"],
        use_cases=["用户需要生成推荐链接", "追踪推荐效果", "了解推荐奖励"],
        capabilities=["生成推荐码和推荐链接", "提供分层推荐奖励机制", "生成多平台分享文案", "追踪推荐效果数据"],
        limitations=["不用于真实推荐系统后端", "不用于支付结算"],
        category="generator",
        icon="users",
    ),
    SkillInfo(
        code="salary_benchmark",
        name="salary_benchmark",
        display_name="薪资基准分析",
        description="分析用户薪资数据，生成行业/岗位/地区的薪资基准报告",
        trigger_words=["薪资基准", "薪资报告", "工资水平", "salary benchmark", "薪资分析"],
        use_cases=["用户需要薪资基准分析", "了解行业薪资水平", "对比薪资数据"],
        capabilities=["分析薪资分布", "评估薪资趋势", "提供薪资建议", "对比薪资数据"],
        limitations=["不用于具体薪资谈判", "不用于劳动合同审查"],
        category="advisor",
        icon="trending-up",
    ),
    SkillInfo(
        code="career_path_mapper",
        name="career_path_mapper",
        display_name="职业路径规划器",
        description="根据用户背景和目标，生成详细的职业发展路径图和阶段性目标",
        trigger_words=["职业路径", "发展路径", "职业规划图", "career path", "职业发展"],
        use_cases=["用户需要职业发展路径规划", "生成阶段性职业目标"],
        capabilities=["生成职业路径图", "制定阶段性目标", "规划技能学习路线", "分析潜在障碍"],
        limitations=["不用于具体面试指导", "不用于简历优化"],
        category="advisor",
        icon="map",
    ),
    SkillInfo(
        code="company_review",
        name="company_review",
        display_name="公司评价分析",
        description="分析用户对公司的评价，提取关键信息，帮助其他用户了解公司真实情况",
        trigger_words=["公司评价", "公司口碑", "公司怎么样", "company review", "工作体验"],
        use_cases=["用户需要了解公司情况", "分析公司口碑", "评估工作体验"],
        capabilities=["分析工作文化", "评估工作生活平衡", "分析薪资福利", "评估管理风格", "分析成长机会"],
        limitations=["不用于具体面试指导", "不用于薪资谈判"],
        category="advisor",
        icon="building",
    ),
    SkillInfo(
        code="default",
        name="default",
        display_name="默认职业咨询",
        description="通用职业规划咨询，回答各类职业发展问题。",
        trigger_words=[],
        use_cases=["用户需要职业咨询"],
        capabilities=["回答职业发展问题", "提供职业建议"],
        limitations=["不用于具体简历优化"],
        category="advisor",
        icon="message-circle",
    ),
]


def list_skills() -> list[dict]:
    """列出所有 skill，返回字典列表。"""
    return [
        {
            "code": s.code,
            "name": s.name,
            "display_name": s.display_name,
            "description": s.description,
            "trigger_words": s.trigger_words,
            "use_cases": s.use_cases,
            "capabilities": s.capabilities,
            "limitations": s.limitations,
            "category": s.category,
            "icon": s.icon,
            "is_active": s.is_active,
        }
        for s in _SKILLS
    ]


def get_skill(name: str) -> dict | None:
    """按名称获取 skill 信息。"""
    for s in _SKILLS:
        if s.name == name:
            return {
                "name": s.name,
                "display_name": s.display_name,
                "description": s.description,
                "trigger_words": s.trigger_words,
                "use_cases": s.use_cases,
                "capabilities": s.capabilities,
                "limitations": s.limitations,
                "category": s.category,
                "is_active": s.is_active,
            }
    return None


def get_skills_by_category(category: str) -> list[dict]:
    """按分类获取 skill 列表。"""
    return [
        {
            "name": s.name,
            "display_name": s.display_name,
            "description": s.description,
            "trigger_words": s.trigger_words,
            "use_cases": s.use_cases,
            "capabilities": s.capabilities,
            "limitations": s.limitations,
            "category": s.category,
            "is_active": s.is_active,
        }
        for s in _SKILLS
        if s.category == category
    ]


def find_skill(content: str, context: dict | None = None) -> dict | None:
    """根据消息内容匹配最适合的 skill（基于触发词匹配）。

    Args:
        content: 用户消息内容
        context: 对话上下文（含 conversation、history 等）

    Returns:
        匹配的 skill 字典，无匹配返回 None
    """
    if not content:
        return None

    content_lower = content.lower()
    best_match = None
    best_score = 0

    for s in _SKILLS:
        # 计算触发词匹配分数
        score = 0
        for trigger in s.trigger_words:
            if trigger in content_lower:
                score += len(trigger)  # 长触发词权重更高

        if score > best_score:
            best_score = score
            best_match = {
                "name": s.name,
                "display_name": s.display_name,
                "description": s.description,
                "trigger_words": s.trigger_words,
                "use_cases": s.use_cases,
                "capabilities": s.capabilities,
                "limitations": s.limitations,
                "category": s.category,
                "is_active": s.is_active,
            }

    return best_match if best_score > 0 else None


# ===== Skill 实例解析 =====

# Skill name → BaseSkill class mapping
_SKILL_CLASSES: dict[str, type] = {}


def _load_skill_classes():
    """延迟加载所有 BaseSkill 子类。"""
    global _SKILL_CLASSES
    if _SKILL_CLASSES:
        return
    
    from app.skills.default_skill import DefaultSkill
    from app.skills.interview_simulation import InterviewSimulationSkill
    from app.skills.career_planning import CareerPlanningSkill
    from app.skills.career_transition import CareerTransitionSkill
    from app.skills.grad_school_planning import GradSchoolPlanningSkill
    from app.skills.resume_diagnosis import ResumeDiagnosisSkill
    from app.skills.industry_analyzer import IndustryAnalyzerSkill
    from app.skills.salary_negotiation import SalaryNegotiationSkill
    from app.skills.salary_benchmark import SalaryBenchmarkSkill
    from app.skills.learning_plan_generator import LearningPlanGeneratorSkill
    from app.skills.interview_coach import InterviewCoachSkill
    from app.skills.resume_optimizer import ResumeOptimizerSkill
    from app.skills.career_path_mapper import CareerPathMapperSkill
    from app.skills.company_review import CompanyReviewSkill
    from app.skills.user_referral import UserReferralSkill
    
    for cls in [DefaultSkill, InterviewSimulationSkill, CareerPlanningSkill,
                CareerTransitionSkill, GradSchoolPlanningSkill, ResumeDiagnosisSkill,
                IndustryAnalyzerSkill, SalaryNegotiationSkill, SalaryBenchmarkSkill,
                LearningPlanGeneratorSkill, InterviewCoachSkill, ResumeOptimizerSkill,
                CareerPathMapperSkill, CompanyReviewSkill, UserReferralSkill]:
        _SKILL_CLASSES[cls.code] = cls


def get_skill_instance(name: str) -> BaseSkill | None:
    """按名称获取 BaseSkill 实例。"""
    _load_skill_classes()
    
    # 先尝试精确匹配
    if name in _SKILL_CLASSES:
        return _SKILL_CLASSES[name]()
    
    # 尝试从 SkillInfo 匹配
    for s in _SKILLS:
        if s.name == name and s.name in _SKILL_CLASSES:
            return _SKILL_CLASSES[s.name]()
    
    return None


def find_skill_instance(content: str, context: dict | None = None) -> BaseSkill | None:
    """根据消息内容和对话上下文匹配最适合的 BaseSkill 实例。
    
    支持上下文感知：如果对话历史中出现过相关关键词，给予加分。
    无匹配返回 DefaultSkill。
    """
    _load_skill_classes()
    
    if not content:
        return _SKILL_CLASSES.get("default", lambda: None)()
    
    content_lower = content.lower()
    best_match = None
    best_score = 0
    
    # 提取对话历史内容用于上下文匹配
    history_content = ""
    if context and "history" in context:
        for msg in context["history"]:
            if isinstance(msg, dict):
                history_content += " " + msg.get("content", "").lower()
            elif isinstance(msg, str):
                history_content += " " + msg.lower()
    
    for s in _SKILLS:
        if s.code == "default":
            continue  # skip default in scoring
        score = 0
        
        # 当前消息匹配
        for trigger in s.trigger_words:
            if trigger in content_lower:
                score += len(trigger)
        
        # 上下文加成：对话历史中出现过相关关键词
        if history_content:
            for trigger in s.trigger_words:
                if trigger in history_content:
                    score += len(trigger) * 0.3  # 上下文加成30%
        
        if score > best_score and s.name in _SKILL_CLASSES:
            best_score = score
            best_match = _SKILL_CLASSES[s.name]()
    
    return best_match if best_match else _SKILL_CLASSES.get("default", lambda: None)()
