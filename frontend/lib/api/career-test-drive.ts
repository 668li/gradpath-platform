// frontend/lib/api/career-test-drive.ts
// 职业试驾 API 客户端
import { request } from "./client";
import type {
  CareerTestDrive,
  CareerTestDriveCreate,
} from "../../types/career-test-drive";

const BASE = "/api/career-test-drive";

export const careerTestDriveApi = {
  generate: (data: CareerTestDriveCreate) =>
    request<CareerTestDrive>(BASE + "/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  getHistory: () => request<CareerTestDrive[]>(BASE + "/history"),

  getById: (id: string) => request<CareerTestDrive>(`${BASE}/${id}`),
};
