"use client";

import {
  PieChart, Pie, Cell, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip,
  LineChart, Line, CartesianGrid, Legend,
} from "recharts";
import { RATE_LABEL, RATE_COLORS } from "@/lib/constants";
import type { EmploymentRecord, EmploymentTrend } from "@/types";

export function DestinationPie({ record }: { record: EmploymentRecord }) {
  const data = Object.entries(record.rates)
    .filter(([, v]) => v !== null && v > 0)
    .map(([key, value]) => ({
      name: RATE_LABEL[key] ?? key,
      value: value!,
      key,
    }));

  if (data.length === 0) return <p className="text-sm text-slate-400">暂无去向分布数据</p>;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={100}
          label={({ name, value }) => `${name} ${(value * 100).toFixed(0)}%`}
        >
          {data.map((d) => (
            <Cell key={d.key} fill={RATE_COLORS[d.key] ?? "#999"} />
          ))}
        </Pie>
        <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function RankingBar({
  data,
  title,
}: {
  data: { name: string; count: number }[];
  title: string;
}) {
  if (!data || data.length === 0)
    return <p className="text-sm text-slate-400">暂无{title}数据</p>;

  const top10 = data.slice(0, 10).reverse();

  return (
    <ResponsiveContainer width="100%" height={Math.max(200, top10.length * 32)}>
      <BarChart data={top10} layout="vertical">
        <XAxis type="number" />
        <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 12 }} />
        <Tooltip />
        <Bar dataKey="count" fill="#3377f6" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function TrendLine({ trend }: { trend: EmploymentTrend }) {
  if (!trend || trend.years.length < 1)
    return <p className="text-sm text-slate-400">暂无趋势数据</p>;

  const data = trend.years.map((year, i) => ({
    year: String(year),
    就业率: trend.employment_rate[i],
    升学率: trend.further_study_rate[i],
    考公率: trend.civil_service_rate[i],
    出国率: trend.abroad_rate[i],
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="year" />
        <YAxis tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
        <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
        <Legend />
        <Line type="monotone" dataKey="就业率" stroke="#3377f6" />
        <Line type="monotone" dataKey="升学率" stroke="#16a34a" />
        <Line type="monotone" dataKey="考公率" stroke="#d97706" />
        <Line type="monotone" dataKey="出国率" stroke="#7c3aed" />
      </LineChart>
    </ResponsiveContainer>
  );
}
