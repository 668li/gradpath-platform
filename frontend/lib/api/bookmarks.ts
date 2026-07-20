import { request, buildQuery } from "./client";

export interface BookmarkResponse {
  id: string;
  user_id: string;
  target_type: string;
  target_id: string;
  created_at: string;
}

export interface BookmarkListResponse {
  items: BookmarkResponse[];
  total: number;
}

export interface BookmarkCreate {
  target_type: string;
  target_id: string;
}

export const bookmarksApi = {
  list: (params?: { target_type?: string }) =>
    request<BookmarkListResponse>(
      `/api/bookmarks${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  add: (body: BookmarkCreate) =>
    request<BookmarkResponse>("/api/bookmarks", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  remove: (id: string) =>
    request<void>(`/api/bookmarks/${id}`, { method: "DELETE" }),
};
