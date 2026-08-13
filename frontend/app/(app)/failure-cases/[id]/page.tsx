"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import {
  ArrowLeft,
  HeartCrack,
  Eye,
  ThumbsUp,
  BookOpen,
  AlertCircle,
  Lightbulb,
  Route,
  ArrowRight,
} from "lucide-react";
import { failureCaseApi } from "@/lib/api";
import {
  PATH_LABELS,
  STAGE_LABELS,
  PATH_BADGE_COLORS,
} from "@/types/failure-case";
import { Badge, Button } from "@/components/ui/form-controls";
import { LoadingState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";

export default function FailureCaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const caseId = params.id as string;

  const { data: caseData, isLoading } = useSWR(
    `/api/failure-cases/${caseId}`,
    () => failureCaseApi.get(caseId),
  );

  const [helpfulLoading, setHelpfulLoading] = useState(false);
  const [localHelpfulCount, setLocalHelpfulCount] = useState<number | null>(
    null,
  );

  const handleMarkHelpful = async () => {
    if (!user) {
      toast.info("请先登录后再操作");
      router.push("/login");
      return;
    }
    if (helpfulLoading) return;
    setHelpfulLoading(true);
    try {
      const result = await failureCaseApi.markHelpful(caseId);
      setLocalHelpfulCount(result.helpful_count);
      toast.success("感谢你的反馈！");
    } catch {
      toast.error("操作失败，请稍后重试");
    } finally {
      setHelpfulLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-3xl px-4 py-8">
          <LoadingState text="加载案例详情中…" />
        </div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-3xl px-4 py-8">
          <div className="rounded-xl border border-dashed border-paper-300 bg-white px-6 py-14 text-center">
            <HeartCrack className="mx-auto h-10 w-10 text-ink-300" strokeWidth={1.5} />
            <p className="mt-4 font-display text-base font-medium text-ink-700">
              案例不存在或未通过审核
            </p>
            <Link
              href="/failure-cases"
              className="mt-4 inline-flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 font-medium"
            >
              <ArrowLeft className="h-4 w-4" />
              返回案例库
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const helpfulCount = localHelpfulCount ?? caseData.helpful_count;

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Back link */}
        <Link
          href="/failure-cases"
          className="inline-flex items-center gap-1.5 text-sm text-ink-400 hover:text-ink-700 transition-colors mb-6"
        >
          <ArrowLeft className="h-4 w-4" />
          返回案例库
        </Link>

        {/* Header */}
        <div className="mb-6">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Badge color={PATH_BADGE_COLORS[caseData.path_type]}>
              {PATH_LABELS[caseData.path_type]}
            </Badge>
            <Badge color="slate">{STAGE_LABELS[caseData.stage]}</Badge>
            <span className="text-xs text-ink-400">{caseData.author_role}</span>
          </div>
          <h1 className="font-display text-2xl font-bold text-ink-800 leading-snug mb-3">
            {caseData.title}
          </h1>
          <div className="flex items-center gap-4 text-xs text-ink-400">
            <span className="inline-flex items-center gap-1">
              <Eye className="h-3.5 w-3.5" />
              {caseData.view_count} 次浏览
            </span>
            <span className="inline-flex items-center gap-1">
              <ThumbsUp className="h-3.5 w-3.5" />
              {helpfulCount} 人觉得有帮助
            </span>
            <span>
              {new Date(caseData.created_at).toLocaleDateString("zh-CN")}
            </span>
          </div>
        </div>

        {/* Story */}
        <section className="mb-8 rounded-xl border border-paper-300 bg-white p-6">
          <h2 className="font-display text-lg font-semibold text-ink-800 mb-4 flex items-center gap-2">
            <HeartCrack className="h-5 w-5 text-brand-500" strokeWidth={1.8} />
            我的故事
          </h2>
          <div className="space-y-4">
            {caseData.story.split("\n\n").map((paragraph, idx) => (
              <p key={idx} className="text-sm text-ink-600 leading-relaxed">
                {paragraph}
              </p>
            ))}
          </div>
        </section>

        {/* Lessons */}
        {caseData.lessons.length > 0 && (
          <section className="mb-8 rounded-xl border border-amber-200 bg-amber-50 p-6">
            <h2 className="font-display text-lg font-semibold text-amber-800 mb-4 flex items-center gap-2">
              <BookOpen className="h-5 w-5" strokeWidth={1.8} />
              教训提炼
            </h2>
            <ul className="space-y-3">
              {caseData.lessons.map((lesson, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-amber-200 text-xs font-bold text-amber-800">
                    {idx + 1}
                  </span>
                  <p className="text-sm text-amber-900 leading-relaxed pt-0.5">
                    {lesson}
                  </p>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Regrets */}
        {caseData.regrets.length > 0 && (
          <section className="mb-8 rounded-xl border border-red-200 bg-red-50 p-6">
            <h2 className="font-display text-lg font-semibold text-red-800 mb-4 flex items-center gap-2">
              <AlertCircle className="h-5 w-5" strokeWidth={1.8} />
              后悔的事
            </h2>
            <ul className="space-y-3">
              {caseData.regrets.map((regret, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-red-400" />
                  <p className="text-sm text-red-900 leading-relaxed">
                    {regret}
                  </p>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* What would I do */}
        <section className="mb-8 rounded-xl border border-brand-200 bg-brand-50 p-6">
          <h2 className="font-display text-lg font-semibold text-brand-800 mb-4 flex items-center gap-2">
            <Lightbulb className="h-5 w-5" strokeWidth={1.8} />
            如果重来我会这样做
          </h2>
          <div className="space-y-3">
            {caseData.what_would_i_do.split("\n").map((line, idx) => (
              <p key={idx} className="text-sm text-brand-900 leading-relaxed">
                {line}
              </p>
            ))}
          </div>
        </section>

        {/* Helpful button */}
        <div className="mb-8 flex items-center justify-center gap-4">
          <Button
            variant="secondary"
            onClick={handleMarkHelpful}
            loading={helpfulLoading}
            className="px-6"
          >
            <ThumbsUp className="h-4 w-4" />
            有帮助（{helpfulCount}）
          </Button>
        </div>

        {/* CTA: Career Simulator */}
        <div className="rounded-xl border border-brand-300 bg-gradient-to-br from-brand-50 to-brand-100 p-6 text-center">
          <Route className="mx-auto h-8 w-8 text-brand-500 mb-3" strokeWidth={1.5} />
          <h3 className="font-display text-lg font-semibold text-ink-800 mb-2">
            失败不是终点，而是看清下一条路的机会
          </h3>
          <p className="text-sm text-ink-500 mb-4 max-w-md mx-auto leading-relaxed">
            用职业路径模拟器探索你的可能性，基于真实数据推演不同路径的预期收益与风险。
          </p>
          <Link
            href="/career-simulator"
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
          >
            打开职业路径模拟器
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
