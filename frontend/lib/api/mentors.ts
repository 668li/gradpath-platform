import type {
  MentorPersona,
  MentorAdviceRequest,
  MultiPerspectiveRequest,
  MultiPerspectiveResponse,
  GrowthPatternResponse,
  MentorListResponse,
  MentorResponse,
  MentorReviewListResponse,
  MentorReviewCreate,
  MentorReviewResponse,
} from "@/types";
import { request, buildQuery } from "./client";

// ===== 护城河功能：AI 导师人格库 =====
export const mentorsApi = {
  listPersonas: () => request<MentorPersona[]>("/api/mentors/personas"),
  getAdvice: (body: MentorAdviceRequest) =>
    request<{ persona_code: string; advice: string }>("/api/mentors/advice", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getMultiPerspective: (body: MultiPerspectiveRequest) =>
    request<MultiPerspectiveResponse>("/api/mentors/multi-perspective", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

// ===== 护城河功能：成长模式智能 =====
export const growthPatternsApi = {
  analyze: () => request<GrowthPatternResponse>("/api/growth-patterns/analyze"),
};

// ===== 考研导师评价系统 =====
export const mentorApi = {
  /** 获取导师列表（支持筛选） */
  list: (params?: {
    page?: number;
    page_size?: number;
    university?: string;
    department?: string;
    research_direction?: string;
    min_rating?: number;
    enrollment_status?: string;
    search?: string;
  }) =>
    request<MentorListResponse>(
      `/api/mentors/kaoyan-mentors${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),

  /** 获取导师详情 */
  getDetail: (mentorId: string) =>
    request<MentorResponse>(`/api/mentors/kaoyan-mentors/${mentorId}`),

  /** 获取导师评价列表 */
  getReviews: (mentorId: string, page = 1, pageSize = 20) =>
    request<MentorReviewListResponse>(
      `/api/mentors/kaoyan-mentors/${mentorId}/reviews${buildQuery({ page: String(page), page_size: String(pageSize) })}`,
    ),

  /** 提交导师评价 */
  submitReview: (mentorId: string, data: MentorReviewCreate) =>
    request<MentorReviewResponse>(`/api/mentors/kaoyan-mentors/${mentorId}/reviews`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** 点赞评价 */
  likeReview: (mentorId: string, reviewId: string) =>
    request<{ success: boolean }>(`/api/mentors/kaoyan-mentors/${mentorId}/reviews/${reviewId}/like`, {
      method: "POST",
    }),
};