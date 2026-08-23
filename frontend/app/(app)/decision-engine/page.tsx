"use client";

// frontend/app/(app)/decision-engine/page.tsx
// 三路决策引擎 — 输入学生档案，对比考研/考公/就业（每个数字可溯源）

import { useState } from "react";
import { Lightbulb } from "lucide-react";
import { pathDecisionApi } from "@/lib/api";
import { EngineForm } from "@/components/decision-engine/engine-form";
import { PathResultCard } from "@/components/decision-engine/path-result-card";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import type { DecisionEngineInput, DecisionEngineResponse } from "@/types/path-comparison";

export default function DecisionEnginePage() {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DecisionEngineResponse | null>(null);
  const [input, setInput] = useState<DecisionEngineInput | null>(null);

  const handleAnalyze = async (values: DecisionEngineInput) => {
    setLoading(true);
    setInput(values);
    try {
      const data = await pathDecisionApi.analyze(values);
      setResult(data);
      toast.success("三路对比已生成，展开卡片查看数据来源");
    } catch {
      setResult(null);
      toast.error("对比失败，请检查输入后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* 页头 */}
      <div>
        <h1 className="text-2xl font-bold text-ink-800">三路决策引擎</h1>
        <p className="mt-1 text-ink-500">
          输入你的专业与基本情况，用现有真实数据对比考研 / 考公 / 就业三条路——每个数字都可溯源。
        </p>
      </div>

      {/* 输入表单 */}
      <EngineForm loading={loading} onSubmit={handleAnalyze} initial={input ?? undefined} />

      {/* 结果区 */}
      {loading && (
        <LoadingState text="正在聚合真实数据生成三路对比…" />
      )}

      {!loading && result && (
        <div className="space-y-5">
          {/* 档案摘要 */}
          <div className="flex flex-wrap items-center gap-2 rounded-xl border border-paper-200 bg-paper-50/70 px-4 py-3 text-xs text-ink-500">
            <span className="font-medium text-ink-700">当前档案：</span>
            {Object.entries(result.input).map(([k, v]) => (
              <span key={k} className="rounded-full bg-white border border-paper-200 px-2 py-0.5">
                {k === "major" ? "专业" : k === "region" ? "地区" : k === "school_tier" ? "层次" : "届别"}：{String(v)}
              </span>
            ))}
          </div>

          {/* 三路卡片 */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {result.metrics.map((m) => (
              <PathResultCard key={m.path_type} metric={m} />
            ))}
          </div>

          {/* 综合建议 */}
          <div className="rounded-xl border border-purple-200 bg-gradient-to-br from-purple-50 via-fuchsia-50 to-indigo-50 p-5">
            <div className="flex items-start gap-3">
              <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-fuchsia-600 text-white">
                <Lightbulb className="h-4 w-4" />
              </span>
              <div className="flex-1 min-w-0">
                <h3 className="mb-2 text-base font-semibold text-ink-900">综合建议</h3>
                <div className="text-sm leading-relaxed text-ink-700 whitespace-pre-line">
                  {result.recommendation}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {!loading && !result && (
        <EmptyState
          title="输入专业，生成你的三路对比"
          description="引擎会用数据库里的真实分数线、岗位表与薪资数据做对比，每个数字都有来源。数据覆盖有限时会如实标注。"
        />
      )}
    </div>
  );
}
