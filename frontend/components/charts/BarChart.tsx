// 统一柱状图：合并
//   - ScoreDistributionChart（竖向，range/count，品牌色阶逐条着色，
//     tooltip 显示"X 所（Y%）"百分比 formatter，空态"暂无分数线分布数据"）
//   - RankingBar（横向 layout=vertical，name/count，Top10 截断 + 反转，
//     移动端 Y 轴宽度收窄，超 6 字省略，aria-label 排名摘要）
//
// 通过 orientation 切换横/竖，保留各自独有逻辑。

"use client";

import {
  BarChart as ReBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useEffect, useState } from "react";
import { BRAND_SCALE } from "./primitives/colors";
import { tooltipStyle } from "./primitives/ChartTooltip";
import { ChartEmpty } from "./primitives/ChartCard";

const GRID_COLOR = "var(--color-paper-200, #f5f3ec)";
const TICK_COLOR = "var(--color-ink-400, #7a7468)";
const RANK_COLOR = "#3377f6";

// recharts 轴样式：提取为模块顶层常量，避免每次渲染创建新对象导致 React.memo 失效
const TICK_STYLE_PLAIN = { fontSize: 12 };
const TICK_STYLE_COLORED = { fill: TICK_COLOR, fontSize: 12 };
const AXIS_LINE_STYLE = { stroke: GRID_COLOR };

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

// 名称省略：超过 6 个字符显示前 5 个 + …
function formatTickName(name: string): string {
  if (!name) return "";
  return name.length > 6 ? `${name.slice(0, 5)}…` : name;
}

export interface DistributionPoint {
  range: string;
  count: number;
}

export interface RankPoint {
  name: string;
  count: number;
}

interface BarChartProps {
  // —— 竖向分布（ScoreDistributionChart）——
  data?: DistributionPoint[];
  // —— 横向排名（RankingBar）——
  ranking?: RankPoint[];

  orientation?: "vertical" | "horizontal";
  /** 横向排名标题，用于空态 / aria 文案 */
  title?: string;
  /** 横向排名截断条数，默认 10 */
  topN?: number;
  height?: number;
  emptyText?: string;
  ariaLabel?: string;
}

export function BarChart({
  data,
  ranking,
  orientation = "vertical",
  title = "排名",
  topN = 10,
  height,
  emptyText,
  ariaLabel,
}: BarChartProps) {
  const isMobile = useIsMobile();

  // —— 横向排名（RankingBar）——
  if (orientation === "horizontal" || ranking) {
    const resolved = ranking ?? [];
    if (!resolved || resolved.length === 0) {
      return <p className="text-sm text-slate-400">暂无{title}数据</p>;
    }

    const topList = resolved.slice(0, topN).reverse();
    const top5 = resolved.slice(0, 5);
    const summary = top5.map((d) => `${d.name}${d.count}人`).join("，");
    const label = `${title}排名（Top${Math.min(topN, resolved.length)}）：${summary}`;

    return (
      <div role="img" aria-label={ariaLabel ?? label}>
        <ResponsiveContainer width="100%" height={height ?? Math.max(200, topList.length * 32)}>
          <ReBarChart data={topList} layout="vertical">
            <XAxis type="number" />
            <YAxis
              type="category"
              dataKey="name"
              width={isMobile ? 80 : 120}
              tick={TICK_STYLE_PLAIN}
              tickFormatter={formatTickName}
            />
            <Tooltip />
            <Bar dataKey="count" fill={RANK_COLOR} radius={[0, 4, 4, 0]} />
          </ReBarChart>
        </ResponsiveContainer>
        <span className="sr-only">{label}</span>
      </div>
    );
  }

  // —— 竖向分布（ScoreDistributionChart）——
  const resolved = data ?? [];
  if (!resolved.length) {
    return <ChartEmpty message={emptyText ?? "暂无分数线分布数据"} height={height ?? 300} />;
  }

  const total = resolved.reduce((sum, d) => sum + d.count, 0);

  return (
    <ResponsiveContainer width="100%" height={height ?? 300}>
      <ReBarChart data={resolved} role="img" aria-label={ariaLabel ?? "分数线分布柱状图"}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
        <XAxis
          dataKey="range"
          tick={TICK_STYLE_COLORED}
          tickLine={false}
          axisLine={AXIS_LINE_STYLE}
        />
        <YAxis
          tick={TICK_STYLE_COLORED}
          tickLine={false}
          axisLine={AXIS_LINE_STYLE}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(value: number, _name: string, props: { payload?: DistributionPoint }) => [
            `${value} 所（${total > 0 ? ((value / total) * 100).toFixed(1) : 0}%）`,
            props.payload?.range ?? "",
          ]}
        />
        <Bar dataKey="count" name="院校数" radius={[4, 4, 0, 0]}>
          {resolved.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill={BRAND_SCALE[index % BRAND_SCALE.length]} />
          ))}
        </Bar>
      </ReBarChart>
    </ResponsiveContainer>
  );
}
