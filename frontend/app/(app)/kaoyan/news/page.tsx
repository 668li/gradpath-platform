"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import useSWR from "swr";
import {
  Newspaper,
  Search,
  ArrowUpDown,
  CalendarClock,
  AlertTriangle,
  ShieldCheck,
} from "lucide-react";
import { kaoyanNewsApi } from "@/lib/api";
import { Badge, Button } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Pagination } from "@/components/ui/pagination";
import { SourceBadge } from "@/components/ui/source-badge";
import { QualityBadge } from "@/components/ui/quality-badge";
import { mostUrgentKeyDate, formatDate } from "./key-dates";
import type { KaoyanNewsResponse } from "@/types";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 10;

/** 分类 tab 兜底（接口无数据时仍展示标准分类） */
const FALLBACK_CATEGORIES = [
  "政策",
  "招生简章",
  "复试",
  "调剂",
  "复试线",
  "推免",
  "报录比",
  "择校",
  "备考",
];

const SOURCE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "全部来源" },
  { value: "eol_kaoyan", label: "中国教育在线" },
  { value: "official_announce", label: "高校公告" },
  { value: "rss", label: "新浪教育" },
];

const GRADE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "全部质量" },
  { value: "A", label: "A 优质" },
  { value: "B", label: "B 良好" },
  { value: "C", label: "C 一般" },
  { value: "D", label: "D 低质" },
];

