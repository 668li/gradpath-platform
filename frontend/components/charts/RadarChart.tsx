// 统一雷达图：合并
//   - SchoolRadarChart（多系列院校对比，RADAR_COLORS，空态"暂无院校对比数据"）
//   - SkillRadar（单系列技能数，蓝 #3377f6，fillOpacity 0.4）
//   - HollandRadar（单系列霍兰德 6 维，青 #0d9488，fillOpacity 0.35，中性灰网格）
//   - LifeWheelRadar（单系列人生 8 维，青 #0d9488，fillOpacity 0.35，固定量程 [0,10]）
//
// 通过 selectAxis/series 配置兼容不同数据形态，保留各自配色与独有逻辑。

"use client";

import {
  RadarChart as ReRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { RADAR_COLORS, FALLBACK_COLOR } from "./primitives/colors";
import { tooltipStyle, tooltipStyleNeutral } from "./primitives/ChartTooltip";
import { ChartEmpty } from "./primitives/ChartCard";

const TICK_COLOR = "var(--color-ink-400, #7a7468)";
const NEUTRAL_TICK = "#6b6760";
const NEUTRAL_GRID = "#e2e0db";

// recharts 极轴样式：提取为模块顶层常量，避免每次渲染创建新对象导致 React.memo 失效
const TICK_STYLE_NEUTRAL = { fill: NEUTRAL_TICK, fontSize: 12 };
const TICK_STYLE_BRAND = { fill: TICK_COLOR, fontSize: 12 };

// —— 多系列（院校对比）形态 ——
export interface SchoolRadarSeries {
  name: string;
  scores: Record<string, number>;
}

// —— 单系列形态（技能 / 霍兰德 / 人生轮）——
export interface RadarPoint {
  category?: string;
  dimension?: string;
  score?: number;
  count?: number;
  [k: string]: string | number | undefined;
}

interface RadarChartProps {
  /** 多系列院校对比数据 */
  schools?: SchoolRadarSeries[];
  /** 单系列数据（点或 {category|dimension, score|count}） */
  data?: RadarPoint[];
  /** 数据轴 key：dimension（院校/人生轮）或 category（技能/霍兰德） */
  axisKey?: "dimension" | "category";
  /** 数值 key：score 或 count */
  valueKey?: "score" | "count";
  /** 单系列名称（tooltip/legend 显示） */
  seriesName?: string;
  /** 单系列颜色；默认 brand 主色；霍兰德/人生轮旧值为 #0d9488 */
  color?: string;
  /** 填充透明度；默认 0.2（院校），其余旧值 0.35/0.4 */
  fillOpacity?: number;
  /** 固定量程 [min,max]；人生轮旧值为 [0,10] */
  domain?: [number, number];
  /** 网格颜色：neutral 用 #e2e0db（霍兰德/人生轮），默认品牌 paper-200 */
  gridVariant?: "brand" | "neutral";
  /** 是否显示极坐标刻度数值；默认 false（院校/霍兰德/人生轮旧行为） */
  showRadiusTicks?: boolean;
  height?: number;
  emptyText?: string;
  /** 无障碍标签 */
  ariaLabel?: string;
}

export function RadarChart({
  schools,
  data,
  axisKey = "dimension",
  valueKey = "score",
  seriesName = "数值",
  color,
  fillOpacity,
  domain,
  gridVariant = "brand",
  showRadiusTicks = false,
  height = 320,
  emptyText = "暂无数据",
  ariaLabel,
}: RadarChartProps) {
  // —— 多系列院校对比 ——
  if (schools) {
    if (!schools.length) {
      return <ChartEmpty message="暂无院校对比数据" height={height} />;
    }
    const allDimensions = Array.from(
      new Set(schools.flatMap((s) => Object.keys(s.scores)))
    );
    const chartData = allDimensions.map((dim) => {
      const entry: Record<string, string | number> = { dimension: dim };
      schools.forEach((school) => {
        entry[school.name] = school.scores[dim] ?? 0;
      });
      return entry;
    });

    return (
      <ResponsiveContainer width="100%" height={height}>
        <ReRadarChart data={chartData} outerRadius="70%" role="img" aria-label={ariaLabel ?? "院校对比雷达图"}>
          <PolarGrid stroke={gridVariant === "neutral" ? NEUTRAL_GRID : "var(--color-paper-200, #f5f3ec)"} />
          <PolarAngleAxis
            dataKey="dimension"
            tick={gridVariant === "neutral" ? TICK_STYLE_NEUTRAL : TICK_STYLE_BRAND}
          />
          <PolarRadiusAxis allowDecimals={false} tick={showRadiusTicks} axisLine={false} domain={domain} />
          {schools.map((school, i) => {
            const c = color ?? RADAR_COLORS[i % RADAR_COLORS.length];
            return (
              <Radar
                key={school.name}
                name={school.name}
                dataKey={school.name}
                stroke={c}
                fill={c}
                fillOpacity={fillOpacity ?? 0.2}
                strokeWidth={2}
              />
            );
          })}
          <Tooltip contentStyle={tooltipStyle} />
          <Legend />
        </ReRadarChart>
      </ResponsiveContainer>
    );
  }

  // —— 单系列形态 ——
  const resolved = data ?? [];
  if (!resolved.length) {
    return <ChartEmpty message={emptyText} height={height} />;
  }

  const gridColor = gridVariant === "neutral" ? NEUTRAL_GRID : "var(--color-paper-200, #f5f3ec)";
  const c = color ?? "var(--color-brand-600, #0d7159)";

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ReRadarChart data={resolved} outerRadius="72%" role="img" aria-label={ariaLabel ?? "雷达图"}>
        <PolarGrid stroke={gridColor} />
        <PolarAngleAxis dataKey={axisKey} tick={gridVariant === "neutral" ? TICK_STYLE_NEUTRAL : TICK_STYLE_BRAND} />
        <PolarRadiusAxis
          allowDecimals={false}
          tick={showRadiusTicks}
          axisLine={false}
          domain={domain}
        />
        <Radar
          name={seriesName}
          dataKey={valueKey}
          stroke={c}
          fill={c}
          fillOpacity={fillOpacity ?? 0.35}
          strokeWidth={2}
        />
        <Tooltip contentStyle={gridVariant === "neutral" ? tooltipStyleNeutral : tooltipStyle} />
      </ReRadarChart>
    </ResponsiveContainer>
  );
}
