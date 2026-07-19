// 统一折线图：合并
//   - ScoreTrendChart（单条 year/score，品牌主色，空态"暂无分数线数据"）
//   - TrendLine（EmploymentTrend 多系列：就业率/升学率/考公率/出国率，
//     connectNulls 避免断线，Y 轴百分比，sr-only 逐年摘要，移动端高度）
//
// 通过 props 在两种形态间切换，保留各自独有逻辑。

"use client";

import {
  LineChart as ReLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useEffect, useState } from "react";
import { tooltipStyle } from "./primitives/ChartTooltip";
import { ChartEmpty } from "./primitives/ChartCard";
import type { EmploymentTrend } from "@/types";

const BRAND_LINE = "var(--color-brand-600, #0d7159)";
const GRID_COLOR = "var(--color-paper-200, #f5f3ec)";
const TICK_COLOR = "var(--color-ink-400, #7a7468)";
const NEUTRAL_GRID = "#e2e8f0";

const MOBILE_CHART_HEIGHT = 220;
const DESKTOP_CHART_HEIGHT = 300;

function useIsMobile(breakpoint = 768): boolean {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${breakpoint}px)`);
    const onChange = () => setIsMobile(mql.matches);
    onChange();
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [breakpoint]);
  return isMobile;
}

function pct(v: number): string {
  return `${(v * 100).toFixed(0)}%`;
}

// 多系列固定配色（TrendLine 旧值）
const TREND_COLORS: Record<string, string> = {
  就业率: "#3377f6",
  升学率: "#16a34a",
  考公率: "#d97706",
  出国率: "#7c3aed",
};

export interface ScorePoint {
  year: number;
  score: number;
}

interface LineChartProps {
  // —— 单系列（ScoreTrendChart）——
  data?: ScorePoint[];
  /** 折线数值 key，默认 "score" */
  valueKey?: string;
  /** 折线名称，默认 "分数线" */
  name?: string;

  // —— 多系列（TrendLine）——
  trend?: EmploymentTrend;
  /** 上下文标签，如 "清华大学机械工程" */
  contextLabel?: string;

  height?: number;
  emptyText?: string;
  ariaLabel?: string;
}

export function LineChart({
  data,
  valueKey = "score",
  name = "分数线",
  trend,
  contextLabel,
  height,
  emptyText = "暂无数据",
  ariaLabel,
}: LineChartProps) {
  const isMobile = useIsMobile();

  // —— 多系列就业趋势（TrendLine）——
  if (trend) {
    if (!trend || trend.years.length < 1) {
      return <p className="text-sm text-slate-400">暂无趋势数据</p>;
    }

    const lineData = trend.years.map((year, i) => ({
      year: String(year),
      就业率: trend.employment_rate[i],
      升学率: trend.further_study_rate[i],
      考公率: trend.civil_service_rate[i],
      出国率: trend.abroad_rate[i],
    }));

    const prefix = contextLabel ? `${contextLabel}的` : "";
    const yearRange =
      trend.years.length > 1
        ? `${trend.years[0]}年至${trend.years[trend.years.length - 1]}`
        : `${trend.years[0]}年`;
    const label = `${prefix}${yearRange}就业去向趋势，包含就业率、升学率、考公率、出国率`;

    const detail = trend.years
      .map((year, i) => {
        const seg = [
          `就业率${trend.employment_rate[i] !== null && trend.employment_rate[i] !== undefined ? pct(trend.employment_rate[i]) : "无数据"}`,
          `升学率${trend.further_study_rate[i] !== null && trend.further_study_rate[i] !== undefined ? pct(trend.further_study_rate[i]) : "无数据"}`,
          `考公率${trend.civil_service_rate[i] !== null && trend.civil_service_rate[i] !== undefined ? pct(trend.civil_service_rate[i]) : "无数据"}`,
          `出国率${trend.abroad_rate[i] !== null && trend.abroad_rate[i] !== undefined ? pct(trend.abroad_rate[i]) : "无数据"}`,
        ].join("，");
        return `${year}年：${seg}`;
      })
      .join("。");

    return (
      <div role="img" aria-label={label}>
        <ResponsiveContainer
          width="100%"
          height={height ?? (isMobile ? MOBILE_CHART_HEIGHT : DESKTOP_CHART_HEIGHT)}
        >
          <ReLineChart data={lineData}>
            <CartesianGrid strokeDasharray="3 3" stroke={NEUTRAL_GRID} />
            <XAxis dataKey="year" />
            <YAxis tickFormatter={(v) => pct(v)} />
            <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
            <Legend />
            <Line type="monotone" dataKey="就业率" stroke={TREND_COLORS["就业率"]} connectNulls />
            <Line type="monotone" dataKey="升学率" stroke={TREND_COLORS["升学率"]} connectNulls />
            <Line type="monotone" dataKey="考公率" stroke={TREND_COLORS["考公率"]} connectNulls />
            <Line type="monotone" dataKey="出国率" stroke={TREND_COLORS["出国率"]} connectNulls />
          </ReLineChart>
        </ResponsiveContainer>
        <span className="sr-only">{`${label}。${detail}`}</span>
      </div>
    );
  }

  // —— 单系列（ScoreTrendChart）——
  const resolved = data ?? [];
  if (!resolved.length) {
    return <ChartEmpty message={emptyText} height={height ?? 300} />;
  }

  const sortedData = [...resolved].sort((a, b) => a.year - b.year);

  return (
    <ResponsiveContainer width="100%" height={height ?? 300}>
      <ReLineChart data={sortedData} role="img" aria-label={ariaLabel ?? "分数线趋势折线图"}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
        <XAxis
          dataKey="year"
          tick={{ fill: TICK_COLOR, fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: GRID_COLOR }}
        />
        <YAxis
          tick={{ fill: TICK_COLOR, fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: GRID_COLOR }}
          domain={["dataMin - 10", "dataMax + 10"]}
        />
        <Tooltip contentStyle={tooltipStyle} />
        <Legend />
        <Line
          type="monotone"
          dataKey={valueKey}
          name={name}
          stroke={BRAND_LINE}
          strokeWidth={2}
          dot={{ fill: BRAND_LINE, strokeWidth: 2 }}
          activeDot={{ r: 6 }}
        />
      </ReLineChart>
    </ResponsiveContainer>
  );
}
