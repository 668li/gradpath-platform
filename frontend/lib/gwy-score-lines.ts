import type { GwyScoreLineResponse } from "@/types";

/**
 * 进面分数线展示工具。
 *
 * 同一 position_code 在 gwy_score_line 中可能有多条：不同批次（首批/调剂/补充录用）
 * 各一条；同批次内也可能因官方按专业方向拆分行而出现多条（职位表里 position_code
 * 本就非唯一）。展示时按批次聚合取最低分，避免同一批次重复出现。
 */
export interface ScoreLineAgg {
  batch: string;
  score: number;
}

/** 按批次聚合：每批次取最低进面分，按批次名排序（首批 < 调剂 < 补充录用）。 */
export function aggregateScoreLines(
  lines: GwyScoreLineResponse[] | undefined,
): ScoreLineAgg[] {
  if (!lines || lines.length === 0) return [];
  const byBatch = new Map<string, number>();
  for (const l of lines) {
    if (l.min_score == null) continue;
    const cur = byBatch.get(l.batch);
    if (cur == null || l.min_score < cur) byBatch.set(l.batch, l.min_score);
  }
  const order = ["首批", "调剂", "补充录用"];
  return [...byBatch.entries()]
    .sort((a, b) => order.indexOf(a[0]) - order.indexOf(b[0]))
    .map(([batch, score]) => ({ batch, score }));
}

/** 格式化为「首批 122.8 分 · 补充录用 146.7 分」；无数据返回 null。 */
export function formatScoreLines(
  lines: GwyScoreLineResponse[] | undefined,
): string | null {
  const agg = aggregateScoreLines(lines);
  if (agg.length === 0) return null;
  return agg.map(({ batch, score }) => `${batch} ${score} 分`).join(" · ");
}
