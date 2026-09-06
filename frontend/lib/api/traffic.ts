import { request } from "./client";

// ===== 流量看板（/admin/traffic，admin-only） =====
// 数据源：宿主侧 monitoring/traffic_pipeline.sh 每日 21:50 upsert t_traffic_daily。
// 口径与微信日报一致：444 已单列为 blocked、机器人已滤、轮询心跳不计入 pv。

export interface TrafficDay {
  date: string; // YYYY-MM-DD（北京时间）
  pv: number;
  uv: number;
  blocked: number;
  registrations: number;
  conversion_rate: number; // registrations / uv
}

export interface TrafficSummary {
  total_uv: number;
  total_pv: number;
  total_blocked: number;
  total_registrations: number;
  conversion_rate: number;
}

export interface TrafficDailyResponse {
  days: TrafficDay[]; // 按 date 升序
  summary: TrafficSummary;
}

export const trafficApi = {
  daily: (days = 30) =>
    request<TrafficDailyResponse>(`/api/traffic/daily?days=${days}`),
};
