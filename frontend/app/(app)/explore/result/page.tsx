"use client";

import { Suspense, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Compass, Users } from "lucide-react";
import { employmentApi, communityApi } from "@/lib/api";
import { Button } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { EmploymentDestinationPie, RankingBar, TrendLine } from "@/components/charts";
import { RATE_LABEL } from "@/lib/constants";
import type { CommunityAggregate, EmploymentSearchResult } from "@/types";

// 优化：讨论区组件较大(17KB)且在页面下方，按需加载减少首屏 JS 体积
const DiscussionSection = dynamic(
  () => import("@/components/discussion-section").then((m) => m.DiscussionSection),
  {
    ssr: false,
    loading: () => <LoadingState />,
  },
);

const COMMUNITY_COMPARISON_KEYS = [
  "employment",
  "further_study",
  "civil_service",
  "abroad",
  "startup",
  "gap_year",
];

/** 将中文编码为 Base64 并 URL 编码，用于跳转聚合结果页 */
function encodeParam(value: string): string {
  return encodeURIComponent(btoa(unescape(encodeURIComponent(value))));
}

function ExploreResultContent() {
  const router = useRouter();
  const toast = useToast();
  const searchParams = useSearchParams();
  // 从 URL 读取 Base64 编码的参数并解码为中文
  const sEncoded = searchParams.get("s") ?? "";
  const mEncoded = searchParams.get("m") ?? "";
  const school = sEncoded ? decodeURIComponent(escape(atob(sEncoded))) : "";
  const major = mEncoded ? decodeURIComponent(escape(atob(mEncoded))) : "";

  const [data, setData] = useState<EmploymentSearchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(false);

  // 社区聚合数据（辅助信息，独立加载，失败静默处理）
  const [communityData, setCommunityData] = useState<CommunityAggregate | null>(null);
  const [communityLoading, setCommunityLoading] = useState(true);

  useEffect(() => {
    // 无参数（直接访问 /explore/result）时重定向回搜索页
    if (!school || !major) {
      setRedirecting(true);
      router.replace("/explore");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const result = await employmentApi.search({ school, major });
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) {
          toast.push(
            err instanceof Error ? err.message : "搜索失败",
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

  // 拉取同校同专业的社区聚合数据（静默失败，不阻断官方数据展示）
  useEffect(() => {
    if (!school || !major) return;
    let cancelled = false;
    (async () => {
      try {
        const result = await communityApi.aggregate({ school, major });
        if (!cancelled) setCommunityData(result);
      } catch {
        if (!cancelled) setCommunityData(null);
      } finally {
        if (!cancelled) setCommunityLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [school, major]);

  if (redirecting || loading) return <LoadingState />;

  if (!data || !data.school || data.records.length === 0) {
    return (
      <div className="space-y-6">
        <Link href="/explore" className="inline-flex items-center text-sm text-brand-600 hover:underline">
          <ArrowLeft className="h-4 w-4" /> 返回搜索
        </Link>
        <EmptyState
          title="未找到匹配数据"
          description={`暂无「${school} · ${major}」的就业去向数据`}
          action={
            <Link href="/explore">
              <Button>查看已收录学校</Button>
            </Link>
          }
        />
        <DiscussionSection
          topicType="school_major"
          topicKey={`${school}|${major}`}
          title={`${school} · ${major} 讨论`}
        />
      </div>
    );
  }

  const latest = data.records[0];

  // 社区数据对比：官方比例（0~1）vs 社区计数（需换算为比例）
  const communityDist = communityData?.destination_distribution ?? null;
  const communityTotal = communityDist
    ? Object.values(communityDist).reduce((a, b) => a + b, 0)
    : 0;
  const hasCommunity =
    !!communityData && communityData.sample_count > 0 && communityTotal > 0;

  // 构造对比行：仅保留官方或社区任一有数据的去向类型
  const comparisonRows = COMMUNITY_COMPARISON_KEYS.map((key) => {
    const officialRate = latest.rates[key as keyof typeof latest.rates];
    const officialPct =
      officialRate !== null && officialRate !== undefined
        ? Math.round(officialRate * 100)
        : null;
    const communityCount = communityDist?.[key] ?? 0;
    const communityPct =
      hasCommunity && communityCount > 0
        ? Math.round((communityCount / communityTotal) * 100)
        : null;
    return {
      key,
      label: RATE_LABEL[key] ?? key,
      officialPct,
      communityPct,
    };
  }).filter(
    (r) => r.officialPct !== null || r.communityPct !== null,
  );

  return (
    <div className="space-y-6">
      <Link href="/explore" className="inline-flex items-center text-sm text-brand-600 hover:underline">
        <ArrowLeft className="h-4 w-4" /> 返回搜索
      </Link>

      <div>
        <h1 className="page-title">{data.school.name} · {data.major}</h1>
        <p className="text-sm text-slate-500 mt-1">
          {data.records.length} 条记录 · 数据来源：高校就业质量年度报告
        </p>
      </div>

      {/* 卡片一：去向分布 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4">毕业去向分布（{latest.year}年）</h2>
        <EmploymentDestinationPie
          record={latest}
          contextLabel={`${data.school.name}${data.major ?? ""}`}
        />
        {latest.total_graduates && (
          <p className="text-center text-sm text-slate-400 mt-2">
            毕业总人数：{latest.total_graduates}人
          </p>
        )}
      </div>

      {/* 卡片二：排名 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4">重点单位 / 升学去向排名</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-medium text-slate-600 mb-2">就业单位 Top10</h3>
            <RankingBar ranking={latest.employer_ranking} title="就业单位" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-slate-600 mb-2">升学去向 Top10</h3>
            <RankingBar ranking={latest.school_for_further_study} title="升学去向" />
          </div>
        </div>
      </div>

      {/* 卡片三：趋势 */}
      {data.trend && data.trend.years.length > 1 && (
        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-4">多年趋势</h2>
          <TrendLine
            trend={data.trend}
            contextLabel={`${data.school.name}${data.major ?? ""}`}
          />
        </div>
      )}

      {/* 社区数据卡片：官方 vs 社区对比 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
          <Users className="h-4 w-4 text-brand-500" />
          社区数据
        </h2>
        {communityLoading ? (
          <p className="text-sm text-slate-400">加载社区数据中…</p>
        ) : hasCommunity ? (
          <div className="space-y-3">
            <p className="text-sm text-slate-500">
              已聚合 <span className="font-semibold text-brand-600">
                {communityData!.sample_count}
              </span> 份匿名报告，与官方数据对比：
            </p>
            {comparisonRows.length > 0 ? (
              <div className="overflow-hidden rounded-lg border border-slate-100">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs text-slate-500">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">去向类型</th>
                      <th className="px-3 py-2 text-right font-medium">官方</th>
                      <th className="px-3 py-2 text-right font-medium">社区</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {comparisonRows.map((r) => (
                      <tr key={r.key}>
                        <td className="px-3 py-2 text-slate-700">{r.label}</td>
                        <td className="px-3 py-2 text-right text-slate-600">
                          {r.officialPct !== null ? `${r.officialPct}%` : "—"}
                        </td>
                        <td className="px-3 py-2 text-right text-brand-600">
                          {r.communityPct !== null ? `${r.communityPct}%` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-slate-400">暂无可对比的去向分布数据</p>
            )}
            <Link
              href={`/community/result?s=${encodeParam(school)}&m=${encodeParam(major)}`}
              className="inline-flex items-center text-sm text-brand-600 hover:underline"
            >
              查看完整社区聚合结果 →
            </Link>
          </div>
        ) : (
          <div className="flex flex-col items-start gap-3">
            <p className="text-sm text-slate-500">
              「{school} · {major}」暂无社区数据，官方数据之外的真实去向需要你的分享。
            </p>
            <Link href="/community">
              <Button variant="secondary">
                <Users className="h-4 w-4" /> 分享你的去向，帮助学弟学妹
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* 讨论区 */}
      <DiscussionSection
        topicType="school_major"
        topicKey={`${school}|${major}`}
        title={`${school} · ${major} 讨论`}
      />

      {/* CTA */}
      <div className="card bg-brand-50 border-brand-100">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-slate-800">你的去向是什么？</p>
            <p className="text-sm text-slate-500">记录你的去向决策，与同专业数据对比</p>
          </div>
          <Link href="/decisions">
            <Button>
              <Compass className="h-4 w-4" /> 记录去向决策
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ExploreResultPage() {
  // useSearchParams 必须包裹在 Suspense 边界中（Next.js 14 要求）
  return (
    <Suspense fallback={<LoadingState />}>
      <ExploreResultContent />
    </Suspense>
  );
}
