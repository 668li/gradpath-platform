"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, AlertTriangle, Users } from "lucide-react";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { communityApi } from "@/lib/api";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { RankingBar } from "@/components/employment-charts";
import {
  RATE_LABEL,
  RATE_COLORS,
  SALARY_RANGE_LABEL,
} from "@/lib/constants";
import type { CommunityAggregate } from "@/types";

const CHART_HEIGHT = 300;

/** 社区去向分布饼图：接受计数 Record，自行换算为比例展示 */
function CommunityDestinationPie({
  distribution,
  contextLabel,
}: {
  distribution: Record<string, number>;
  contextLabel?: string;
}) {
  const entries = Object.entries(distribution).filter(([, v]) => v > 0);
  if (entries.length === 0) {
    return <p className="text-sm text-slate-400">暂无去向分布数据</p>;
  }

  const total = entries.reduce((sum, [, v]) => sum + v, 0);
  const data = entries.map(([key, value]) => ({
    name: RATE_LABEL[key] ?? key,
    value: value,
    key,
  }));
  const summary = data
    .map((d) => `${d.name}${d.value}人(${((d.value / total) * 100).toFixed(0)}%)`)
    .join("，");
  const prefix = contextLabel ? `${contextLabel}社区` : "社区";
  const ariaLabel = `${prefix}毕业去向分布：共${total}人，${summary}`;

  return (
    <div role="img" aria-label={ariaLabel}>
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={100}
            label={({ name, value }) =>
              `${name} ${value}(${((value / total) * 100).toFixed(0)}%)`
            }
          >
            {data.map((d) => (
              <Cell key={d.key} fill={RATE_COLORS[d.key] ?? "#999"} />
            ))}
          </Pie>
          <Tooltip
            formatter={(v: number) => `${v}人 (${((v / total) * 100).toFixed(1)}%)`}
          />
        </PieChart>
      </ResponsiveContainer>
      <span className="sr-only">{ariaLabel}</span>
    </div>
  );
}

/** 薪资分布柱状图：接受计数 Record */
function SalaryDistributionBar({
  distribution,
}: {
  distribution: Record<string, number>;
}) {
  const entries = Object.entries(distribution).filter(([, v]) => v > 0);
  if (entries.length === 0) {
    return <p className="text-sm text-slate-400">暂无薪资分布数据</p>;
  }
  const data = entries.map(([key, value]) => ({
    name: SALARY_RANGE_LABEL[key] ?? key,
    count: value,
  }));
  const summary = data.map((d) => `${d.name}${d.count}人`).join("，");
  const ariaLabel = `社区薪资分布：${summary}`;

  return (
    <div role="img" aria-label={ariaLabel}>
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="count" fill="#7c3aed" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <span className="sr-only">{ariaLabel}</span>
    </div>
  );
}

function CommunityResultContent() {
  const router = useRouter();
  const toast = useToast();
  const searchParams = useSearchParams();
  // 从 URL 读取 Base64 编码的参数并解码为中文（与 explore 保持一致）
  const sEncoded = searchParams.get("s") ?? "";
  const mEncoded = searchParams.get("m") ?? "";
  const school = sEncoded ? decodeURIComponent(escape(atob(sEncoded))) : "";
  const major = mEncoded ? decodeURIComponent(escape(atob(mEncoded))) : "";

  const [data, setData] = useState<CommunityAggregate | null>(null);
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    // 无参数（直接访问）时重定向回社区提交页
    if (!school || !major) {
      setRedirecting(true);
      router.replace("/community");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const result = await communityApi.aggregate({ school, major });
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) {
          toast.push(
            err instanceof Error ? err.message : "加载聚合数据失败",
            "error",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [school, major, router, toast]);

  if (redirecting || loading) return <LoadingState />;

  // 无数据或样本为 0
  if (!data || data.sample_count === 0) {
    return (
      <div className="space-y-6">
        <Link
          href="/community"
          className="inline-flex items-center text-sm text-brand-600 hover:underline"
        >
          <ArrowLeft className="h-4 w-4" /> 返回社区数据
        </Link>
        <EmptyState
          title="暂无社区数据"
          description={`「${school} · ${major}」还没有人提交去向报告`}
          action={
            <Link href="/community">
              <Button>
                <Users className="h-4 w-4" /> 我来分享去向
              </Button>
            </Link>
          }
        />
      </div>
    );
  }

  const insufficient = !data.sufficient || data.sample_count < 3;
  const contextLabel = `${school}${major}`;

  return (
    <div className="space-y-6">
      <Link
        href="/community"
        className="inline-flex items-center text-sm text-brand-600 hover:underline"
      >
        <ArrowLeft className="h-4 w-4" /> 返回社区数据
      </Link>

      <div>
        <h1 className="page-title">{school} · {major}</h1>
        <p className="text-sm text-slate-500 mt-1">
          社区聚合数据 · 共 {data.sample_count} 份匿名报告
        </p>
      </div>

      {/* 样本数提示 */}
      {insufficient ? (
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
          <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" />
          <div>
            <p className="text-sm font-medium text-amber-800">样本不足</p>
            <p className="text-xs text-amber-700 mt-0.5">
              当前仅 {data.sample_count} 份样本（建议至少 3 份），数据仅供参考，请谨慎解读。
            </p>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 px-4 py-3">
          <Users className="h-5 w-5 shrink-0 text-green-600" />
          <p className="text-sm text-green-800">
            已聚合 {data.sample_count} 份匿名报告，数据具备一定参考价值
          </p>
        </div>
      )}

      {/* 去向分布 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4">毕业去向分布</h2>
        {data.destination_distribution ? (
          <CommunityDestinationPie
            distribution={data.destination_distribution}
            contextLabel={contextLabel}
          />
        ) : (
          <p className="text-sm text-slate-400">暂无去向分布数据</p>
        )}
      </div>

      {/* 热门雇主 & 城市 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4">热门雇主 / 城市</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-medium text-slate-600 mb-2">热门雇主 Top10</h3>
            <RankingBar data={data.top_employers ?? []} title="热门雇主" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-slate-600 mb-2">城市分布 Top10</h3>
            <RankingBar data={data.top_cities ?? []} title="城市分布" />
          </div>
        </div>
      </div>

      {/* 热门行业 */}
      {data.top_industries && data.top_industries.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-4">热门行业</h2>
          <RankingBar data={data.top_industries} title="热门行业" />
        </div>
      )}

      {/* 薪资分布 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4">薪资分布</h2>
        {data.salary_distribution ? (
          <SalaryDistributionBar distribution={data.salary_distribution} />
        ) : (
          <p className="text-sm text-slate-400">暂无薪资分布数据</p>
        )}
      </div>

      {/* CTA */}
      <div className="card bg-brand-50 border-brand-100">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-slate-800">你的去向是什么？</p>
            <p className="text-sm text-slate-500">
              分享你的去向，让这份数据更准确
            </p>
          </div>
          <Link href="/community">
            <Button>
              <Users className="h-4 w-4" /> 提交我的去向
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function CommunityResultPage() {
  // useSearchParams 必须包裹在 Suspense 边界中（Next.js 14 要求）
  return (
    <Suspense fallback={<LoadingState />}>
      <CommunityResultContent />
    </Suspense>
  );
}
