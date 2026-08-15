"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Building2,
  MapPin,
  GraduationCap,
  Users,
  Target,
  Search,
  FileText,
  Globe,
  ChevronDown,
  Landmark,
  BadgeCheck,
  TrendingUp,
  Check,
  Plus,
  ArrowRight,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/lib/api/swr-config";
import { buildQuery } from "@/lib/api/client";
import { formatScoreLines } from "@/lib/gwy-score-lines";
import { GWY_COMPARE_MAX, useGwyCompareStore } from "@/stores/gwy-compare";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Pagination } from "@/components/ui/pagination";
import type {
  GwyPositionListResponse,
  GwyPositionResponse,
  GwyPositionStatsResponse,
  GwyScoreLineListResponse,
} from "@/types";

const PAGE_SIZE = 12;

/** 省份候选（职位数据实际分布：全国 31 省级行政区 + 深圳/广州等单列市） */
const PROVINCES = [
  "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
  "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
  "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
  "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆",
  "深圳市", "广州市", "大连市", "青岛市", "厦门市", "宁波市",
] as const;

const EDUCATION_LEVELS = [
  "本科及以上", "仅限本科", "本科或硕士研究生", "硕士研究生及以上",
  "仅限硕士研究生", "本科或研究生（硕士）", "研究生（硕士）及以上",
  "仅限博士研究生", "大专及以上", "大专或本科", "仅限大专",
] as const;

const POLITICAL_STATUSES = [
  "不限", "中共党员", "中共党员或共青团员", "群众", "共青团员",
] as const;

const ORG_LEVELS = [
  "中央", "省（副省）级", "市（地）级", "县（区）级及以下",
] as const;

const EXAM_CATEGORIES = [
  "行政执法类", "市（地）级及以下直属机构综合管理类",
  "中央机关及其省级直属机构综合管理类",
] as const;

const STAT_CARD_STYLE =
  "rounded-xl border border-paper-200 bg-white p-4 flex items-start gap-3";

const FILTER_SELECT_CLASS =
  "rounded-lg border border-paper-300 bg-white px-3 py-2 text-sm text-ink-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100";

export default function GwyPositionsPage() {
  return (
    <Suspense fallback={<LoadingState text="加载国考职位…" />}>
      <GwyPositionsPageContent />
    </Suspense>
  );
}

function GwyPositionsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const q = searchParams.get("q") || "";
  const province = searchParams.get("province") || "";
  const education_req = searchParams.get("education_req") || "";
  const political_status = searchParams.get("political_status") || "";
  const org_level = searchParams.get("org_level") || "";
  const exam_category = searchParams.get("exam_category") || "";
  const page = Math.max(1, Number(searchParams.get("page") || "1") || 1);

  const [expandedId, setExpandedId] = useState<string | null>(null);

  // 对比清单：skipHydration 模式，客户端挂载后从 localStorage 恢复
  const compareIds = useGwyCompareStore((s) => s.ids);
  const toggleCompare = useGwyCompareStore((s) => s.toggle);
  const clearCompare = useGwyCompareStore((s) => s.clear);
  useEffect(() => {
    useGwyCompareStore.persist.rehydrate();
  }, []);

  const updateParams = useCallback(
    (patch: Record<string, string | number>) => {
      const sp = new URLSearchParams(searchParams.toString());
      Object.entries(patch).forEach(([k, v]) => {
        if (v === "" || v === null || v === undefined) sp.delete(k);
        else sp.set(k, String(v));
      });
      router.replace(`/civil-service/positions?${sp.toString()}`);
    },
    [router, searchParams],
  );

  const hasFilter =
    q || province || education_req || political_status || org_level || exam_category;

  // 列表请求 URL（SWR 缓存键）
  const listUrl = useMemo(
    () =>
      `/api/gwy-positions${buildQuery({
        page,
        page_size: PAGE_SIZE,
        q: q || null,
        province: province || null,
        education_req: education_req || null,
        political_status: political_status || null,
        org_level: org_level || null,
        exam_category: exam_category || null,
      })}`,
    [page, q, province, education_req, political_status, org_level, exam_category],
  );

  const { data: listData, isLoading: listLoading, error: listError } = useApi<GwyPositionListResponse>(
    listUrl,
    { fallbackData: undefined },
  );
  const { data: stats } = useApi<GwyPositionStatsResponse>("/api/gwy-positions/stats");

  const items = listData?.items ?? [];
  const total = listData?.total ?? 0;

  const clearFilters = () => {
    router.replace("/civil-service/positions");
    setExpandedId(null);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* 页头 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-ink-800 mb-2 flex items-center gap-2">
          <Landmark className="h-8 w-8 text-blue-600" />
          2026 国考职位检索
        </h1>
        <p className="text-ink-500">
          数据来源：国家公务员局 2026 年度招考简章官方职位表（共 {stats?.total ?? "…"} 个职位）
        </p>
      </div>

      {/* 统计概览 */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
        <div className={STAT_CARD_STYLE}>
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 shrink-0">
            <Target className="h-5 w-5 text-blue-500" />
          </div>
          <div>
            <p className="text-xs text-ink-400">职位总数</p>
            <p className="text-xl font-bold text-ink-800">{stats?.total ?? "—"}</p>
          </div>
        </div>
        <div className={STAT_CARD_STYLE}>
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-50 shrink-0">
            <MapPin className="h-5 w-5 text-green-500" />
          </div>
          <div>
            <p className="text-xs text-ink-400">覆盖地区</p>
            <p className="text-xl font-bold text-ink-800">
              {stats && stats.by_province.length > 0 ? `${stats.by_province.length}` : "—"}
            </p>
          </div>
        </div>
        <div className={STAT_CARD_STYLE}>
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-50 shrink-0">
            <GraduationCap className="h-5 w-5 text-purple-500" />
          </div>
          <div>
            <p className="text-xs text-ink-400">学历层次</p>
            <p className="text-xl font-bold text-ink-800">
              {stats && stats.by_education.length > 0 ? `${stats.by_education.length}` : "—"}
            </p>
          </div>
        </div>
        <div className={STAT_CARD_STYLE}>
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50 shrink-0">
            <Users className="h-5 w-5 text-amber-500" />
          </div>
          <div>
            <p className="text-xs text-ink-400">机构层级</p>
            <p className="text-xl font-bold text-ink-800">
              {stats && stats.by_org_level.length > 0 ? `${stats.by_org_level.length}` : "—"}
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
              placeholder="搜索职位名称 / 部门 / 专业要求…"
              className="w-full rounded-lg border border-paper-300 bg-white pl-9 pr-3 py-2 text-sm text-ink-700 placeholder:text-ink-300 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <select
            value={province}
            onChange={(e) => updateParams({ province: e.target.value, page: 1 })}
            className={FILTER_SELECT_CLASS}
          >
            <option value="">全部地区</option>
            {PROVINCES.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <select
            value={education_req}
            onChange={(e) => updateParams({ education_req: e.target.value, page: 1 })}
            className={FILTER_SELECT_CLASS}
          >
            <option value="">全部学历</option>
            {EDUCATION_LEVELS.map((e) => (
              <option key={e} value={e}>{e}</option>
            ))}
          </select>
          <select
            value={political_status}
            onChange={(e) => updateParams({ political_status: e.target.value, page: 1 })}
            className={FILTER_SELECT_CLASS}
          >
            <option value="">政治面貌不限</option>
            {POLITICAL_STATUSES.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <select
            value={org_level}
            onChange={(e) => updateParams({ org_level: e.target.value, page: 1 })}
            className={FILTER_SELECT_CLASS}
          >
            <option value="">全部层级</option>
            {ORG_LEVELS.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
          <select
            value={exam_category}
            onChange={(e) => updateParams({ exam_category: e.target.value, page: 1 })}
            className={FILTER_SELECT_CLASS}
          >
            <option value="">全部考试类别</option>
            {EXAM_CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
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
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:opacity-90 transition-opacity"
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
                selected={compareIds.includes(item.id)}
                onToggleCompare={() => toggleCompare(item.id)}
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

      {/* 底部对比栏：勾选职位后浮出 */}
      {compareIds.length > 0 && (
        <div className="fixed bottom-6 left-1/2 z-40 -translate-x-1/2">
          <div className="flex items-center gap-3 rounded-full border border-blue-200 bg-white/95 py-2.5 pl-5 pr-2.5 shadow-xl backdrop-blur">
            <span className="whitespace-nowrap text-sm text-ink-700">
              已选{" "}
              <span className="font-bold text-blue-600">{compareIds.length}</span>{" "}
              / {GWY_COMPARE_MAX} 个职位
            </span>
            <button
              onClick={clearCompare}
              className="text-xs text-ink-400 hover:text-red-500 transition-colors"
            >
              清空
            </button>
            <Link
              href="/civil-service/positions/compare"
              className="inline-flex items-center gap-1.5 rounded-full bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
            >
              对比职位
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

/** 职位卡片：点击展开完整详情；右上角可勾选加入对比清单 */
function PositionCard({
  position,
  expanded,
  onToggle,
  selected,
  onToggleCompare,
}: {
  position: GwyPositionResponse;
  expanded: boolean;
  onToggle: () => void;
  selected: boolean;
  onToggleCompare: () => void;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border bg-white transition-all",
        selected
          ? "border-blue-300 ring-1 ring-blue-200"
          : expanded
            ? "border-blue-300 shadow-md"
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
              <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                <Building2 className="h-3 w-3" />
                {position.dept_name || position.bureau || "—"}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-paper-100 px-2.5 py-0.5 text-xs text-ink-500">
                <BadgeCheck className="h-3 w-3" />
                {position.position_code}
              </span>
            </div>
            <h3 className="font-display font-bold text-ink-800 mb-1">
              {position.position_name || "—"}
            </h3>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-500">
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" />
                {position.work_location || "—"}
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

        <div className="flex shrink-0 flex-col items-center gap-2 pt-4 pr-4">
          <button
            onClick={onToggleCompare}
            aria-pressed={selected}
            aria-label={selected ? "移出对比" : "加入对比"}
            className={cn(
              "inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              selected
                ? "border-blue-600 bg-blue-600 text-white"
                : "border-paper-300 bg-white text-ink-500 hover:border-blue-400 hover:text-blue-600",
            )}
          >
            {selected ? <Check className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
            {selected ? "已对比" : "对比"}
          </button>
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

/** 进面分数线区块：按职位代码拉取面试名单聚合分（首批/调剂/补充录用）。 */
function ScoreLinePanel({ positionCode }: { positionCode: string }) {
  const { data } = useApi<GwyScoreLineListResponse>(
    `/api/gwy-score-lines${buildQuery({ position_code: positionCode, page_size: 20 })}`,
  );
  const formatted = formatScoreLines(data?.items);
  if (!formatted) return null;
  return (
    <div className="mt-3 rounded-lg border border-blue-100 bg-blue-50/60 p-3">
      <p className="flex items-center gap-1.5 text-xs font-medium text-blue-700 mb-1.5">
        <TrendingUp className="h-3.5 w-3.5" />
        2026 进面最低分
      </p>
      <p className="text-sm text-ink-700">{formatted}</p>
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

function PositionDetail({ position }: { position: GwyPositionResponse }) {
  return (
    <div className="px-5 pb-5 border-t border-paper-100 pt-3 animate-fade-in">
      <div className="flex flex-wrap gap-2 mb-4">
        <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
          {position.org_level || "层级未知"}
        </span>
        <span className="inline-flex items-center rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700">
          {position.exam_category || "类别未知"}
        </span>
        {position.political_status && (
          <span className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700">
            {position.political_status}
          </span>
        )}
        {position.interview_ratio && (
          <span className="inline-flex items-center rounded-full bg-paper-100 px-2.5 py-0.5 text-xs text-ink-500">
            面试比例 {position.interview_ratio}
          </span>
        )}
      </div>

      <div className="grid gap-x-8 md:grid-cols-2">
        <div>
          <DetailRow label="部门代码" value={position.dept_code} />
          <DetailRow label="招录机关" value={position.dept_name} />
          <DetailRow label="用人司局" value={position.bureau} />
          <DetailRow label="机构性质" value={position.agency_type} />
          <DetailRow label="职位属性" value={position.position_attr} />
          <DetailRow label="职位分布" value={position.position_distribution} />
          <DetailRow label="专业要求" value={position.major_req} />
          <DetailRow label="学历要求" value={position.education_req} />
          <DetailRow label="学位要求" value={position.degree_req} />
          <DetailRow label="政治面貌" value={position.political_status} />
        </div>
        <div>
          <ScoreLinePanel positionCode={position.position_code} />
          <DetailRow label="最低工作年限" value={position.min_work_years} />
          <DetailRow label="基层工作最低年限" value={position.grassroots_exp_req} />
          <DetailRow label="专业能力测试" value={position.professional_test} />
          <DetailRow label="面试比例" value={position.interview_ratio} />
          <DetailRow label="工作地点" value={position.work_location} />
          <DetailRow label="落户地点" value={position.settle_location} />
          <DetailRow label="备注" value={position.remarks} />
          <DetailRow label="咨询电话1" value={position.phone1} />
          <DetailRow label="咨询电话2" value={position.phone2} />
          <DetailRow label="咨询电话3" value={position.phone3} />
          {position.dept_website && (
            <div className="flex flex-col sm:flex-row sm:gap-2 text-sm py-1.5 border-b border-paper-100">
              <span className="text-ink-400 shrink-0 sm:w-28">部门网站</span>
              <a
                href={position.dept_website}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-blue-600 hover:underline break-all"
              >
                <Globe className="h-3.5 w-3.5" />
                {position.dept_website}
              </a>
            </div>
          )}
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
