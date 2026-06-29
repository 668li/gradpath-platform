"use client";

import { useEffect, useState } from "react";
import {
  PieChart, Pie, Cell, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip,
  LineChart, Line, CartesianGrid, Legend,
} from "recharts";
import { RATE_LABEL, RATE_COLORS } from "@/lib/constants";
import type { EmploymentRecord, EmploymentTrend } from "@/types";

const MOBILE_CHART_HEIGHT = 220;
const DESKTOP_CHART_HEIGHT = 300;

/**
 * 简单的移动端检测 hook（SSR 安全：首屏默认 false，挂载后修正）。
 * 用于根据视口动态调整图表高度 / 坐标轴宽度。
 */
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

/** 0~1 比例 → 百分比整数字符串，如 0.45 → "45%" */
function pct(v: number): string {
  return `${(v * 100).toFixed(0)}%`;
}

/** 0~1 比例或 null → 友好文本，null 显示"无数据" */
function rateText(v: number | null | undefined): string {
  if (v === null || v === undefined) return "无数据";
  return pct(v);
}

/** YAxis 名称省略：超过 6 个字符显示前 5 个 + … */
function formatTickName(name: string): string {
  if (!name) return "";
  return name.length > 6 ? `${name.slice(0, 5)}…` : name;
}

/**
 * 毕业去向分布饼图。
 * 注意：本组件已由 DestinationPie 重命名为 EmploymentDestinationPie，
 * 以避免与 components/charts.tsx 中同名的 DestinationPie 冲突。
 */
export function EmploymentDestinationPie({
  record,
  contextLabel,
}: {
  record: EmploymentRecord;
  /** 可选上下文，如 "清华大学机械工程"，用于丰富无障碍描述 */
  contextLabel?: string;
}) {
  const isMobile = useIsMobile();
  const data = Object.entries(record.rates)
    .filter(([, v]) => v !== null && v > 0)
    .map(([key, value]) => ({
      name: RATE_LABEL[key] ?? key,
      value: value!,
      key,
    }));

  if (data.length === 0) {
    return <p className="text-sm text-slate-400">暂无去向分布数据</p>;
  }

  const summary = data.map((d) => `${d.name}${pct(d.value)}`).join("，");
  const prefix = contextLabel ? `${contextLabel}${record.year}年` : `${record.year}年`;
  const ariaLabel = `${prefix}毕业去向分布：${summary}`;

  return (
    <div role="img" aria-label={ariaLabel}>
      <ResponsiveContainer
        width="100%"
        height={isMobile ? MOBILE_CHART_HEIGHT : DESKTOP_CHART_HEIGHT}
      >
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={100}
            label={({ name, value }) => `${name} ${pct(value)}`}
          >
            {data.map((d) => (
              <Cell key={d.key} fill={RATE_COLORS[d.key] ?? "#999"} />
            ))}
          </Pie>
          <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
        </PieChart>
      </ResponsiveContainer>
      <span className="sr-only">{ariaLabel}</span>
    </div>
  );
}

/**
 * 横向条形排名图（就业单位 / 升学去向 Top10）。
 */
export function RankingBar({
  data,
  title,
}: {
  data: { name: string; count: number }[];
  title: string;
}) {
  const isMobile = useIsMobile();

  if (!data || data.length === 0)
    return <p className="text-sm text-slate-400">暂无{title}数据</p>;

  const top10 = data.slice(0, 10).reverse();
  // 用于无障碍摘要：取前 5 条，按原始（由高到低）顺序
  const top5 = data.slice(0, 5);
  const summary = top5.map((d) => `${d.name}${d.count}人`).join("，");
  const ariaLabel = `${title}排名（Top${Math.min(10, data.length)}）：${summary}`;

  return (
    <div role="img" aria-label={ariaLabel}>
      <ResponsiveContainer width="100%" height={Math.max(200, top10.length * 32)}>
        <BarChart data={top10} layout="vertical">
          <XAxis type="number" />
          <YAxis
            type="category"
            dataKey="name"
            width={isMobile ? 80 : 120}
            tick={{ fontSize: 12 }}
            tickFormatter={formatTickName}
          />
          <Tooltip />
          <Bar dataKey="count" fill="#3377f6" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <span className="sr-only">{ariaLabel}</span>
    </div>
  );
}

/**
 * 多年趋势折线图。
 * 各 rate 字段类型为 (number | null)[]，使用 connectNulls 避免断线。
 */
export function TrendLine({
  trend,
  contextLabel,
}: {
  trend: EmploymentTrend;
  /** 可选上下文，如 "清华大学机械工程"，用于丰富无障碍描述 */
  contextLabel?: string;
}) {
  const isMobile = useIsMobile();

  if (!trend || trend.years.length < 1)
    return <p className="text-sm text-slate-400">暂无趋势数据</p>;

  const data = trend.years.map((year, i) => ({
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
  const ariaLabel = `${prefix}${yearRange}就业去向趋势，包含就业率、升学率、考公率、出国率`;

  // 详细的逐年文本替代（供读屏 / 文本浏览器使用）
  const detail = trend.years
    .map((year, i) => {
      const seg = [
        `就业率${rateText(trend.employment_rate[i])}`,
        `升学率${rateText(trend.further_study_rate[i])}`,
        `考公率${rateText(trend.civil_service_rate[i])}`,
        `出国率${rateText(trend.abroad_rate[i])}`,
      ].join("，");
      return `${year}年：${seg}`;
    })
    .join("。");

  return (
    <div role="img" aria-label={ariaLabel}>
      <ResponsiveContainer
        width="100%"
        height={isMobile ? MOBILE_CHART_HEIGHT : DESKTOP_CHART_HEIGHT}
      >
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="year" />
          <YAxis tickFormatter={(v) => pct(v)} />
          <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
          <Legend />
          <Line type="monotone" dataKey="就业率" stroke="#3377f6" connectNulls />
          <Line type="monotone" dataKey="升学率" stroke="#16a34a" connectNulls />
          <Line type="monotone" dataKey="考公率" stroke="#d97706" connectNulls />
          <Line type="monotone" dataKey="出国率" stroke="#7c3aed" connectNulls />
        </LineChart>
      </ResponsiveContainer>
      <span className="sr-only">{`${ariaLabel}。${detail}`}</span>
    </div>
  );
}
