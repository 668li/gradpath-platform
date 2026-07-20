from app.models.assessment import Assessment
from app.models.career_event import CareerEvent, EventType
from app.models.career_plan import CareerPlan
from app.models.career_profile import CareerProfile
from app.models.community_report import CommunityReport, DestinationType, SalaryRange
from app.models.company import Company, CompanySize
from app.models.company_review import CompanyReview
from app.models.conversation import Conversation, Message
from app.models.dataset_info import DatasetInfo
from app.models.crawler_run import CrawlerRun
from app.models.data_source import DataSource
from app.models.decision_analysis import DecisionAnalysis
from app.models.destination_decision import DecisionStatus, DestinationDecision
from app.models.grad_intel import (
    DarkKnowledge,
    GradAdjustmentInfo,
    GradSchoolIntel,
    GradScorelineRecord,
    GradYanzhaoProgram,
    SelfPositioning,
)
from app.models.career_intel import CareerDarkKnowledge, CareerPositioning, CompanyIntel
from app.models.civil_service_intel import CivilServiceDarkKnowledge, CivilServicePositioning, PostIntel
from app.models.employment_data import Degree, EmploymentData
from app.models.growth_insight import GrowthInsight
from app.models.interview_report import InterviewDimension, InterviewReport, InterviewResult
from app.models.knowledge_article import KnowledgeArticle
from app.models.market_data import MarketData
from app.models.milestone_log import MilestoneLog
from app.models.pipeline_enums import ContentType, SourceType
from app.models.post import Post, PostTopicType
from app.models.proactive_insight import ProactiveInsight
from app.models.reference_snapshot import ReferenceSnapshot, SnapshotSource
from app.models.report_record import ParseStatus, ReportRecord
from app.models.retrospective import PeriodType, Retrospective
from app.models.salary_benchmark import ExperienceLevel, SalaryBenchmark
from app.models.school import School
from app.models.skill_node import SkillNode
from app.models.streak import StreakRecord
from app.models.life_design import LifeDesignSprint, WeeklyReview
from app.models.life_wheel import LifeWheelSnapshot
from app.models.user import User, UserStage
from app.models.user_badge import UserBadge
from app.models.user_setting import UserSetting
from app.models.mentor import Mentor
from app.models.mentor_review import MentorReview
from app.models.experience_post import ExperiencePost
from app.models.kaoyan_news import KaoyanNews
from app.models.qa import QA
from app.models.qa_answer import QAAnswer
from app.models.bookmark import Bookmark, BookmarkTargetType
from app.models.comment import Comment
from app.models.notification import Notification, NotificationType
from app.models.outcome_report import AdmissionPath, OutcomeReport, OutcomeType
from app.models.community_rating import CommunityRating
from app.models.event import Event, Feedback
# 决策副驾驶护城河
from app.models.user_memory import MemoryFactType, UserMemoryFact
from app.models.onboarding import OnboardingStatus, UserOnboarding
from app.models.decision_review import DecisionReviewQueue, ReviewStatus
from app.models.dark_knowledge_push import DarkKnowledgePushLog, PushFeedback

__all__ = [
    "User", "UserStage",
    "Assessment",
    "DestinationDecision", "DecisionStatus",
    "CareerEvent", "EventType",
    "SkillNode",
    "Retrospective", "PeriodType",
    "ReferenceSnapshot", "SnapshotSource",
    "School",
    "ReportRecord", "ParseStatus",
    "EmploymentData", "Degree",
    "CommunityReport", "DestinationType", "SalaryRange",
    "InterviewReport", "InterviewDimension", "InterviewResult",
    "DataSource",
    "CrawlerRun",
    "SourceType", "ContentType",
    "Post", "PostTopicType",
    "Company", "CompanySize",
    "CompanyReview",
    "SalaryBenchmark", "ExperienceLevel",
    "MarketData",
    "DatasetInfo",
    "UserBadge",
    "GrowthInsight",
    "UserSetting",
    # Phase 11 AI 职业管家
    "KnowledgeArticle",
    "Conversation", "Message",
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
    # 考研外部资讯
    "KaoyanNews",
    # 收藏
    "Bookmark", "BookmarkTargetType",
    # 评论
    "Comment",
    # 通知
    "Notification", "NotificationType",
    # 上岸报告
    "OutcomeReport", "OutcomeType", "AdmissionPath",
    # 社区评分
    "CommunityRating",
    # 可用性测试埋点/反馈
    "Event",
    "Feedback",
    # 决策副驾驶护城河
    "UserMemoryFact", "MemoryFactType",
    "UserOnboarding", "OnboardingStatus",
    "DecisionReviewQueue", "ReviewStatus",
    "DarkKnowledgePushLog", "PushFeedback",
]

# AI 增强功能
from app.models.embedding_model import DocumentEmbedding, RAGStats
