import { request, buildQuery } from "./client";

export interface NotificationResponse {
  id: string;
  user_id: string;
  type: string;
  title: string;
  content: string;
  link?: string | null;
  read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationResponse[];
  total: number;
  unread_count: number;
}

export const notificationsApi = {
  list: (params?: { unread_only?: boolean; page?: number; page_size?: number }) =>
    request<NotificationListResponse>(
      `/api/notifications${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
  unreadCount: () =>
    request<{ unread_count: number }>("/api/notifications/unread-count"),
  markRead: (id: string) =>
    request<NotificationResponse>(`/api/notifications/${id}/read`, {
      method: "PUT",
    }),
  markAllRead: () =>
    request<{ message: string }>("/api/notifications/read-all", {
      method: "POST",
    }),
};