function NewsItemCard({ news }: { news: KaoyanNewsResponse }) {
  const urgent = mostUrgentKeyDate(news.key_dates);
  const dateText = formatDate(news.published_at) ?? formatDate(news.crawled_at);

  return (
    <article
      className={cn(
        "rounded-xl border bg-white p-4 shadow-sm transition-shadow hover:shadow-md",
        news.is_expired ? "border-ink-200 opacity-70" : "border-paper-200",
      )}
    >
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <QualityBadge grade={news.quality_grade} score={news.quality_score} />
        {news.category && news.category !== "general" && (
          <Badge color="blue" className="text-xs">
            {news.category}
          </Badge>
        )}
        {news.is_expired && (
          <span title="关键时间点已过或超过 180 天">
            <Badge color="slate" className="text-xs">
              <AlertTriangle className="h-3 w-3 mr-1" /> 已过期
            </Badge>
          </span>
        )}
      </div>

      <h3 className="font-semibold text-ink-900 leading-snug mb-1.5">
        <Link
          href={`/kaoyan/news/${news.id}`}
          className="hover:text-brand-600 transition-colors line-clamp-2"
        >
          {news.title}
        </Link>
      </h3>

      {/* AI 提纯摘要（信息差核心卖点） */}
      {news.ai_summary && (
        <p className="text-sm text-ink-500 mb-2.5 line-clamp-2 leading-relaxed">
          {news.ai_summary}
        </p>
      )}

      {/* 关键日期倒计时高亮 */}
      {urgent && (
        <div
          className={cn(
            "mb-2.5 inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium",
            urgent.urgent
              ? "bg-red-50 text-red-600"
              : "bg-brand-50 text-brand-700",
          )}
        >
          <CalendarClock className="h-3 w-3" />
          {urgent.text}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-400">
        <SourceBadge sourceUrl={news.source_url} sourcePlatform={news.source_platform} showPlatform={false} />
        {dateText && <span>{dateText}</span>}
      </div>
    </article>
  );
}

export default function KaoyanNewsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const category = searchParams.get("category") || "";
  const search = searchParams.get("search") || "";
  const sort = searchParams.get("sort") || "latest";
  const quality_grade = searchParams.get("quality_grade") || "";
  const source_platform = searchParams.get("source_platform") || "";
  const page = parseInt(searchParams.get("page") || "1", 10);

  const listKey = `/api/kaoyan-news?category=${category}&search=${search}&sort=${sort}&grade=${quality_grade}&platform=${source_platform}&page=${page}`;
  const { data, isLoading, error } = useSWR(listKey, () =>
    kaoyanNewsApi.list({
      category: category || undefined,
      search: search || undefined,
      sort: (sort === "quality" ? "quality" : "latest"),
      quality_grade: quality_grade || undefined,
      source_platform: source_platform || undefined,
      page,
      page_size: PAGE_SIZE,
    }),
  );

  const { data: categoriesData } = useSWR("/api/kaoyan-news/categories", () =>
    kaoyanNewsApi.categories(),
  );
  const categories = useMemo(() => {
    const fromApi = categoriesData?.categories ?? [];
    const merged = [...new Set([...fromApi, ...FALLBACK_CATEGORIES])];
    return fromApi.length > 0 ? merged : FALLBACK_CATEGORIES;
  }, [categoriesData]);

  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    if (key !== "page") params.set("page", "1");
    router.push(`/kaoyan/news?${params.toString()}`);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.currentTarget as HTMLFormElement;
    const input = form.elements.namedItem("search") as HTMLInputElement;
    updateFilter("search", input.value.trim());
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      {/* 页头 */}
      <header className="mb-5">
        <h1 className="text-2xl font-bold text-ink-900 flex items-center gap-2">
          <Newspaper className="h-6 w-6 text-brand-600" />
          资讯中心
        </h1>
        <p className="mt-1 text-sm text-ink-500 flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="inline-flex items-center gap-1">
            <ShieldCheck className="h-3.5 w-3.5 text-green-500" />
            考研 / 考公 / 就业多赛道 · 相似去重 · 质量分级 · 关键日期解读
          </span>
          <span className="inline-flex items-center gap-1 text-ink-400">
            <ArrowUpDown className="h-3.5 w-3.5" />
            已按「最新 / 质量」排序，可切换
          </span>
        </p>
      </header>

      {/* 筛选区 */}
      <div className="mb-4 space-y-3">
        {/* 分类 tab */}
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => updateFilter("category", "")}
            className={cn(
              "rounded-full px-3 py-1 text-sm transition-colors",
              category === ""
                ? "bg-brand-600 text-white"
                : "bg-ink-100 text-ink-600 hover:bg-ink-200",
            )}
          >
            全部
          </button>
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => updateFilter("category", c)}
              className={cn(
                "rounded-full px-3 py-1 text-sm transition-colors",
                category === c
                  ? "bg-brand-600 text-white"
                  : "bg-ink-100 text-ink-600 hover:bg-ink-200",
              )}
            >
              {c}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* 搜索 */}
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-1.5">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-400" />
              <input
                name="search"
                defaultValue={search}
                placeholder="搜索资讯关键词…"
                className="rounded-md border border-paper-300 bg-white pl-8 pr-2 py-1.5 text-sm w-56 focus:outline-none focus:ring-2 focus:ring-brand-200"
              />
            </div>
            <Button type="submit" size="sm">搜索</Button>
          </form>

          {/* 排序 */}
          <div className="flex rounded-md border border-paper-300 overflow-hidden">
            {(["latest", "quality"] as const).map((s) => (
              <button
                key={s}
                onClick={() => updateFilter("sort", s === "latest" ? "" : "quality")}
                className={cn(
                  "px-3 py-1.5 text-sm transition-colors",
                  sort === s ? "bg-brand-50 text-brand-700 font-medium" : "bg-white text-ink-500 hover:bg-ink-50",
                )}
              >
                {s === "latest" ? "最新" : "按质量"}
              </button>
            ))}
          </div>

          {/* 来源筛选 */}
          <select
            value={source_platform}
            onChange={(e) => updateFilter("source_platform", e.target.value)}
            className="rounded-md border border-paper-300 bg-white px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-200"
          >
            {SOURCE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          {/* 质量筛选 */}
          <select
            value={quality_grade}
            onChange={(e) => updateFilter("quality_grade", e.target.value)}
            className="rounded-md border border-paper-300 bg-white px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-200"
          >
            {GRADE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          {data && data.total > 0 && (
            <span className="ml-auto text-sm text-ink-400">
              共 {data.total} 条
            </span>
          )}
        </div>
      </div>

      {/* 列表 */}
      {isLoading ? (
        <LoadingState text="正在加载资讯…" />
      ) : error ? (
        <EmptyState title="加载失败" description="资讯服务暂不可用，请稍后重试" />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          title="暂无相关资讯"
          description="换个筛选条件试试，或等待新一批提纯后的资讯入库"
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {data.items.map((item) => (
            <NewsItemCard key={item.id} news={item} />
          ))}
        </div>
      )}

      {data && (
        <Pagination
          page={data.page}
          pageSize={data.page_size}
          total={data.total}
          onPageChange={(p) => updateFilter("page", String(p))}
        />
      )}
    </div>
  );
}
