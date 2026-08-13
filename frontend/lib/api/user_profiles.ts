import { request, buildQuery } from "./client";
import type { UserProfile, ExperiencePostResponse, QAResponse, QAAnswerResponse } from "@/types";

export const userProfileApi = {
  getProfile: (userId: string) =>
    request<UserProfile>(`/api/users/${userId}/profile`),
  getPosts: (userId: string, page = 1, pageSize = 20) =>
    request<ExperiencePostResponse[]>(`/api/users/${userId}/posts${buildQuery({ page, page_size: pageSize })}`),
  getQA: (userId: string, page = 1, pageSize = 20) =>
    request<QAResponse[]>(`/api/users/${userId}/qa${buildQuery({ page, page_size: pageSize })}`),
  getAnswers: (userId: string, page = 1, pageSize = 20) =>
    request<QAAnswerResponse[]>(`/api/users/${userId}/answers${buildQuery({ page, page_size: pageSize })}`),
};
