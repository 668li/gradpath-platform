"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Landmark,
  Trash2,
  X,
} from "lucide-react";
import { GWY_COMPARE_MAX, useGwyCompareStore } from "@/stores/gwy-compare";
import { gwyPositionsApi, gwyScoreLinesApi } from "@/lib/api/gwy";
import { formatScoreLines } from "@/lib/gwy-score-lines";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import type { GwyPositionResponse, GwyScoreLineResponse } from "@/types";

/** 对比维度（与招考简章字段对齐） */
const FIELDS: { label: string; get: (p: GwyPositionResponse) => string | null }[] = [
  { label: "招录机关", get: (p) => p.dept_name },
  { label: "用人司局", get: (p) => p.bureau },
  { label: "职位名称", get: (p) => p.position_name },
  { label: "机构层级", get: (p) => p.org_level },
  { label: "考试类别", get: (p) => p.exam_category },
  { label: "职位属性", get: (p) => p.position_attr },
  { label: "招考人数", get: (p) => (p.recruit_count != null ? `${p.recruit_count} 人` : null) },
  { label: "工作地点", get: (p) => p.work_location },
  { label: "落户地点", get: (p) => p.settle_location },
  { label: "专业要求", get: (p) => p.major_req },
  { label: "学历要求", get: (p) => p.education_req },
  { label: "学位要求", get: (p) => p.degree_req },
  { label: "政治面貌", get: (p) => p.political_status },
  { label: "基层工作年限", get: (p) => p.grassroots_exp_req },
  { label: "最低服务年限", get: (p) => p.min_work_years },
  { label: "面试比例", get: (p) => p.interview_ratio },
  { label: "专业能力测试", get: (p) => p.professional_test },
  { label: "备注", get: (p) => p.remarks },
];

export default function GwyComparePage() {
  const ids = useGwyCompareStore((s) => s.ids);
  const remove = useGwyCompareStore((s) => s.remove);
  const clear = useGwyCompareStore((s) => s.clear);

  const [positions, setPositions] = useState<GwyPositionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  // 按职位代码关联的进面分数线（key = position_code）
  const [scoreLines, setScoreLines] = useState<Record<string, GwyScoreLineResponse[]>>({});

  // 客户端挂载后从 localStorage 恢复对比清单
  useEffect(() => {
    useGwyCompareStore.persist.rehydrate();
  }, []);

  // 拉取选中职位详情；失效 id（已被删除）自动移出清单
  useEffect(() => {
    let cancelled = false;
    if (ids.length === 0) {
      setPositions([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setLoadError(false);
    Promise.all(
      ids.map((id) => gwyPositionsApi.get(id).catch(() => null)),
    ).then((results) => {
      if (cancelled) return;
      const ok = results.filter((r): r is GwyPositionResponse => r !== null);
      setPositions(ok);
      setLoading(false);
      if (ok.length !== ids.length) {
        const valid = new Set(ok.map((r) => r.id));
        ids.filter((id) => !valid.has(id)).forEach((id) => remove(id));
      }
    }).catch(() => {
      if (cancelled) return;
      setLoadError(true);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [ids, remove]);

  // 为每个职位拉取进面分数线（按 position_code），失败时该列显示 "—"
  useEffect(() => {
    let cancelled = false;
    if (positions.length === 0) {
      setScoreLines({});
      return;
    }
    Promise.all(
      positions.map((p) =>
        gwyScoreLinesApi
          .list({ position_code: p.position_code, page_size: 20 })
          .then((r) => [p.position_code, r.items] as const)
          .catch(() => [p.position_code, [] as GwyScoreLineResponse[]] as const),
      ),
    ).then((pairs) => {
      if (cancelled) return;
      setScoreLines(Object.fromEntries(pairs));
    });
    return () => {
      cancelled = true;
    };
  }, [positions]);

  // 对比维度 = 招考简章字段 + 进面最低分（按职位代码关联 gwy_score_line）
  const fields = useMemo(
    () => [
      ...FIELDS,
      {
        label: "进面最低分",
        get: (p: GwyPositionResponse) => formatScoreLines(scoreLines[p.position_code]),
      },
    ],
    [scoreLines],
  );

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <Link
            href="/civil-service/positions"
            className="inline-flex items-center gap-1 text-sm text-ink-400 hover:text-blue-600 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            返回职位检索
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-ink-800 flex items-center gap-2">
            <Landmark className="h-8 w-8 text-blue-600" />
            国考职位对比
          </h1>
          <p className="text-ink-500 mt-1">
            并排对比招考条件（最多 {GWY_COMPARE_MAX} 个职位）
          </p>
        </div>
        {positions.length > 0 && (
          <button
            onClick={clear}
            className="inline-flex items-center gap-1.5 rounded-lg border border-paper-300 px-3 py-2 text-sm text-ink-500 hover:text-red-600 hover:border-red-200 transition-colors"
          >
            <Trash2 className="h-4 w-4" />
            清空对比
          </button>
        )}
      </div>

      {loading ? (
        <LoadingState text="加载职位详情…" />
      ) : loadError ? (
        <EmptyState title="加载失败" description="无法获取职位数据，请稍后重试" />
      ) : positions.length === 0 ? (
        <EmptyState
          title="暂无对比职位"
          description="在国考职位检索页勾选心仪职位后，可在这里并排对比招考条件"
          action={
            <Link
              href="/civil-service/positions"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:opacity-90 transition-opacity"
            >
              去挑选职位
            </Link>
          }
        />
      ) : (
        <div className="rounded-xl border border-paper-200 bg-white overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[760px]">
              <thead>
                <tr className="border-b border-paper-200">
                  <th className="w-32 shrink-0 bg-paper-50 p-4 text-left align-top text-xs font-medium text-ink-400">
                    字段
                  </th>
                  {positions.map((p) => (
                    <th key={p.id} className="p-4 text-left align-top">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="font-bold text-ink-800 leading-snug">
                            {p.dept_name || "—"}
                          </p>
                          <p className="mt-0.5 text-xs text-ink-500">
                            {p.position_name || "—"}
                          </p>
                          <p className="mt-1.5 inline-block rounded bg-paper-100 px-1.5 py-0.5 font-mono text-[11px] text-ink-500">
                            {p.position_code}
                          </p>
                        </div>
                        <button
                          onClick={() => remove(p.id)}
                          aria-label={`移除 ${p.position_name || p.position_code}`}
                          className="rounded-md p-1 text-ink-300 hover:bg-red-50 hover:text-red-500 transition-colors shrink-0"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {fields.map((field, i) => (
                  <tr
                    key={field.label}
                    className={i % 2 === 1 ? "bg-paper-50/60" : ""}
                  >
                    <td className="bg-paper-50 p-3 align-top text-xs font-medium text-ink-400">
                      {field.label}
                    </td>
                    {positions.map((p) => (
                      <td
                        key={p.id}
                        className="p-3 align-top text-ink-700 whitespace-pre-line"
                      >
                        {field.get(p) || "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
