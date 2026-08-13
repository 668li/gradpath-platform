export {
  getToken,
  setToken,
  clearToken,
  getRefreshToken,
  setRefreshToken,
  clearRefreshToken,
  request,
  buildQuery,
} from "./client";
export type { ApiError } from "./client";

export { cachedRequest, invalidateCache, clearQueryCache } from "./query-cache";
export {
  SWR_GLOBAL_CONFIG,
  apiFetcher,
  useApi,
  useApiMutation,
  useInvalidate,
} from "./swr-config";

export { authApi } from "./auth";
export { dashboardApi } from "./dashboard";
export { decisionsApi, decisionJournalApi, decisionAnalysisApi } from "./decisions";
export { eventsApi } from "./events";
export { skillsApi, skillApi } from "./skills";
export { retrospectivesApi } from "./retrospectives";
export { employmentApi, communityApi, interviewApi } from "./employment";
export { pipelineApi, externalDataApi } from "./pipeline";
export { postsApi, commentApi, followApi } from "./posts";
export { notificationsApi } from "./notifications";
export { bookmarksApi } from "./bookmarks";
export type { NotificationResponse, NotificationListResponse } from "./notifications";
export type { BookmarkResponse, BookmarkListResponse, BookmarkCreate } from "./bookmarks";
export { aiApi, careerIntelApi, civilServiceIntelApi, proactiveInsightsApi } from "./ai";
export { gamificationApi, streaksApi } from "./gamification";
export { exportApi } from "./export";
export { exportV2Api } from "./exportV2";
export { chatApi } from "./chat";
export { knowledgeApi } from "./knowledge";
export { careerPlansApi, careerProfileApi, planTemplatesApi } from "./career";
export { assessmentApi, lifeWheelApi } from "./assessment";
export { mentorsApi, growthPatternsApi, mentorApi } from "./mentors";
export { gradIntelApi, gradVisualizationApi, schoolAnalystApi, schoolCompareApi } from "./grad";
export type { AnalystReportRequest, AnalystReportResponse, CompareRequest, CompareResponse, SchoolAnalysis } from "./grad";
export { kaoyanCommunityApi, kaoyanNewsApi } from "./kaoyan";
export { studyPlanApi, learningResourceApi } from "./study";
export { aiStudyPlanApi } from "./ai-study-plan";
export { crawlerApi } from "./crawlers";
export { researchQueueApi } from "./research-queue";
export { recommendationApi, lifeDesignApi } from "./recommendations";
export { searchApi } from "./search";
export { outcomeReportApi } from "./outcome-report";
export { careerSimulatorApi } from "./career-simulator";
export type { PathConfig, PathResult, YearResult, SimulateResponse, Preset, CityTier, Industry } from "./career-simulator";
export { pathComparisonApi } from "./path-comparison";
export type { PathInput, PathMetrics, ComparisonResponse, RiskLevel, PathType } from "@/types/path-comparison";

export { microActionApi } from "./micro-action";
export type {
  MicroActionTargetPath,
  MicroActionTaskType,
  MicroActionTaskStatus,
  MicroActionPlanStatus,
  MicroActionPlanCreate,
  MicroActionTaskResponse,
  MicroActionPlanResponse,
  TaskCompleteRequest,
} from "@/types/micro-action";

// 三中心 v1（行动任务中心 / 成长档案中心 / 复盘中心）
export { actionsApi } from "./actions";
export type {
  ActionType,
  ActionStatus,
  StreakStatus,
  ActionCreateRequest,
  ActionUpdateRequest,
  CheckinRequest,
  StreakVO,
  ActionVO,
  ActionListResponse,
  CheckinVO,
  CheckinListResponse,
  ActionWeightVO,
  ActionWeightListResponse,
} from "@/types/action-center";

