# 三中心 + 数据真实性接入层（系统设计 §4.2 契约落库，MVP 方案 C）
from app.models.action_center import ActionCheckin, ActionStreak, ActionWeight, DailyAction
from app.models.assessment import Assessment
from app.models.block_relation import BlockRelation
from app.models.bookmark import Bookmark, BookmarkTargetType
from app.models.career_event import CareerEvent, EventType
from app.models.career_intel import CareerDarkKnowledge, CareerPositioning, CompanyIntel
from app.models.career_plan import CareerPlan
from app.models.career_profile import CareerProfile
from app.models.civil_service_intel import (
    CivilServiceDarkKnowledge,
    CivilServicePositioning,
    PostIntel,
)
from app.models.comment import Comment
from app.models.community_rating import CommunityRating
from app.models.community_report import CommunityReport, DestinationType, SalaryRange
from app.models.company import Company, CompanySize
from app.models.company_review import CompanyReview
from app.models.conversation import Conversation, Message
from app.models.crawler_run import CrawlerRun
from app.models.dark_knowledge_push import DarkKnowledgePushLog, PushFeedback
from app.models.data_source import DataSource
from app.models.dataset_info import DatasetInfo
from app.models.decision_analysis import DecisionAnalysis
from app.models.decision_review import DecisionReviewQueue, ReviewStatus
from app.models.destination_decision import DecisionStatus, DestinationDecision
from app.models.employment_data import Degree, EmploymentData
from app.models.event import Event, Feedback
from app.models.experience_post import ExperiencePost
from app.models.failure_case import FailureCase

# 家庭对话脚手架
from app.models.family_dialogue import FamilyDialogueSession
from app.models.grad_intel import (
    DarkKnowledge,
    GradAdjustmentInfo,
    GradSchoolIntel,
    GradScorelineRecord,
    GradYanzhaoProgram,
    SelfPositioning,
)
from app.models.growth_center import GrowthArchive, GrowthTrajectory
from app.models.growth_insight import GrowthInsight
from app.models.gwy_position import GwyPosition
from app.models.gwy_province_position import GwyProvincePosition
from app.models.gwy_score_line import GwyScoreLine
from app.models.ingestion import (
    DataFreshness,
    DataSourceMeta,
    ExternalResearchItem,
    ReviewQueueItem,
)
from app.models.interview_report import InterviewReport, InterviewResult
from app.models.kaoyan_news import KaoyanNews
from app.models.knowledge_article import KnowledgeArticle
from app.models.life_design import LifeDesignSprint, WeeklyReview
from app.models.life_wheel import LifeWheelSnapshot
from app.models.market_data import MarketData
from app.models.mentor import Mentor
from app.models.mentor_review import MentorReview

# 7天微行动
from app.models.micro_action import MicroActionPlan, MicroActionTask
from app.models.milestone_log import MilestoneLog
from app.models.notification import Notification, NotificationType
from app.models.onboarding import OnboardingStatus, UserOnboarding
from app.models.outcome_report import AdmissionPath, OutcomeReport, OutcomeType

# 多路径 What-If 对比
from app.models.path_comparison import PathComparison

# 路径冲突调解
from app.models.path_conflict import PathConflictResolution
from app.models.pipeline_enums import ContentType, SourceType
from app.models.post import Post, PostTopicType
from app.models.proactive_insight import ProactiveInsight
from app.models.qa import QA
from app.models.qa_answer import QAAnswer

# 质量分反馈闭环（Phase I）
from app.models.quality_feedback import (
    QualityFeedback,
    QualityFeedbackTargetType,
    QualityFeedbackType,
)

# 社区治理
from app.models.report import Report, ReportStatus, ReportTargetType
from app.models.report_record import ParseStatus, ReportRecord
from app.models.retrospective import PeriodType, Retrospective
from app.models.review_record import ReviewRecord
from app.models.salary_benchmark import ExperienceLevel, SalaryBenchmark
from app.models.school import School
from app.models.skill_node import SkillNode
from app.models.streak import StreakRecord
from app.models.user import User, UserStage
from app.models.user_badge import UserBadge
from app.models.user_llm_config import UserLLMConfig

# 决策副驾驶护城河
from app.models.user_memory import MemoryFactType, UserMemoryFact
from app.models.user_setting import UserSetting

