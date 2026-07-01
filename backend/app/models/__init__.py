from app.models.career_event import CareerEvent, EventType
from app.models.career_plan import CareerPlan
from app.models.career_profile import CareerProfile
from app.models.community_report import CommunityReport, DestinationType, SalaryRange
from app.models.company import Company, CompanySize
from app.models.conversation import Conversation, Message
from app.models.data_source import DataSource
from app.models.destination_decision import DecisionStatus, DestinationDecision
from app.models.employment_data import Degree, EmploymentData
from app.models.growth_insight import GrowthInsight
from app.models.interview_report import InterviewDimension, InterviewReport, InterviewResult
from app.models.knowledge_article import KnowledgeArticle
from app.models.market_data import MarketData
from app.models.milestone_log import MilestoneLog
from app.models.pipeline_enums import ContentType, SourceType
from app.models.post import Post, PostTopicType
from app.models.reference_snapshot import ReferenceSnapshot, SnapshotSource
from app.models.report_record import ParseStatus, ReportRecord
from app.models.retrospective import PeriodType, Retrospective
from app.models.salary_benchmark import ExperienceLevel, SalaryBenchmark
from app.models.school import School
from app.models.skill_node import SkillNode
from app.models.user import User, UserStage
from app.models.user_badge import UserBadge
from app.models.user_setting import UserSetting

__all__ = [
    "User", "UserStage",
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
    "SourceType", "ContentType",
    "Post", "PostTopicType",
    "Company", "CompanySize",
    "SalaryBenchmark", "ExperienceLevel",
    "MarketData",
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
]
