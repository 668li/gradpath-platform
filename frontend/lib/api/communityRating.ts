import { request, buildQuery } from "./client";

export interface RatingResponse {
  id: string;
  target_type: string;
  target_id: string;
  user_id: string;
  score: number;
  comment?: string;
  created_at: string;
  verified?: boolean;
}

export interface RatingStats {
  target_type: string;
  target_id: string;
  average: number;
  count: number;
  distribution?: Record<number, number>;
}

export interface TopRatedItem {
  target_type: string;
  target_id: string;
  average: number;
  count: number;
  title?: string;
}

export const ratingApi = {
  rate: (body: {
    target_type: string;
    target_id: string;
    score: number;
    comment?: string;
  }) =>
    request<RatingResponse>("/api/community-rating/rate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  stats: (target_type: string, target_id: string) =>
    request<RatingStats>(
      `/api/community-rating/stats/${encodeURIComponent(target_type)}/${encodeURIComponent(target_id)}`,
    ).then((raw) => ({
      // 后端实际返回 avg_stars / rating_count / quality_score / distribution，
      // 前端约定用 average / count。在此做字段映射，避免上层 .toFixed() 因 undefined 崩溃。
      target_type: raw.target_type ?? target_type,
      target_id: raw.target_id ?? target_id,
      average:
        (raw as unknown as { avg_stars?: number; average?: number }).avg_stars ??
        raw.average ??
        0,
      count:
        (raw as unknown as { rating_count?: number; count?: number })
          .rating_count ??
        raw.count ??
        0,
      distribution: raw.distribution,
    })),
  top: (params?: { target_type?: string; limit?: number }) =>
    request<TopRatedItem[]>(
      `/api/community-rating/top${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
  userRatings: (params?: { target_type?: string }) =>
    request<RatingResponse[]>(
      `/api/community-rating/user${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
  verifyBadge: (target_type: string, target_id: string) =>
    request<{ verified: boolean }>(
      `/api/community-rating/verify/${encodeURIComponent(target_type)}/${encodeURIComponent(target_id)}`,
      { method: "POST", body: JSON.stringify({}) },
    ),
};