__all__ = [
    "User",
    "UserStage",
    "UserStatus",
    "Assessment",
    "DestinationDecision",
    "DecisionStatus",
    "CareerEvent",
    "EventType",
    "SkillNode",
    "Retrospective",
    "PeriodType",
    "School",
    "ReportRecord",
    "ParseStatus",
    "EmploymentData",
    "Degree",
    "CommunityReport",
    "DestinationType",
    "SalaryRange",
    "InterviewReport",
    "InterviewResult",
    "DataSource",
    "CrawlerRun",
    "SourceType",
    "ContentType",
    "Post",
    "PostTopicType",
    "Company",
    "CompanySize",
    "CompanyReview",
    "SalaryBenchmark",
    "ExperienceLevel",
    "MarketData",
    "DatasetInfo",
    "UserBadge",
    "GrowthInsight",
    "UserSetting",
    "UserLLMConfig",
    # Phase 11 AI 职业管家
    "KnowledgeArticle",
    "Conversation",
    "Message",
    "CareerPlan",
    "CareerProfile",
    # Phase 12 里程碑执行日志与提醒
    "MilestoneLog",
    # 护城河功能
    "LifeWheelSnapshot",
    "StreakRecord",
    "ProactiveInsight",
    "LifeDesignSprint",
    "WeeklyReview",
    "DecisionAnalysis",
    # 考研情报
    "GradSchoolIntel",
    "SelfPositioning",
    "DarkKnowledge",
    "GradYanzhaoProgram",
    "GradScorelineRecord",
    "GradAdjustmentInfo",
    # 求职作战室
    "CompanyIntel",
    "CareerPositioning",
    "CareerDarkKnowledge",
    # 考公作战室
    "PostIntel",
    "CivilServicePositioning",
    "CivilServiceDarkKnowledge",
    # 考研导师评价系统
    "Mentor",
    "MentorReview",
    # 考研社区交流系统
    "ExperiencePost",
    "QA",
    "QAAnswer",
    # 失败案例库（对冲幸存者偏差）
    "FailureCase",
    # 考研外部资讯
    "KaoyanNews",
    # 国考职位
    "GwyPosition",
    # 国考进面分数线
    "GwyScoreLine",
    # 省考职位
    "GwyProvincePosition",
    # 收藏
    "Bookmark",
    "BookmarkTargetType",
    # 评论
    "Comment",
    # 通知
    "Notification",
    "NotificationType",
    # 上岸报告
    "OutcomeReport",
    "OutcomeType",
    "AdmissionPath",
    # 社区评分
    "CommunityRating",
    # 可用性测试埋点/反馈
    "Event",
    "Feedback",
    # 决策副驾驶护城河
    "UserMemoryFact",
    "MemoryFactType",
    "UserOnboarding",
    "OnboardingStatus",
    "DecisionReviewQueue",
    "ReviewStatus",
    "DarkKnowledgePushLog",
    "PushFeedback",
    # 路径冲突调解
    "PathConflictResolution",
    # 多路径 What-If 对比
    "PathComparison",
    # 7天微行动
    "MicroActionPlan",
    "MicroActionTask",
    # 家庭对话脚手架
    "FamilyDialogueSession",
    # 三中心 + 数据真实性接入层
    "DailyAction",
    "ActionCheckin",
    "ActionStreak",
    "ActionWeight",
    "GrowthTrajectory",
    "GrowthArchive",
    "ReviewRecord",
    "DataSourceMeta",
    "ExternalResearchItem",
    "ReviewQueueItem",
    "DataFreshness",
    "DocumentEmbedding",
    "CareerTestDrive",
    "Follow",
    "GrowthSnapshot",
    "LearningResource",
    "StudyPlan",
    "Report",
    "ReportStatus",
    "ReportTargetType",
    "BlockRelation",
    "QualityFeedback",
    "QualityFeedbackTargetType",
    "QualityFeedbackType",
]

# AI 增强功能
# 独立表模型（原未导出，导致 alembic autogenerate 漏检这 5 张表；
# 需在 Base.metadata 注册后才能生成对应迁移）
from app.models.career_test_drive import CareerTestDrive
from app.models.embedding_model import DocumentEmbedding
from app.models.follow import Follow
from app.models.growth_snapshot import GrowthSnapshot
from app.models.learning_resource import LearningResource
from app.models.study_plan import StudyPlan
