"use client";

// Dashboard 当前决策卡（D9 Phase 2.3 首页重构第一段）。
// 数据 = 既有 API 组合：/api/decisions 列表取最近 planned 决策 → /api/decision-os card。
// 展示纪律：只呈现状态（假设/证据立场计数/下一步行动），不给结论、不打分。

import { useEffect, useState } from "react";
import Link from "next/link";
import { decisionsApi } from "@/lib/api/decisions";
import { decisionOsApi, type DecisionCard as Card } from "@/lib/api/decisionOs";

const HYP_STATUS_LABEL: Record<string, string> = {
  untested: "未验证",
  supporting: "有支持",
  refuted: "已证伪",
  obsolete: "已失效",
};

export function CurrentDecisionCard() {
  const [card, setCard] = useState<Card | null>(null);
  const [loading, setLoading] = useState(true);
  const [empty, setEmpty] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await decisionsApi.list({ page_size: 20 });
        const current = (list.items || []).find((d) => d.status === "planned");
        if (!current) {
          if (!cancelled) setEmpty(true);
          return;
        }
        const c = await decisionOsApi.card(current.id);
        if (!cancelled) setCard(c);
      } catch {
        if (!cancelled) setEmpty(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <section className="card p-5 animate-fade-in">
        <div className="h-4 w-32 animate-pulse rounded bg-gray-100" />
        <div className="mt-3 h-6 w-2/3 animate-pulse rounded bg-gray-100" />
      </section>
    );
  }

  if (empty || !card) {
    return (
      <section className="card p-5 animate-fade-in">
        <h2 className="text-lg font-semibold text-ink-800">当前决策</h2>
        <p className="mt-2 text-sm text-gray-500">
          你现在没有进行中的重大决策。有了就把它变成可以验证的系统。
        </p>
        <Link
          href="/decision-os"
          className="mt-3 inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          去决策 OS 说清你的决定
        </Link>
      </section>
    );
  }

  const d = card.decision;
  const untested = card.hypotheses.filter((h) => h.status === "untested").slice(0, 3);
  const nextAction = card.actions.find((a) => a.status !== "done" && a.status !== "skipped");

  return (
    <section className="card p-5 animate-fade-in">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-ink-800">当前决策</h2>
          <p className="mt-1 text-base text-ink-700">{d.question || "（未命名决策）"}</p>
        </div>
        <span className="shrink-0 rounded-full bg-blue-50 px-3 py-1 text-xs text-blue-700">
          证据验证中 · {card.hypotheses.filter((h) => h.status === "untested").length} 个假设待验证
        </span>
      </div>

      {untested.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-medium text-gray-500">最关键的未验证假设</p>
          <ul className="mt-2 space-y-2">
            {untested.map((h) => (
              <li key={h.id} className="text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span>{h.statement}</span>
                  <span className="shrink-0 text-xs text-gray-400">{HYP_STATUS_LABEL[h.status]}</span>
                </div>
                <div className="mt-1 flex h-1.5 w-full overflow-hidden rounded bg-gray-100">
                  <div
                    className="bg-green-500"
                    style={{ width: `${(h.supporting / Math.max(h.evidence_count, 1)) * 100}%` }}
                  />
                  <div
                    className="bg-red-400"
                    style={{ width: `${(h.contradicting / Math.max(h.evidence_count, 1)) * 100}%` }}
                  />
                </div>
                <p className="mt-0.5 text-xs text-gray-400">
                  证据 {h.evidence_count} 条（支持 {h.supporting} / 反对 {h.contradicting}）
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 rounded-lg bg-amber-50 p-3 text-sm">
        <p className="text-xs font-medium text-amber-700">下一步最小验证行动</p>
        <p className="mt-1 text-ink-700">
          {nextAction ? nextAction.title : "还没有验证行动——先给最关键的假设设计一个"}
        </p>
      </div>

      <Link
        href={`/decision-os?decision=${d.id}`}
        className="mt-4 inline-block text-sm font-medium text-blue-600 hover:text-blue-700"
      >
        在决策 OS 中继续验证 →
      </Link>
    </section>
  );
}