export { growthApi } from "./growth";
export type {
  TrajectoryEventType,
  ArchiveStatus,
  GrowthTrajectoryCreateRequest,
  GrowthTrajectoryVO,
  GrowthTrajectoryListResponse,
  GrowthArchiveVO,
  GrowthStatsVO,
} from "@/types/growth-center";

export { reviewsApi } from "./reviews";
export type {
  ReviewType,
  // ReviewStatus 与决策副驾驶（onboarding review）同名，冲突 —
  // 复盘状态类型请从 "@/types/review-center" 直接导入
  AIReviewStatus,
  ReviewCreateRequest,
  ReviewVO,
  ReviewDetailVO,
  ReviewPageResponse,
  AIReviewVO,
} from "@/types/review-center";

export { familyDialogueApi } from "./family-dialogue";
export type {
  ParentArchetype,
  FamilyDialogueStatus,
  FamilyDialogueStart,
  Argument,
  PracticeMessage as FamilyPracticeMessage,
  FamilyDialogueResponse,
  PracticeRequest as FamilyPracticeRequest,
} from "@/types/family-dialogue";

export { careerTestDriveApi } from "./career-test-drive";
export type { CareerTestDrive, CareerTestDriveCreate, TimeBlock } from "../../types/career-test-drive";

export { ragSearchApi } from "./rag";
export type { RAGSearchResponse, RAGSearchResult } from "./rag";
export { admissionApi } from "./admission";
export type { PredictResponse, HistoryResponse } from "./admission";
export { ratingApi } from "./communityRating";
export type { RatingResponse, RatingStats, TopRatedItem } from "./communityRating";
export { learningMethodsApi } from "./learningMethods";
export type { LearningMethod, LearningMethodListResponse, LearningMethodTag, LearningMethodStats } from "./learningMethods";

// 失败案例库（对冲幸存者偏差）
export { failureCaseApi } from "./failure-case";
export type {
  FailureCasePathType,
  FailureCaseStage,
  FailureCaseResponse,
  FailureCaseListResponse,
  FailureCaseStatsResponse,
  FailureCaseCreate,
} from "@/types/failure-case";

// 决策副驾驶护城河（Phase D）
export {
  userContextApi,
  userMemoryApi,
  onboardingApi,
  decisionPulseApi,
  darkKnowledgePushApi,
  pathConflictApi,
} from "./decision-copilot";

// 同路人洞察（创意功能）
export { peerInsightsApi } from "./peer-insights";
export type {
  PeerMirrorResponse,
  ProcrastinationResponse,
  DarkKnowledgeGapResponse,
} from "./peer-insights";
export type {
  MemoryFactType,
  OnboardingStatus,
  ReviewStatus,
  PushFeedback,
  ContextCareerProfile,
  ContextOnboarding,
  ContextMemoryFact,
  ContextDecision,
  ContextOutcomeReport,
  UserContextStats,
  UserContext,
  UserContextPrompt,
  UserMemoryFact,
  UserMemoryListResponse,
  AddFactRequest,
  AddFactResponse,
  MemoryFeedbackRequest,
  MemoryFeedbackResponse,
  ExtractRequest,
  ExtractResponse,
  OnboardingRecord,
  OnboardingGetResponse,
  OnboardingSaveRequest,
  OnboardingStatusResponse,
  PulseOverview,
  PulseActiveDecision,
  PulseReviewItem,
  PulseDarkKnowledgeItem,
  PulseMemoryFact,
  PulseFull,
  PulseListResponse,
  DarkKnowledgePush,
  DarkKnowledgePushListResponse,
  DarkKnowledgeUnreadCount,
  DarkKnowledgePushRequest,
  DarkKnowledgePushTriggerResponse,
  DarkKnowledgeFeedbackRequest,
  PathConflictOption,
  PathConflictAssessmentSummary,
  PathConflictCurrentSituation,
  PathConflictDetection,
  PathConflictResolveRequest,
  PathConflictActionPlan,
  PathConflictResolution,
} from "../../types/decision-copilot";