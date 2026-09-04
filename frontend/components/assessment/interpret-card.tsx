"use client";

// 测评 × 专有数据 → 专属路径解读卡（护城河本体）。
// 铁律：一切数字来自后端真实数据；空态诚实展示，绝不前端编造。
import Link from "next/link";
import { Compass, Database, Loader2, Users } from "lucide-react";
import { PathResultCard } from "@/components/decision-engine/path-result-card";
import { PositionAnalysisCard } from "@/components/decision-engine/position-analysis-card";
import { SchoolAnalysisCard } from "@/components/decision-engine/school-analysis-card";
import type { AssessmentInterpretResponse } from "@/types";
import type { PathMetrics } from "@/types/path-comparison";

const LEAN_LABELS: Record<string, string> = {
  kaoyan: "考研深造",
  civil_service: "考公进体制",
  employment: "直接就业",
};

/** major_prospect 后端为聚合字典，这里只声明本卡消费的字段 */
interface ProspectView {
  matched_major?: string;
  exact_match?: boolean;
  category?: string;
  industries?: Array<{ industry: string; salary_non_private: number }>;
  grad_paths?: Array<{ school_name: string; major_name?: string; score_line?: number }>;
  civil_service?: { level?: string; label?: string; note?: string };
  tier_fact?: string;
}

export interface InterpretCardProps {
  data: AssessmentInterpretResponse | null;
  loading: boolean;
  error: string | null;
}

export function InterpretCard({ data, loading, error }: InterpretCardProps) {
  if (loading && !data) {
    return (
      <div className="card flex items-center gap-3 py-6">
        <Loader2 className="h-5 w-5 animate-spin text-brand-600" />
        <p className="text-sm text-ink-500">正在结合你的真实报考数据生成专属解读…</p>
      </div>
    );
  }
  if (error && !data) {
    return (
      <div className="card space-y-1">
        <h2 className="font-display font-semibold text-ink-800">你的专属路径（基于真实数据）</h2>
        <p className="text-sm text-ink-500">
          专属解读暂时没能生成（{error}）。不影响上方测评结果，稍后可重试。
        </p>
      </div>
    );
  }
  if (!data) return null;

  if (!data.has_assessment) {
    return (
      <div className="card space-y-1">
        <h2 className="font-display font-semibold text-ink-800">你的专属路径（基于真实数据）</h2>
        <p className="text-sm text-ink-500">{data.message ?? "完成测评后可解锁。"}</p>
      </div>
    );
  }

  const interp = data.interpretation;
  const paths = (data.paths ?? []) as PathMetrics[];
  const prospect = (data.major_prospect ?? {}) as ProspectView;
  const peer = data.peer_destinations;

  return (
    <div className="card space-y-4">
      <div className="flex items-center gap-2">
        <Compass className="h-4 w-4 text-brand-600" />
        <h2 className="font-display font-semibold text-ink-800">
          你的专属路径（基于真实数据）
        </h2>
      </div>

      {/* 测评 lean + 理由 */}
      {interp && (
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            {interp.primary_lean && (
              <span className="inline-flex items-center rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-brand-700">
                偏好：{LEAN_LABELS[interp.primary_lean] ?? interp.primary_lean}
              </span>
            )}
            <span className="text-[10px] text-ink-400">测评只提供方向偏好，不作报考结论</span>
          </div>
          {interp.reason && (
            <p className="text-sm text-ink-600 leading-relaxed">{interp.reason}</p>
          )}
        </div>
      )}

      {/* 三路真实数据：有则渲染决策引擎同款卡，无则诚实引导补档案 */}
      {paths.length > 0 ? (
        <div className="space-y-3">
          {paths.map((m) => (
            <PathResultCard key={m.path_type} metric={m} />
          ))}
        </div>
      ) : (
        data.recommendation && (
          <div className="rounded-xl border border-paper-200 bg-paper-50 p-3.5">
            <p className="text-sm text-ink-600 leading-relaxed">{data.recommendation}</p>
            <Link
              href="/profile"
              className="mt-1.5 inline-block text-xs font-medium text-brand-600 hover:underline"
            >
              前往个人档案补全 →
            </Link>
          </div>
        )
      )}

      {data.position_analysis && <PositionAnalysisCard analysis={data.position_analysis} />}
      {data.school_analysis && <SchoolAnalysisCard analysis={data.school_analysis} />}

      {/* 同分人群去向：无样本时诚实占位，绝不编造 */}
      {peer && (
        <div className="rounded-xl border border-paper-200 p-3.5 space-y-2">
          <div className="flex items-center gap-1.5 text-sm font-semibold text-ink-700">
            <Users className="h-3.5 w-3.5 text-ink-400" />
            同分人群去向
          </div>
          {peer.has_data && peer.distribution.length > 0 ? (
            <div className="space-y-1.5">
              <p className="text-xs text-ink-400">基于 {peer.peer_count} 位相近分数用户的真实回传</p>
              {peer.distribution.map((d) => (
                <div key={d.label} className="flex items-center justify-between text-sm">
                  <span className="text-ink-600">{d.label}</span>
                  <span className="tabular-nums text-ink-500">
                    {d.count} 人 · {Math.round(d.rate * 100)}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-ink-400">
              暂无相近分数的回传样本——你是最早回传结果的一批，你的选择会成为后来人的参照。
            </p>
          )}
        </div>
      )}

      {/* 专业前景紧凑摘要（完整分析去专业前景页） */}
      {(prospect.civil_service?.label ||
        prospect.industries?.length ||
        prospect.grad_paths?.length ||
        prospect.tier_fact) && (
        <div className="rounded-xl border border-paper-200 p-3.5 space-y-2">
          <div className="flex items-center gap-1.5 text-sm font-semibold text-ink-700">
            <Database className="h-3.5 w-3.5 text-ink-400" />
            专业前景速览{prospect.matched_major ? ` · ${prospect.matched_major}` : ""}
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            {prospect.civil_service?.label && (
              <span className="rounded-full border border-paper-200 bg-paper-50 px-2 py-0.5 text-ink-600">
                {prospect.civil_service.label}
              </span>
            )}
            {(prospect.industries ?? []).slice(0, 3).map((i) => (
              <span
                key={i.industry}
                className="rounded-full border border-paper-200 bg-paper-50 px-2 py-0.5 text-ink-600"
              >
                {i.industry} 非私营年均 {(i.salary_non_private / 10000).toFixed(1)} 万
              </span>
            ))}
          </div>
          {(prospect.grad_paths ?? []).slice(0, 3).map((g) => (
            <p key={`${g.school_name}-${g.major_name ?? ""}`} className="text-xs text-ink-500">
              考研参考：{g.school_name}
              {g.score_line ? ` 复试线 ${g.score_line} 分` : ""}
            </p>
          ))}
          {prospect.tier_fact && (
            <p className="text-xs text-ink-500 leading-relaxed">出身层次参考：{prospect.tier_fact}</p>
          )}
          <Link
            href="/major-prospects"
            className="inline-block text-xs font-medium text-brand-600 hover:underline"
          >
            查看完整专业前景分析 →
          </Link>
        </div>
      )}

      {/* 溯源脚注 */}
      {data.data_notes && data.data_notes.length > 0 && (
        <div className="border-t border-paper-100 pt-2.5 space-y-1">
          {data.data_notes.map((n) => (
            <p key={n} className="text-[10px] leading-relaxed text-ink-400">
              · {n}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
