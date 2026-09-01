"use client";

// frontend/app/(app)/decision-engine/page.tsx
// 三路决策引擎 — 输入学生档案，生成「我的报考决策报告」：
// 报告式布局（三路横评 / 分数三档 / 岗位与院校分析 / 同分人群去向 / 行动时间线 / 综合建议）
// + 结果回传闭环 + 分享（匿名链接 / 复制文案）。

import { useMemo, useState } from "react";
import { pathDecisionApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { EngineForm } from "@/components/decision-engine/engine-form";
import { DecisionReport } from "@/components/decision-engine/decision-report";
import { ShareReportActions } from "@/components/decision-engine/share-report-actions";
import { OutcomeForm } from "@/components/decision-engine/outcome-form";
import { ReciprocityBlock } from "@/components/decision-engine/reciprocity-block";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import type { DecisionEngineInput, DecisionEngineResponse } from "@/types/path-comparison";

export default function DecisionEnginePage() {
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DecisionEngineResponse | null>(null);
  const [input, setInput] = useState<DecisionEngineInput | null>(null);

  // 身份包预填（W1-D3/D4）：档案里的报考身份做底，本次会话已提交的 input 优先
  const initial = useMemo<Partial<DecisionEngineInput> | undefined>(() => {
    if (!user) return input ?? undefined;
    return {
      ...(input ?? {}),
      fresh_status: input?.fresh_status ?? user.fresh_status ?? undefined,
      party_status: input?.party_status ?? user.party_status ?? undefined,
      education: input?.education ?? user.education ?? undefined,
      gender: input?.gender ?? user.gender ?? undefined,
      has_grassroots: input?.has_grassroots ?? user.has_grassroots ?? undefined,
    };
  }, [user, input]);

  const handleAnalyze = async (values: DecisionEngineInput) => {
    setLoading(true);
    setInput(values);
    try {
      const data = await pathDecisionApi.analyze(values);
      setResult(data);
      toast.success("报考决策报告已生成，每个数字都可展开查看来源");
    } catch {
      setResult(null);
      toast.error("对比失败，请检查输入后重试");
    } finally {
      setLoading(false);
    }
  };

  const handleOutcomeSaved = (outcome: NonNullable<DecisionEngineResponse["outcome"]>) => {
    setResult((prev) => (prev ? { ...prev, outcome } : prev));
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* 页头 */}
      <div>
        <h1 className="text-2xl font-bold text-ink-800">三路决策引擎</h1>
        <p className="mt-1 text-ink-500">
          输入你的专业与基本情况，用现有真实数据对比考研 / 考公 / 就业三条路——生成属于你的「报考决策报告」，每个数字都可溯源。
        </p>
      </div>

      {/* 输入表单 */}
      <EngineForm loading={loading} onSubmit={handleAnalyze} initial={initial} />

      {/* 结果区 */}
      {loading && (
        <LoadingState text="正在聚合真实数据生成报考决策报告…" />
      )}

      {!loading && result && (
        <div className="space-y-5">
          {/* 互惠回传引导（回传闭环的信任底座，展示真实回传量） */}
          <ReciprocityBlock />

          {/* 报告式布局（截图/打印友好） */}
          <DecisionReport result={result} />

          {/* 分享（匿名链接 + 复制文案） */}
          <ShareReportActions result={result} />

          {/* 结果回传（决策飞轮闭环第一圈） */}
          <OutcomeForm decisionId={result.id} outcome={result.outcome} onSaved={handleOutcomeSaved} />
        </div>
      )}

      {!loading && !result && (
        <EmptyState
          title="输入专业，生成你的报考决策报告"
          description="引擎会用数据库里的真实分数线、岗位表与薪资数据生成报告，每个数字都有来源。数据覆盖有限时会如实标注。"
        />
      )}
    </div>
  );
}
