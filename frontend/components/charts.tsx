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
