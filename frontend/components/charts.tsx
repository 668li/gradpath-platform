"use client";

import {
  PieChart,
  Pie,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { PIE_COLORS } from "@/lib/constants";

interface PieDatum {
  name: string;
  value: number;
}

export function DestinationPie({
  data,
  height = 280,
}: {
  data: PieDatum[];
  height?: number;
}) {
  if (!data.length) return null;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={90}
          innerRadius={45}
          paddingAngle={2}
          label
        >
          {data.map((_, i) => (
            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

interface RadarDatum {
  category: string;
  count: number;
}

export function SkillRadar({
  data,
  height = 320,
}: {
  data: RadarDatum[];
  height?: number;
}) {
  if (!data.length) return null;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data} outerRadius="75%">
        <PolarGrid />
        <PolarAngleAxis dataKey="category" />
        <PolarRadiusAxis allowDecimals={false} />
        <Radar
          name="技能数"
          dataKey="count"
          stroke="#3377f6"
          fill="#3377f6"
          fillOpacity={0.4}
        />
        <Tooltip />
      </RadarChart>
    </ResponsiveContainer>
  );
}

/** 霍兰德 6 维度雷达图 — 品牌色填充 */
export function HollandRadar({
  data,
  height = 300,
}: {
  data: { code: string; name: string; score: number }[];
  height?: number;
}) {
  if (!data.length) return null;
  const chartData = data.map((d) => ({ category: `${d.code} ${d.name}`, score: d.score }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={chartData} outerRadius="72%">
        <PolarGrid stroke="#e2e0db" />
        <PolarAngleAxis
          dataKey="category"
          tick={{ fill: "#6b6760", fontSize: 12 }}
        />
        <PolarRadiusAxis allowDecimals={false} tick={false} axisLine={false} />
        <Radar
          name="得分"
          dataKey="score"
          stroke="#0d9488"
          fill="#0d9488"
          fillOpacity={0.35}
          strokeWidth={2}
        />
        <Tooltip
          contentStyle={{
            borderRadius: 8,
            border: "1px solid #e2e0db",
            fontSize: 13,
          }}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
