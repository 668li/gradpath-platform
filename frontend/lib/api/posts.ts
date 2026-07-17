import type {
  PostListResponse,
  PostCreate,
  PostItem,
  CommentListResponse,
  CommentCreate,
  CommentResponse,
} from "@/types";
import { request, buildQuery } from "./client";

// ===== 讨论帖 =====
export const postsApi = {
  list: (params: {
    topic_type: string;
    topic_key: string;
    page?: number;
    page_size?: number;
  }) =>
    request<PostListResponse>("/api/posts/list", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  create: (body: PostCreate) =>
    request<PostItem>("/api/posts", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  update: (id: string, content: string) =>
    request<PostItem>(`/api/posts/${id}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),

  remove: (id: string) =>
    request<void>(`/api/posts/${id}`, { method: "DELETE" }),
};

// ===== 评论 =====
export const commentApi = {
  listByPost: (postId: string, params?: { offset?: number; limit?: number }) =>
    request<CommentListResponse>(
      `/api/comments/post/${postId}${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  create: (body: CommentCreate) =>
    request<CommentResponse>("/api/comments", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  delete: (id: string) =>
    request<void>(`/api/comments/${id}`, { method: "DELETE" }),
  like: (id: string) =>
    request<{ message: string; like_count: number }>(`/api/comments/${id}/like`, {
      method: "POST",
    }),
};