"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Eye, MousePointerClick, ShieldBan, UserPlus, Percent } from "lucide-react";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useAuthStore } from "@/stores/auth";
import { trafficApi, type TrafficDailyResponse } from "@/lib/api/traffic";

// 流量看板：访客/浏览/攻击/注册转化率的一站式趋势。
// 口径备注：uv=不重复 IP（NAT 低估、伪装 UA 爬虫高估）；444 已单列为攻击。
function StatCard({
  label,
  value,
  detail,
  icon: Icon,
  color,
}: {
  label: string;
  value: string;
  detail: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-2xl border border-paper-300 bg-white p-5">
      <div className="flex items-center gap-2">
        <span className={`rounded-lg p-1.5 ${color}`}>
          <Icon className="h-4 w-4" />
        </span>
        <span className="text-xs text-ink-500">{label}</span>
      </div>
      <span className="font-display text-2xl font-semibold text-ink-900">{value}</span>
      <span className="text-xs text-ink-400">{detail}</span>
    </div>
  );
}

export default function TrafficDashboardPage() {
  const user = useAuthStore((s) => s.user);
  const hydrated = useAuthStore((s) => s.hydrated);
  const [range, setRange] = useState<7 | 30>(30);
  const [data, setData] = useState<TrafficDailyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async (days: number) => {
    setLoading(true);
    setError("");
    try {
      setData(await trafficApi.daily(days));
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (hydrated && user) void load(range);
  }, [hydrated, user, range]);

  if (!hydrated || loading) return <LoadingState text="加载流量数据..." />;
  if (error || !data)
    return (
      <EmptyState
        title="加载失败"
        description={error || "暂无数据（数据由每日 21:50 聚合任务写入，新站可能需要等待 1-2 天）"}
      />
    );

  const { summary, days } = data;
  const chartData = days.map((d) => ({
    date: d.date.slice(5), // MM-DD
    访客UV: d.uv,
    浏览PV: d.pv,
    转化率: Number((d.conversion_rate * 100).toFixed(1)),
  }));
  const last = days[days.length - 1];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-xl font-semibold text-ink-900">流量看板</h1>
          <p className="text-sm text-ink-400">
            访客/浏览/攻击拦截/注册转化率 · 数据每日 21:50 聚合（与微信日报同口径）
          </p>
        </div>
        <div className="flex gap-1 rounded-xl border border-paper-300 bg-white p-1">
          {([7, 30] as const).map((d) => (
            <button
              key={d}
              onClick={() => setRange(d)}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                range === d ? "bg-brand-600 text-white" : "text-ink-500 hover:bg-paper-100"
              }`}
            >
              近 {d} 天
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatCard
          label="访客 UV 合计"
          value={String(summary.total_uv)}
          detail="不重复来源 IP（估算）"
          icon={Eye}
          color="text-indigo-600 bg-indigo-50"
        />
        <StatCard
          label="有效浏览 PV"
          value={String(summary.total_pv)}
          detail="已剔除机器人/静态资源/轮询"
          icon={MousePointerClick}
          color="text-emerald-600 bg-emerald-50"
        />
        <StatCard
          label="注册转化率"
          value={`${(summary.conversion_rate * 100).toFixed(1)}%`}
          detail={`${summary.total_registrations} 注册 / ${summary.total_uv} 访客`}
          icon={Percent}
          color="text-amber-600 bg-amber-50"
        />
        <StatCard
          label="新注册用户"
          value={String(summary.total_registrations)}
          detail="按北京时间注册日聚合"
          icon={UserPlus}
          color="text-sky-600 bg-sky-50"
        />
        <StatCard
          label="攻击拦截"
          value={String(summary.total_blocked)}
          detail="444 探测拦截次数（fail2ban 联动）"
          icon={ShieldBan}
          color="text-red-600 bg-red-50"
        />
      </div>

      <div className="rounded-2xl border border-paper-300 bg-white p-5">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="font-display text-base font-semibold text-ink-900">趋势</h2>
          <span className="text-xs text-ink-400">
            最新一天（{last?.date}）：UV {last?.uv} · PV {last?.pv} · 注册 {last?.registrations}
          </span>
        </div>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 5, right: 10, bottom: 0, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} />
              <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickLine={false} />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 11 }}
                tickLine={false}
                unit="%"
              />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="浏览PV" fill="#10b981" radius={[3, 3, 0, 0]} />
              <Bar yAxisId="left" dataKey="访客UV" fill="#6366f1" radius={[3, 3, 0, 0]} />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="转化率"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-paper-300 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-paper-50 text-left text-xs text-ink-500">
            <tr>
              <th className="px-4 py-2.5 font-medium">日期</th>
              <th className="px-4 py-2.5 font-medium">访客 UV</th>
              <th className="px-4 py-2.5 font-medium">浏览 PV</th>
              <th className="px-4 py-2.5 font-medium">注册</th>
              <th className="px-4 py-2.5 font-medium">转化率</th>
              <th className="px-4 py-2.5 font-medium">攻击拦截</th>
            </tr>
          </thead>
          <tbody>
            {[...days].reverse().map((d) => (
              <tr key={d.date} className="border-t border-paper-200">
                <td className="px-4 py-2.5 text-ink-700">{d.date}</td>
                <td className="px-4 py-2.5">{d.uv}</td>
                <td className="px-4 py-2.5">{d.pv}</td>
                <td className="px-4 py-2.5">{d.registrations}</td>
                <td className="px-4 py-2.5">{(d.conversion_rate * 100).toFixed(1)}%</td>
                <td className="px-4 py-2.5 text-red-600">{d.blocked}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
