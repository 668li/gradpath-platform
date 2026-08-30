import { request } from "./client";

// ===== 决策实体库四件套完整率（数据北极星，admin-only） =====
// 四件套 = 招生目录 ∩ 院校情报 ∩ 有效分数线；Top100 = 软科排名前 100 为报考热度代理。

export interface CoverageMissingSchool {
  school: string;
  ranking: number;
  missing: string[]; // "catalog" | "intel" | "scoreline"
}

export interface EntityCoverage {
  definition: string;
  overall: {
    schools_total: number;
    with_catalog: number;
    with_intel: number;
    with_scoreline: number;
    full_set: number;
    full_set_rate: number;
  };
  top100: {
    total: number;
    full_set: number;
    full_set_rate: number;
    missing_sample: CoverageMissingSchool[];
    missing_total: number;
  };
}

export const dataCoverageApi = {
  /** 四件套完整率（管理端数据仪表盘） */
  coverage: () => request<EntityCoverage>("/api/data-freshness/coverage"),
};
