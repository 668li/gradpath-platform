// 统一饼图：合并
//   - AdmissionPieChart（grad，name/value，PIE_COLORS，空态"暂无录取数据"）
//   - DestinationPie（charts.tsx，name/value，PIE_COLORS，空态返回 null）
//   - EmploymentDestinationPie（employment-charts.tsx，EmploymentRecord，RATE_COLORS，
//     移动端高度、label 显示百分比、connectNulls、aria-label 摘要）
//
// 通过 props 切换行为，保留各自独有逻辑。

"use client";

import {
  PieChart as RePieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useEffect, useState } from "react";
import {
  PIE_COLORS,
  RATE_COLORS,
  RATE_LABEL,
  FALLBACK_COLOR,
} from "./primitives/colors";
import { tooltipStyle, tooltipStyleNeutral, SrOnly } from "./primitives/ChartTooltip";
import { ChartEmpty } from "./primitives/ChartCard";
import type { EmploymentRecord } from "@/types";

const MOBILE_CHART_HEIGHT = 220;
const DESKTOP_CHART_HEIGHT = 300;

/** SSR 安全的移动端检测（首屏默认 false，挂载后修正） */
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

export interface PieDatum {
  name: string;
  value: number;
}

interface PieChartProps {
  /** name/value 型数据（AdmissionPieChart / DestinationPie 形态） */
  data?: PieDatum[];
  /** 毕业去向记录（EmploymentDestinationPie 形态）；提供后优先于 data */
  record?: EmploymentRecord;
  /** 上下文标签，如 "清华大学机械工程"，用于丰富无障碍描述 */
  contextLabel?: string;
  /** 是否显示百分比（就业类饼图 label + tooltip 用百分比） */
  percentage?: boolean;
  height?: number;
  /** 空态文案；默认"暂无数据"。传 null 表示空态返回 null（DestinationPie 旧行为） */
  emptyText?: string | null;
  /** 饼图半径（outerRadius），默认 90；就业类旧值为 100 */
  outerRadius?: number;
  innerRadius?: number;
  /** 自定义空态 / 标注渲染（就业类用 sr-only 摘要） */
  ariaSummary?: string;
}

export function PieChart({
  data,
  record,
  contextLabel,
  percentage = false,
  height,
  emptyText = "暂无录取数据",
  outerRadius = 90,
  innerRadius = 45,
  ariaSummary,
}: PieChartProps) {
  const isMobile = useIsMobile();

  // —— 就业去向形态：来自 EmploymentRecord ——
  if (record) {
    const chartData = Object.entries(record.rates)
      .filter(([, v]) => v !== null && v > 0)
      .map(([key, value]) => ({
        name: RATE_LABEL[key] ?? key,
        value: value!,
        key,
      }));

    if (chartData.length === 0) {
      return <p className="text-sm text-slate-400">暂无去向分布数据</p>;
    }

    const summary =
      ariaSummary ??
      chartData.map((d) => `${d.name}${pct(d.value)}`).join("，");
    const prefix = contextLabel ? `${contextLabel}${record.year}年` : `${record.year}年`;
    const ariaLabel = `${prefix}毕业去向分布：${summary}`;

    return (
      <div role="img" aria-label={ariaLabel}>
        <ResponsiveContainer
          width="100%"
          height={height ?? (isMobile ? MOBILE_CHART_HEIGHT : DESKTOP_CHART_HEIGHT)}
        >
          <RePieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={
                percentage
                  ? ({ name, value }) => `${name} ${pct(value)}`
                  : undefined
              }
            >
              {chartData.map((d) => (
                <Cell key={d.key} fill={RATE_COLORS[d.key] ?? FALLBACK_COLOR} />
              ))}
            </Pie>
            <Tooltip
              formatter={(v: number) =>
                percentage ? `${(v * 100).toFixed(1)}%` : `${v}`
              }
            />
          </RePieChart>
        </ResponsiveContainer>
        <SrOnly text={ariaLabel} />
      </div>
    );
  }

  // —— name/value 形态：AdmissionPieChart / DestinationPie ——
  const resolved = data ?? [];

  if (resolved.length === 0) {
    if (emptyText === null) return null; // DestinationPie 旧行为
    return <ChartEmpty message={emptyText} height={height ?? 300} />;
  }

  return (
    <ResponsiveContainer width="100%" height={height ?? 300}>
      <RePieChart role="img" aria-label={ariaSummary ?? "分布饼图"}>
        <Pie
          data={resolved}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={outerRadius}
          innerRadius={innerRadius}
          paddingAngle={2}
          label={percentage ? ({ name, value }) => `${name} ${pct(value)}` : true}
        >
          {resolved.map((_, i) => (
            <Cell key={`cell-${i}`} fill={PIE_COLORS[i % PIE_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(v: number) =>
            percentage ? `${(v * 100).toFixed(1)}%` : `${v}`
          }
        />
        <Legend />
      </RePieChart>
    </ResponsiveContainer>
  );
}
