import type { EventCreate, EventResponse, EventUpdate, PaginatedResponse } from "@/types";
import { request, buildQuery } from "./client";

// ===== Events =====
export const eventsApi = {
  list: (params?: {
    event_type?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }) =>
    request<PaginatedResponse<EventResponse>>(
      `/api/events${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  get: (id: string) => request<EventResponse>(`/api/events/${id}`),
  create: (body: EventCreate) =>
    request<EventResponse>("/api/events", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: EventUpdate) =>
    request<EventResponse>(`/api/events/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  remove: (id: string) =>
    request<void>(`/api/events/${id}`, { method: "DELETE" }),
};