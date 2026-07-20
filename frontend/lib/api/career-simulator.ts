import { request } from "./client";

const BASE = "/api/career-simulator";

export interface PathConfig {
  name: string;
  path_type: string;
  city: string;
  industry: string;
}

export interface YearResult {
  year: number;
  phase: string;
  phase_detail: string;
  monthly_salary: number;
  annual_income: number;
  cumulative_income: number;
  satisfaction: number;
  growth_rate: number;
  risk_level: string;
  risk_factors: string[];
  milestones: string[];
  key_events: string[];
  education_cost: number;
  net_worth: number;
}

export interface PathResult {
  name: string;
  path_type: string;
  industry: string;
  city: string;
  yearly: YearResult[];
  total_income: number;
  total_education_cost: number;
  net_worth_10yr: number;
  avg_satisfaction: number;
  career_growth_score: number;
  stability_score: number;
  overall_risk: string;
  recommendation: string;
  comparison_summary: string;
}

export interface SimulateResponse {
  paths: PathResult[];
  recommendation: string;
  market_context: Record<string, unknown>;
}

export interface Preset {
  name: string;
  path_type: string;
  city: string;
  industry: string;
  description: string;
}

export interface CityTier {
  tier: string;
  cities: string[];
  salary_multiplier: number;
  cost_multiplier: number;
}

export interface Industry {
  id: string;
  name: string;
  paths: string[];
}

export const careerSimulatorApi = {
  simulate: (data: {
    current_year: number;
    years: number;
    paths: PathConfig[];
  }) =>
    request<SimulateResponse>(BASE + "/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  getPresets: () =>
    request<{ presets: Preset[] }>(BASE + "/presets"),

  getCities: () =>
    request<{ tiers: CityTier[] }>(BASE + "/cities"),

  getIndustries: () =>
    request<{ industries: Industry[] }>(BASE + "/industries"),
};
