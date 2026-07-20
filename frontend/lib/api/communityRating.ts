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
    ),
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
