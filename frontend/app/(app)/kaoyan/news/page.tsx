"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Calendar, ExternalLink, Newspaper, RefreshCw, Search } from "lucide-react";
import { Badge, Button, Input } from "@/components/ui/form-controls";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Pagination } from "@/components/ui/pagination";
import { QualityBadge } from "@/components/ui/quality-badge";
import { SourceBadge } from "@/components/ui/source-badge";
import { kaoyanNewsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { KaoyanNewsResponse } from "@/types";

const PAGE_SIZE = 10;
const ALL_CATEGORIES = "全部";

/** 无 source_url 的条目不提供原文入口，页面上显式标注（不包装成有源）。 */
function hasSource(news: KaoyanNewsResponse): boolean {
  return Boolean(news.source_url && news.source_url.trim());
}

function formatDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleDateString("zh-CN");
}

function NewsCard({ news }: { news: KaoyanNewsResponse }) {
  const sourced = hasSource(news);
  const dateText = formatDate(news.published_at) ?? formatDate(news.crawled_at);

  return (
    <article className="rounded-xl border border-paper-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md">
      <div className="mb-2 flex items-start justify-between gap-3">
        <Link
          href={`/kaoyan/news/${news.id}`}
          className="line-clamp-2 font-semibold text-ink-900 transition-colors hover:text-brand-600"
        >
          {news.title}
        </Link>
        <QualityBadge grade={news.quality_grade} score={news.quality_score} reasons={news.quality_reasons} />
      </div>

      {news.summary && <p className="mb-3 line-clamp-2 text-sm text-ink-500">{news.summary}</p>}

      <div className="flex flex-wrap items-center gap-2 text-xs text-ink-400">
        {sourced ? (
          <SourceBadge sourceUrl={news.source_url} sourcePlatform={news.source_platform} />
        ) : (
          <span title="该条目未收录 source_url，无可核对原文">
            <Badge color="red">无原文链接</Badge>
          </span>
        )}
        {dateText && (
          <span className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {dateText}
          </span>
        )}
        {news.category && news.category !== "general" && <Badge color="blue">{news.category}</Badge>}
        {news.is_expired && <Badge color="amber">已过期</Badge>}
        {sourced && (
          <a
            href={news.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-brand-600 hover:text-brand-700"
          >
            原文
            <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>
    </article>
  );
}

export default function KaoyanNewsPage() {
  const [items, setItems] = useState<KaoyanNewsResponse[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [category, setCategory] = useState(ALL_CATEGORIES);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await kaoyanNewsApi.list({
        page,
        page_size: PAGE_SIZE,
        category: category === ALL_CATEGORIES ? undefined : category,
        search: search || undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setError("加载资讯失败，请稍后重试");
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, category, search]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    kaoyanNewsApi
      .categories()
      .then((res) => setCategories(res.categories ?? []))
      .catch(() => setCategories([]));
  }, []);

  const handleSearch = (event: React.FormEvent) => {
    event.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  };

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-4xl px-4 py-6 md:py-8">
        <div className="mb-6">
          <div className="mb-2 flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-brand-sm">
              <Newspaper className="h-5 w-5" strokeWidth={2.2} />
            </div>
            <h1 className="font-display text-xl font-bold tracking-tight text-ink-900 sm:text-2xl">
              考研资讯中心
            </h1>
          </div>
          <p className="ml-[46px] text-sm text-ink-500">
            每条资讯标注来源平台与质量等级，可跳转原文核对。
          </p>
        </div>

        <div className="mb-5 flex flex-col gap-3 sm:flex-row">
          <form onSubmit={handleSearch} className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="搜索资讯标题或内容…"
              aria-label="搜索考研资讯"
              className="pl-9"
            />
          </form>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={handleSearch}>
              搜索
            </Button>
            <Button type="button" variant="ghost" onClick={load} disabled={loading}>
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
              刷新
            </Button>
          </div>
        </div>

        {categories.length > 0 && (
          <div className="mb-5 flex flex-wrap gap-2">
            {[ALL_CATEGORIES, ...categories].map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => {
                  setCategory(item);
                  setPage(1);
                }}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                  category === item
                    ? "border-brand-600 bg-brand-600 text-white"
                    : "border-paper-200 bg-white text-ink-600 hover:bg-paper-100",
                )}
              >
                {item}
              </button>
            ))}
          </div>
        )}

        {loading ? (
          <LoadingState text="加载资讯…" />
        ) : error ? (
          <EmptyState
            title="资讯加载失败"
            description={error}
            action={
              <Button size="sm" variant="secondary" onClick={load}>
                重试
              </Button>
            }
          />
        ) : items.length === 0 ? (
          <EmptyState
            title="暂无资讯"
            description={
              search || category !== ALL_CATEGORIES
                ? "当前筛选条件下没有资讯，试试清空筛选。"
                : "资讯库暂时为空。"
            }
          />
        ) : (
          <div className="space-y-3">
            {items.map((news) => (
              <NewsCard key={news.id} news={news} />
            ))}
          </div>
        )}

        {!loading && !error && <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />}
      </div>
    </div>
  );
}
