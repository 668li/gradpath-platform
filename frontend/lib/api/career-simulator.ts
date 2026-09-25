import { request } from "./client";

const BASE = "/api/career-simulator";

// v2 真数据胜率推演（2026-09-25 重构）：
// 旧版 10 年薪资/满意度预测已判死，本客户端对应新后端口径。

export interface PathConfig {
  name?: string;
  path_type: "grad" | "civil" | "career";
  /** grad: 985/211；civil: police/general/central */
  target?: string | null;
  city?: string | null;
  /** 考研估分(500制) / 考公模考分(200制) */
  estimated_score?: number | null;
}

export interface DistributionMetric {
  label: string;
  p25?: number;
  p50?: number;
  p75?: number;
  value?: number;
  unit: string;
  sample_size: number | null;
  source: string;
  source_url?: string | null;
  direction: "your_score" | "lower_better" | "anchor";
  /** direction=your_score 时给全量分布供画图（降采样后） */
  distribution?: number[];
}

export interface YourPosition {
  metric: string;
  percentile: number | null;
  position_word: string;
  ref_p50: number;
}

export interface PathAnalysis {
  name: string;
  path_type: string;
  target?: string | null;
  city?: string | null;
  estimated_score?: number | null;
  metrics: DistributionMetric[];
  your_position: YourPosition | null;
  honest_gaps: string[];
  disclaimer: string;
  sample_note?: string;
  data_note?: string;
  carding_rate?: { severe_count: number; total: number; rate: number; note: string };
  clusters?: Record<string, { label: string; count: number }>;
}

export interface SimulateResponse {
  paths: PathAnalysis[];
  method_note: string;
  engine_analysis?: {
    recommendation: string | null;
    metrics: Array<Record<string, unknown>>;
    has_discourage_cards: boolean;
    source: string;
  } | null;
}

export interface Preset {
  name: string;
  path_type: string;
  target?: string | null;
  description: string;
}

export interface MetaResponse {
  tiers: Array<{ id: string; name: string }>;
  clusters: Array<{ id: string; name: string }>;
  note: string;
}

export const careerSimulatorApi = {
  simulate: (data: {
    paths: PathConfig[];
    major?: string | null;
    region?: string | null;
    school_tier?: string | null;
  }) =>
    request<SimulateResponse>(BASE + "/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  getPresets: () => request<{ presets: Preset[] }>(BASE + "/presets"),

  getMeta: () => request<MetaResponse>(BASE + "/meta"),
};
