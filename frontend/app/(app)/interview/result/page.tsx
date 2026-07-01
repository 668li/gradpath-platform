"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, AlertTriangle, Briefcase } from "lucide-react";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { interviewApi } from "@/lib/api";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { RankingBar } from "@/components/employment-charts";
import { DiscussionSection } from "@/components/discussion-section";
import {
  INTERVIEW_DIMENSION_LABEL,
  INTERVIEW_DIMENSIONS,
  INTERVIEW_RESULT_LABEL,
  INTERVIEW_RESULT_COLOR,
} from "@/lib/constants";
import type { InterviewAggregate } from "@/types";

const CHART_HEIGHT = 300;

function InterviewResultContent() {
  const router = useRouter();
  const toast = useToast();
  const searchParams = useSearchParams();
  const cEncoded = searchParams.get("c") ?? "";
  const company = cEncoded ? decodeURIComponent(escape(atob(cEncoded))) : "";

  const [data, setData] = useState<InterviewAggregate | null>(null);
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    if (!company) {
      setRedirecting(true);
      router.replace("/interview");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const result = await interviewApi.aggregate({ company });
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
  }, [company, router, toast]);

  if (redirecting || loading) return <LoadingState />;

  if (!data || data.sample_count === 0) {
    return (
      <div className="space-y-6">
        <Link
          href="/interview"
          className="inline-flex items-center text-sm text-brand-600 hover:underline"
        >
          <ArrowLeft className="h-4 w-4" /> 返回面试经验
        </Link>
        <EmptyState
          title="暂无面试数据"
          description={`「${company}」还没有人分享面试经历`}
          action={
            <Link href="/interview">
              <Button>
                <Briefcase className="h-4 w-4" /> 我来分享面试经历
              </Button>
            </Link>
          }
        />
        <DiscussionSection
          topicType="company_position"
          topicKey={`${company}|`}
          title={`${company} 面试讨论`}
        />
      </div>
    );
  }

  const insufficient = !data.sufficient || data.sample_count < 3;

  // 雷达图数据
  const radarData = data.dimension_frequency
    ? INTERVIEW_DIMENSIONS.map((dim) => ({
        dimension: INTERVIEW_DIMENSION_LABEL[dim] ?? dim,
        frequency: Math.round((data.dimension_frequency![dim] ?? 0) * 100),
      }))
    : [];

  // 饼图数据
  const pieData = data.result_distribution
    ? Object.entries(data.result_distribution)
        .filter(([, v]) => v > 0)
        .map(([key, value]) => ({
          name: INTERVIEW_RESULT_LABEL[key] ?? key,
          value: value,
          key,
        }))
    : [];

  return (
    <div className="space-y-6">
      <Link
        href="/interview"
        className="inline-flex items-center text-sm text-brand-600 hover:underline"
      >
        <ArrowLeft className="h-4 w-4" /> 返回面试经验
      </Link>

      <div>
        <h1 className="page-title">{company}</h1>
        <p className="text-sm text-slate-500 mt-1">
          面试聚合数据 · 共 {data.sample_count} 份匿名报告
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
          <Briefcase className="h-5 w-5 shrink-0 text-green-600" />
          <p className="text-sm text-green-800">
            已聚合 {data.sample_count} 份匿名报告，数据具备一定参考价值
          </p>
        </div>
      )}

      {/* 基本信息 */}
      <div className="grid grid-cols-2 gap-4">
        <div className="card text-center">
          <p className="text-2xl font-bold text-brand-600">
            {data.avg_difficulty ? `${data.avg_difficulty}/5` : "—"}
          </p>
          <p className="text-xs text-slate-500">平均难度</p>
        </div>
        <div className="card text-center">
          <p className="text-2xl font-bold text-green-600">
            {data.avg_rounds ? `${data.avg_rounds}` : "—"}
          </p>
          <p className="text-xs text-slate-500">平均轮数</p>
        </div>
      </div>

      {/* 考察维度雷达图 */}
      {radarData.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-4">考察维度频率</h2>
          <div
            role="img"
            aria-label={`${company}面试考察维度频率：${radarData.map((d) => `${d.dimension}${d.frequency}%`).join("，")}`}
          >
            <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis
                  dataKey="dimension"
                  tick={{ fontSize: 12, fill: "#64748b" }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  tick={{ fontSize: 10, fill: "#94a3b8" }}
                />
                <Radar
                  name="频率"
                  dataKey="frequency"
                  stroke="#3377f6"
                  fill="#3377f6"
                  fillOpacity={0.3}
                />
                <Tooltip
                  formatter={(v: number) => `${v}%`}
                />
              </RadarChart>
            </ResponsiveContainer>
            <span className="sr-only">
              {`${company}面试考察维度频率：${radarData.map((d) => `${d.dimension}${d.frequency}%`).join("，")}`}
            </span>
          </div>
        </div>
      )}

      {/* 面试结果分布 */}
      {pieData.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-4">面试结果分布</h2>
          <div
            role="img"
            aria-label={`${company}面试结果分布：${pieData.map((d) => `${d.name}${(d.value * 100).toFixed(0)}%`).join("，")}`}
          >
            <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ name, value }) =>
                    `${name} ${(value * 100).toFixed(0)}%`
                  }
                >
                  {pieData.map((d) => (
                    <Cell key={d.key} fill={INTERVIEW_RESULT_COLOR[d.key] ?? "#999"} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
                />
              </PieChart>
            </ResponsiveContainer>
            <span className="sr-only">
              {`${company}面试结果分布：${pieData.map((d) => `${d.name}${(d.value * 100).toFixed(0)}%`).join("，")}`}
            </span>
          </div>
        </div>
      )}

      {/* 常见岗位 */}
      {data.common_positions && data.common_positions.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-4">常见岗位</h2>
          <RankingBar data={data.common_positions} title="常见岗位" />
        </div>
      )}

      {/* 讨论区 */}
      <DiscussionSection
        topicType="company_position"
        topicKey={`${company}|`}
        title={`${company} 面试讨论`}
      />

      {/* CTA */}
      <div className="card bg-brand-50 border-brand-100">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-slate-800">你的面试经历是什么？</p>
            <p className="text-sm text-slate-500">
              分享你的面试经验，让这份数据更准确
            </p>
          </div>
          <Link href="/interview">
            <Button>
              <Briefcase className="h-4 w-4" /> 提交我的经历
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function InterviewResultPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <InterviewResultContent />
    </Suspense>
  );
}
