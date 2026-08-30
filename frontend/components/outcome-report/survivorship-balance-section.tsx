"use client";

// frontend/components/outcome-report/survivorship-balance-section.tsx
// 幸存者偏差矫正 — 上岸墙的诚实另一半：把失败案例库的真实教训并列摆出。
// 立场：别的平台只给你看上岸的少数人，我们把落榜者的教训也摆在同一面墙上。

import { useEffect, useState } from "react";
import { BookOpen, Scale } from "lucide-react";
import { failureCaseApi } from "@/lib/api";
import type { FailureCaseResponse } from "@/types/failure-case";

const PATH_LABELS: Record<string, string> = {
  kaoyan: "考研",
  civil_service: "考公",
  employment: "求职",
  study_abroad: "留学",
};

export function SurvivorshipBalanceSection({ limit = 3 }: { limit?: number }) {
  const [cases, setCases] = useState<FailureCaseResponse[]>([]);
  const [total, setTotal] = useState<number | null>(null);

  useEffect(() => {
    failureCaseApi
      .list({ size: limit, page: 1 })
      .then((res) => {
        setCases(res.items ?? []);
        setTotal(res.total ?? null);
      })
      .catch(() => {
        // 加载失败就安静降级：宁可不展示，也不放占位假案例
        setCases([]);
      });
  }, [limit]);

  if (cases.length === 0) return null;

  return (
    <section className="rounded-xl border border-paper-300 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-ink-700 to-ink-900 text-white">
            <Scale className="h-4 w-4" />
          </span>
          <div>
            <h3 className="text-base font-semibold text-ink-900">
              另一面墙：那些没有上岸的人
            </h3>
            <p className="text-xs text-ink-500">
              这里只展示成功者是幸存者偏差——以下教训来自真实落榜/受挫者的匿名自述，
              与上岸案例同样值得认真读
            </p>
          </div>
        </div>
        {total != null && total > cases.length && (
          <span className="text-xs text-ink-400">共 {total} 条教训</span>
        )}
      </div>

      <ul className="mt-4 space-y-3">
        {cases.map((c) => (
          <li key={c.id} className="rounded-lg border border-paper-200 bg-paper-50/60 p-4">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="text-sm font-semibold text-ink-800">{c.title}</span>
              <span className="rounded-full bg-ink-100 px-2 py-0.5 text-[11px] text-ink-600">
                {PATH_LABELS[c.path_type] ?? c.path_type}
              </span>
              <span className="text-[11px] text-ink-400">· {c.author_role}</span>
            </div>
            {(c.lessons?.length ?? 0) > 0 && (
              <div className="mt-2 flex items-start gap-1.5 text-xs leading-relaxed text-ink-600">
                <BookOpen className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-400" />
                <span>{c.lessons[0]}</span>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
