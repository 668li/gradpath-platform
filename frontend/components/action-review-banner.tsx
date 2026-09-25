"use client";

import { useCallback, useEffect, useState } from "react";
import { AlarmClock, Check, ThumbsDown, Clock3 } from "lucide-react";
import { retrospectivesApi } from "@/lib/api";
import type { RetroActionCard } from "@/lib/api/retrospectives";
import { Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";

/**
 * 到期行动卡复审横幅（2026-09-25 复盘深化）。
 *
 * KPT Try 复审 + M&M 会议开场核对的同构：新建复盘/进复盘页第一件事 =
 * "你上次说要试的 X，到期了，结果如何？"——这是复盘闭环的留存钩子，
 * 也是原则库的质检线（effective 的行动卡自动升级为已验证原则）。
 */

export function ActionReviewBanner({ onChanged }: { onChanged?: () => void }) {
  const toast = useToast();
  const [actions, setActions] = useState<RetroActionCard[]>([]);
  const [reviewing, setReviewing] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const resp = await retrospectivesApi.dueActions(14);
      setActions(resp.actions);
    } catch {
      // 静默降级，不阻塞复盘页
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const review = async (
    a: RetroActionCard,
    verdict: "effective" | "ineffective" | "not_met",
  ) => {
    setReviewing(a.id);
    try {
      const resp = await retrospectivesApi.reviewAction(a.id, verdict);
      setActions((prev) => prev.filter((x) => x.id !== a.id));
      if (verdict === "effective" && resp.upgraded_principle) {
        toast.push(
          "验证有效——已自动升级为「已验证」原则，AI 对话会开始引用它",
          "success",
        );
      } else if (verdict === "ineffective") {
        toast.push("已记录无效——下次复盘开场不会再问这张卡", "info");
      } else {
        toast.push("还没遇到触发场景——顺延 14 天再问你", "info");
      }
      onChanged?.();
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "复审失败", "error");
    } finally {
      setReviewing(null);
    }
  };

  if (!actions.length) return null;

  return (
    <section className="rounded-xl border border-amber-200 bg-amber-50/60 p-4">
      <h3 className="mb-1 flex items-center gap-2 text-sm font-semibold text-ink-800">
        <AlarmClock className="h-4 w-4 text-amber-500" />
        上次复盘的行动卡到期了（{actions.length} 张）——先验证它们再写新复盘
      </h3>
      <p className="mb-3 text-xs text-ink-400">
        复盘闭环的铁律：上次说"下次要试"的事，这次开场必须给个交代
      </p>
      <div className="space-y-2">
        {actions.map((a) => (
          <div
            key={a.id}
            className="flex flex-col gap-2 rounded-lg border border-amber-100 bg-white p-3 sm:flex-row sm:items-center"
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm text-ink-800">
                <span className="text-ink-400">当</span>
                {a.trigger_scene}
                <span className="text-ink-400"> → </span>
                {a.content}
              </p>
              <p className="mt-0.5 text-xs text-ink-400">到期日：{a.review_due_at}</p>
            </div>
            {reviewing === a.id ? (
              <span className="text-xs text-ink-400">提交中…</span>
            ) : (
              <div className="flex shrink-0 flex-wrap gap-1.5">
                <Button size="sm" variant="secondary" onClick={() => review(a, "effective")}>
                  <Check className="h-3.5 w-3.5 text-green-600" /> 用上了，有效
                </Button>
                <Button size="sm" variant="secondary" onClick={() => review(a, "ineffective")}>
                  <ThumbsDown className="h-3.5 w-3.5" /> 试了没用
                </Button>
                <Button size="sm" variant="secondary" onClick={() => review(a, "not_met")}>
                  <Clock3 className="h-3.5 w-3.5" /> 还没遇到
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
