"use client";

import { Suspense, useCallback, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Building2,
  MapPin,
  GraduationCap,
  Users,
  Search,
  FileText,
  ChevronDown,
  Landmark,
  BadgeCheck,
  Target,
  Layers,
  Sparkles,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/lib/api/swr-config";
import { buildQuery } from "@/lib/api/client";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Pagination } from "@/components/ui/pagination";
import type {
  GwyProvincePositionListResponse,
  GwyProvincePositionResponse,
  GwyProvincePositionStatsResponse,
} from "@/types";

const PAGE_SIZE = 12;

/** 应届限制候选（广东 2026 真实取值） */
const FRESH_GRAD_OPTIONS = ["否", "应届毕业生", "2026届高校毕业生"] as const;

const STAT_CARD_STYLE =
  "rounded-xl border border-paper-200 bg-white p-4 flex items-start gap-3";

const FILTER_SELECT_CLASS =
  "rounded-lg border border-paper-300 bg-white px-3 py-2 text-sm text-ink-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100";

export default function GwyProvincePositionsPage() {
  return (
    <Suspense fallback={<LoadingState text="加载省考职位…" />}>
      <GwyProvincePositionsPageContent />
    </Suspense>
  );
}

function GwyProvincePositionsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const q = searchParams.get("q") || "";
  const sheet_name = searchParams.get("sheet_name") || "";
  const education_req = searchParams.get("education_req") || "";
  const exam_region = searchParams.get("exam_region") || "";
  const fresh_grad_only = searchParams.get("fresh_grad_only") || "";
  const page = Math.max(1, Number(searchParams.get("page") || "1") || 1);

  const [expandedId, setExpandedId] = useState<string | null>(null);

  const updateParams = useCallback(
    (patch: Record<string, string | number>) => {
      const sp = new URLSearchParams(searchParams.toString());
      Object.entries(patch).forEach(([k, v]) => {
        if (v === "" || v === null || v === undefined) sp.delete(k);
        else sp.set(k, String(v));
      });
      router.replace(`/civil-service/province-positions?${sp.toString()}`);
    },
    [router, searchParams],
  );

  const hasFilter = q || sheet_name || education_req || exam_region || fresh_grad_only;

  // 列表请求 URL（SWR 缓存键）
  const listUrl = useMemo(
    () =>
      `/api/gwy-province-positions${buildQuery({
        page,
        page_size: PAGE_SIZE,
        q: q || null,
        sheet_name: sheet_name || null,
        education_req: education_req || null,
        exam_region: exam_region || null,
        fresh_grad_only: fresh_grad_only || null,
      })}`,
    [page, q, sheet_name, education_req, exam_region, fresh_grad_only],
  );

  const { data: listData, isLoading: listLoading, error: listError } = useApi<GwyProvincePositionListResponse>(
    listUrl,
    { fallbackData: undefined },
  );
  const { data: stats } = useApi<GwyProvincePositionStatsResponse>(
    "/api/gwy-province-positions/stats",
  );

  const items = listData?.items ?? [];
  const total = listData?.total ?? 0;

  // 筛选选项动态取自真实数据分布（按招录系统 / 学历 / 考区）
  const sheetOptions = stats?.by_sheet ?? [];
  const educationOptions = stats?.by_education ?? [];
  const regionOptions = stats?.by_region ?? [];

  const clearFilters = () => {
    router.replace("/civil-service/province-positions");
    setExpandedId(null);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* 页头 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-ink-800 mb-2 flex items-center gap-2">
          <Landmark className="h-8 w-8 text-emerald-600" />
          2026 省考职位检索
        </h1>
        <p className="text-ink-500">
          数据来源：广东省 2026 年考试录用公务员公告官方职位表（共{" "}
          {stats?.total ?? "…"} 个职位，计划招录 {stats?.total_recruit ?? "…"} 名）
        </p>
      </div>

      {/* 统计概览 */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
        <div className={STAT_CARD_STYLE}>
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-50 shrink-0">
            <Target className="h-5 w-5 text-emerald-500" />
          </div>
          <div>
            <p className="text-xs text-ink-400">职位总数</p>
            <p className="text-xl font-bold text-ink-800">{stats?.total ?? "—"}</p>
          </div>
        </div>
        <div className={STAT_CARD_STYLE}>
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-50 shrink-0">
            <Users className="h-5 w-5 text-green-500" />
          </div>
          <div>
            <p className="text-xs text-ink-400">计划招录</p>
            <p className="text-xl font-bold text-ink-800">{stats?.total_recruit ?? "—"}</p>
          </div>
        </div>
        <div className={STAT_CARD_STYLE}>
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-50 shrink-0">
            <MapPin className="h-5 w-5 text-purple-500" />
          </div>
          <div>
            <p className="text-xs text-ink-400">覆盖考区</p>
            <p className="text-xl font-bold text-ink-800">
              {stats ? `${stats.by_region.length}` : "—"}
            </p>
          </div>
        </div>
        <div className={STAT_CARD_STYLE}>
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50 shrink-0">
            <Layers className="h-5 w-5 text-amber-500" />
          </div>
          <div>
            <p className="text-xs text-ink-400">招录系统</p>
            <p className="text-xl font-bold text-ink-800">
              {stats ? `${stats.by_sheet.length}` : "—"}
            </p>
          </div>
        </div>
      </div>

      {/* 筛选栏 */}
      <div className="rounded-xl border border-paper-200 bg-white p-4 mb-6">
        <div className="flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-300" />
            <input
              type="text"
              value={q}
              onChange={(e) => updateParams({ q: e.target.value, page: 1 })}
              placeholder="搜索职位名称 / 招考单位 / 专业要求…"
              className="w-full rounded-lg border border-paper-300 bg-white pl-9 pr-3 py-2 text-sm text-ink-700 placeholder:text-ink-300 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <select
            value={sheet_name}
            onChange={(e) => updateParams({ sheet_name: e.target.value, page: 1 })}
            className={FILTER_SELECT_CLASS}
          >
            <option value="">全部招录系统</option>
            {sheetOptions.map((s) => (
              <option key={s.key} value={s.key}>
                {s.key}（{s.count}）
              </option>
            ))}
          </select>
          <select
            value={education_req}
            onChange={(e) => updateParams({ education_req: e.target.value, page: 1 })}
            className={FILTER_SELECT_CLASS}
          >
            <option value="">全部学历</option>
            {educationOptions.map((e) => (
              <option key={e.key} value={e.key}>
                {e.key}（{e.count}）
              </option>
            ))}
          </select>
          <select
            value={exam_region}
            onChange={(e) => updateParams({ exam_region: e.target.value, page: 1 })}
            className={FILTER_SELECT_CLASS}
          >
            <option value="">全部考区</option>
            {regionOptions.map((r) => (
              <option key={r.key} value={r.key}>
                {r.key}（{r.count}）
              </option>
            ))}
          </select>
          <select
            value={fresh_grad_only}
            onChange={(e) => updateParams({ fresh_grad_only: e.target.value, page: 1 })}
            className={FILTER_SELECT_CLASS}
          >
            <option value="">应届限制不限</option>
            {FRESH_GRAD_OPTIONS.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
          {hasFilter && (
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-ink-400 hover:text-brand-600 hover:bg-brand-50"
            >
              <X className="h-4 w-4" />
              清除筛选
            </button>
          )}
        </div>
      </div>

      {/* 结果区 */}
      {listLoading && !items.length ? (
        <LoadingState text="加载职位列表…" />
      ) : listError ? (
        <EmptyState title="加载失败" description="无法获取职位数据，请稍后重试" />
      ) : items.length === 0 ? (
        <EmptyState
          title="没有匹配的职位"
          description={hasFilter ? "试试放宽筛选条件，或清除筛选查看全部职位" : "暂无职位数据"}
          action={
            hasFilter ? (
              <button
                onClick={clearFilters}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 text-white font-medium hover:opacity-90 transition-opacity"
              >
                清除筛选
              </button>
            ) : undefined
          }
        />
      ) : (
        <>
          <p className="text-sm text-ink-400 mb-3">
            共 {total} 个职位
            {hasFilter && "（已按当前条件筛选）"}
          </p>
          <div className="space-y-3">
            {items.map((item) => (
              <PositionCard
                key={item.id}
                position={item}
                expanded={expandedId === item.id}
                onToggle={() => setExpandedId(expandedId === item.id ? null : item.id)}
              />
            ))}
          </div>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            onPageChange={(p) => {
              updateParams({ page: p });
              setExpandedId(null);
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        </>
      )}
    </div>
  );
}

/** 职位卡片：点击展开完整详情 */
function PositionCard({
  position,
  expanded,
  onToggle,
}: {
  position: GwyProvincePositionResponse;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border bg-white transition-all",
        expanded
          ? "border-emerald-300 shadow-md"
          : "border-paper-200 hover:shadow-md",
      )}
    >
      <div className="flex">
        <button
          onClick={onToggle}
          className="flex-1 min-w-0 text-left p-5"
          aria-expanded={expanded}
        >
          <div className="pr-2">
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
                <Building2 className="h-3 w-3" />
                {position.dept_name || "—"}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-paper-100 px-2.5 py-0.5 text-xs text-ink-500">
                <BadgeCheck className="h-3 w-3" />
                {position.position_code}
              </span>
              {position.fresh_grad_only && position.fresh_grad_only !== "否" && (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700">
                  <Sparkles className="h-3 w-3" />
                  {position.fresh_grad_only}
                </span>
              )}
            </div>
            <h3 className="font-display font-bold text-ink-800 mb-1">
              {position.position_name || "—"}
            </h3>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-500">
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" />
                {position.exam_region || "—"}
              </span>
              <span className="flex items-center gap-1">
                <GraduationCap className="h-3.5 w-3.5" />
                {position.education_req || "学历不限"}
              </span>
              {position.recruit_count != null && (
                <span className="flex items-center gap-1">
                  <Users className="h-3.5 w-3.5" />
                  招 {position.recruit_count} 人
                </span>
              )}
            </div>
          </div>
        </button>

        <div className="flex shrink-0 flex-col items-center justify-center gap-2 pt-4 pr-4">
          <button
            onClick={onToggle}
            aria-label={expanded ? "收起详情" : "展开详情"}
            className="rounded-md p-1 text-ink-300 hover:bg-paper-100 hover:text-ink-600 transition-colors"
          >
            <ChevronDown
              className={cn(
                "h-4 w-4 transition-transform",
                expanded && "rotate-180",
              )}
            />
          </button>
        </div>
      </div>

      {expanded && <PositionDetail position={position} />}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="flex flex-col sm:flex-row sm:gap-2 text-sm py-1.5 border-b border-paper-100 last:border-0">
      <span className="text-ink-400 shrink-0 sm:w-28">{label}</span>
      <span className="text-ink-700 whitespace-pre-line break-words">{value}</span>
    </div>
  );
}

function PositionDetail({ position }: { position: GwyProvincePositionResponse }) {
  return (
    <div className="px-5 pb-5 border-t border-paper-100 pt-3 animate-fade-in">
      <div className="flex flex-wrap gap-2 mb-4">
        <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
          {position.sheet_name || "系统未知"}
        </span>
        <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
          {position.position_type || "类别未知"}
        </span>
        {position.psych_test && (
          <span className="inline-flex items-center rounded-full bg-paper-100 px-2.5 py-0.5 text-xs text-ink-500">
            心理测评 {position.psych_test}
          </span>
        )}
        {position.fresh_grad_only && (
          <span className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700">
            应届限制：{position.fresh_grad_only}
          </span>
        )}
      </div>

      <div className="grid gap-x-8 md:grid-cols-2">
        <div>
          <DetailRow label="单位代码" value={position.dept_code} />
          <DetailRow label="招录单位" value={position.dept_name} />
          <DetailRow label="职位代码" value={position.position_code} />
          <DetailRow label="职位类别" value={position.position_type} />
          <DetailRow label="学历要求" value={position.education_req} />
          <DetailRow label="学位要求" value={position.degree_req} />
        </div>
        <div>
          <DetailRow label="研究生专业" value={position.major_req_grad} />
          <DetailRow label="本科专业" value={position.major_req_undergrad} />
          <DetailRow label="大专专业" value={position.major_req_junior} />
          <DetailRow label="基层工作经历" value={position.grassroots_exp_req} />
          <DetailRow label="其他要求" value={position.other_requirements} />
          <DetailRow label="考区" value={position.exam_region} />
          <DetailRow label="招录系统" value={position.sheet_name} />
        </div>
      </div>

      {position.position_desc && (
        <div className="mt-4 rounded-lg bg-paper-50 p-4">
          <p className="flex items-center gap-1.5 text-xs font-medium text-ink-400 mb-2">
            <FileText className="h-3.5 w-3.5" />
            职位简介
          </p>
          <p className="text-sm text-ink-600 leading-relaxed whitespace-pre-line">
            {position.position_desc}
          </p>
        </div>
      )}
    </div>
  );
}
