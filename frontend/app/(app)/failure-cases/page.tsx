"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import useSWR from "swr";
import {
  HeartCrack,
  Eye,
  ThumbsUp,
  BookOpen,
  Filter,
  PenLine,
  ArrowRight,
} from "lucide-react";
import { failureCaseApi } from "@/lib/api";
import {
  PATH_LABELS,
  STAGE_LABELS,
  PATH_BADGE_COLORS,
  type FailureCasePathType,
} from "@/types/failure-case";
import { Badge } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Pagination } from "@/components/ui/pagination";

const PATH_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "全部路径" },
  { value: "kaoyan", label: "考研" },
  { value: "civil_service", label: "考公" },
  { value: "employment", label: "求职" },
  { value: "study_abroad", label: "留学" },
];

const STAGE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "全部阶段" },
  { value: "preparation", label: "备考阶段" },
  { value: "interview", label: "面试/复试阶段" },
  { value: "final_year1", label: "毕业第一年" },
  { value: "year2_plus", label: "毕业两年+" },
];

const PAGE_SIZE = 10;

export default function FailureCasesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const pathType = searchParams.get("path_type") || "";
  const stage = searchParams.get("stage") || "";
  const page = parseInt(searchParams.get("page") || "1", 10);

  const listKey = `/api/failure-cases?path_type=${pathType}&stage=${stage}&page=${page}&size=${PAGE_SIZE}`;
  const { data, isLoading } = useSWR(listKey, () =>
    failureCaseApi.list({
      path_type: pathType || undefined,
      stage: stage || undefined,
      page,
      size: PAGE_SIZE,
    }),
  );

  const { data: statsData } = useSWR("/api/failure-cases/stats", () =>
    failureCaseApi.stats(),
  );

  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.set("page", "1");
    router.push(`/failure-cases?${params.toString()}`);
  };

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(newPage));
    router.push(`/failure-cases?${params.toString()}`);
  };

  const statsCards = useMemo(() => {
    if (!statsData) return [];
    const cards = [
      { label: "真实失败叙事", value: statsData.total, color: "text-brand-600" },
    ];
    const pathEntries: [string, number][] = Object.entries(statsData.by_path);
    for (const [key, count] of pathEntries) {
      const label = PATH_LABELS[key as FailureCasePathType] || key;
      cards.push({ label, value: count, color: "text-ink-700" });
    }
    return cards;
  }, [statsData]);

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
              <HeartCrack className="h-6 w-6" strokeWidth={1.8} />
            </div>
            <div>
              <h1 className="font-display text-2xl font-bold text-ink-800 tracking-tight">
                失败案例库
              </h1>
              <p className="text-sm text-ink-400 mt-0.5">
                对冲幸存者偏差的真实失败叙事 — 失败是正常的，不是终点
              </p>
            </div>
          </div>
          <p className="text-sm text-ink-500 leading-relaxed bg-brand-50 border border-brand-100 rounded-lg px-4 py-3">
            社交媒体只推成功故事，放大焦虑。这里收集真实的第一人称失败经历，
            每一个都有具体的教训提炼。不是"吓唬人"，而是"失败是正常的"——降低试错心理成本。
          </p>
        </div>

        {/* Stats Cards */}
        {statsCards.length > 0 && (
          <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
            {statsCards.map((card) => (
              <div
                key={card.label}
                className="rounded-xl border border-paper-300 bg-white px-4 py-3 text-center"
              >
                <p className={`font-display text-2xl font-bold ${card.color}`}>
                  {card.value}
                </p>
                <p className="text-xs text-ink-400 mt-1">{card.label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Filters */}
        <div className="mb-6 flex flex-wrap items-center gap-3 rounded-xl border border-paper-300 bg-white px-4 py-3">
          <div className="flex items-center gap-2 text-sm text-ink-500">
            <Filter className="h-4 w-4" />
            <span>筛选</span>
          </div>
          <select
            value={pathType}
            onChange={(e) => updateFilter("path_type", e.target.value)}
            className="rounded-lg border border-paper-300 bg-white px-3 py-1.5 text-sm text-ink-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
          >
            {PATH_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <select
            value={stage}
            onChange={(e) => updateFilter("stage", e.target.value)}
            className="rounded-lg border border-paper-300 bg-white px-3 py-1.5 text-sm text-ink-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
          >
            {STAGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <Link
            href="/failure-cases/new"
            className="ml-auto inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
          >
            <PenLine className="h-4 w-4" />
            分享我的失败经历
          </Link>
        </div>

        {/* Case List */}
        {isLoading ? (
          <LoadingState text="加载案例中…" />
        ) : !data || data.items.length === 0 ? (
          <EmptyState
            title="暂无案例"
            description="还没有符合筛选条件的失败案例。你也可以分享自己的经历，帮助后来人。"
            action={
              <Link
                href="/failure-cases/new"
                className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
              >
                <PenLine className="h-4 w-4" />
                分享我的失败经历
              </Link>
            }
          />
        ) : (
          <div className="space-y-4">
            {data.items.map((item) => (
              <Link
                key={item.id}
                href={`/failure-cases/${item.id}`}
                className="block rounded-xl border border-paper-300 bg-white p-5 transition-all hover:border-brand-300 hover:shadow-md"
              >
                {/* Badges */}
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <Badge color={PATH_BADGE_COLORS[item.path_type]}>
                    {PATH_LABELS[item.path_type]}
                  </Badge>
                  <Badge color="slate">
                    {STAGE_LABELS[item.stage]}
                  </Badge>
                  <span className="text-xs text-ink-400">
                    {item.author_role}
                  </span>
                </div>

                {/* Title */}
                <h3 className="font-display text-lg font-semibold text-ink-800 mb-2 leading-snug">
                  {item.title}
                </h3>

                {/* Story preview */}
                <p className="text-sm text-ink-500 leading-relaxed line-clamp-3 mb-3">
                  {item.story}
                </p>

                {/* Meta */}
                <div className="flex items-center gap-4 text-xs text-ink-400">
                  <span className="inline-flex items-center gap-1">
                    <BookOpen className="h-3.5 w-3.5" />
                    {item.lessons.length} 条教训
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <ThumbsUp className="h-3.5 w-3.5" />
                    {item.helpful_count} 人觉得有帮助
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Eye className="h-3.5 w-3.5" />
                    {item.view_count} 次浏览
                  </span>
                  <span className="ml-auto inline-flex items-center gap-1 text-brand-600 font-medium">
                    阅读全文
                    <ArrowRight className="h-3.5 w-3.5" />
                  </span>
                </div>
              </Link>
            ))}

            {/* Pagination */}
            {data && (
              <Pagination
                page={data.page}
                pageSize={data.page_size}
                total={data.total}
                onPageChange={handlePageChange}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
