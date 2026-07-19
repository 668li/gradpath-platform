"use client";

import { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { Search as SearchIcon, Globe, Loader2, ChevronLeft, ChevronRight, Sparkles, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { getToken, ragSearchApi } from "@/lib/api";
import { Badge } from "@/components/ui/form-controls";

/** 根据搜索结果类型和ID生成详情页链接 */
function getResultUrl(type: string, id: string, metadata?: any): string {
  if (metadata?.source === "web" && metadata?.url) return metadata.url;
  switch (type) {
    case "experience":
      return `/kaoyan/community/posts/${id}`;
    case "qa":
      return `/kaoyan/community/qa/${id}`;
    case "knowledge":
      return `/kaoyan/community/posts/${id}`; // knowledge also uses post detail
    default:
      return `/kaoyan/community/posts/${id}`;
  }
}

interface SearchResult {
  id: string;
  type: "experience" | "knowledge" | "qa" | "dark";
  title: string;
  content: string;
  highlight?: string;
  score: number;
  metadata?: Record<string, unknown>;
}

interface SearchResponse {
  query: string;
  type: string;
  total: number;
  page: number;
  page_size: number;
  results: SearchResult[];
}

const TYPE_FILTERS = [
  { key: "all", label: "全部" },
  { key: "experience", label: "经验帖" },
  { key: "knowledge", label: "知识文章" },
  { key: "qa", label: "问答" },
  { key: "dark", label: "暗知识" },
] as const;

const TYPE_BADGE: Record<string, { label: string; className: string }> = {
  experience: { label: "经验", className: "bg-blue-100 text-blue-700" },
  knowledge: { label: "知识", className: "bg-green-100 text-green-700" },
  qa: { label: "问答", className: "bg-purple-100 text-purple-700" },
  dark: { label: "暗知识", className: "bg-amber-100 text-amber-700" },
};

const RAG_SOURCE_LABEL: Record<string, string> = {
  experience: "经验",
  knowledge: "知识",
  qa: "问答",
  dark: "暗知识",
};

const RAG_SOURCE_COLOR: Record<string, "blue" | "green" | "purple" | "amber"> = {
  experience: "blue",
  knowledge: "green",
  qa: "purple",
  dark: "amber",
};

interface RAGResult {
  id: string;
  title: string;
  content: string;
  score: number;
  source?: string;
  url?: string;
  metadata?: Record<string, unknown>;
}

function highlightText(text: string, query: string): string {
  if (!query) return text;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return text.replace(new RegExp(escaped, "gi"), (m) => `<<HL>>${m}<</HL>>`);
}

function HighlightedContent({ text, query }: { text: string; query: string }) {
  const parts = highlightText(text, query).split(/(<<HL>>|<\/HL>>)/g);
  let inHighlight = false;
  return (
    <>
      {parts.map((part, i) => {
        if (part === "<<HL>>") {
          inHighlight = true;
          return null;
        }
        if (part === "<</HL>>") {
          inHighlight = false;
          return null;
        }
        if (inHighlight) {
          return (
            <mark key={i} className="bg-brand-200 text-brand-900 rounded px-0.5">
              {part}
            </mark>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [webSearch, setWebSearch] = useState(false);
  const [ragMode, setRagMode] = useState(false);
  const [ragResults, setRagResults] = useState<RAGResult[]>([]);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const PAGE_SIZE = 20;

  const doSearch = useCallback(
    async (q: string, type: string, p: number) => {
      if (!q.trim()) return;
      setLoading(true);
      setSearched(true);
      try {
        if (ragMode) {
          const data = await ragSearchApi.search({ query: q });
          setRagResults(data.results || []);
          setTotal(data.total || 0);
          setResults([]);
        } else if (webSearch) {
          setRagResults([]);
          const token = getToken();
          const res = await fetch(`/api/ai/agent/web-search?q=${encodeURIComponent(q)}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          });
          const data = await res.json();
          const webResults: SearchResult[] = (data.results || data.data || data || []).map(
            (r: any, i: number) => ({
              id: r.id || `web-${i}`,
              type: "knowledge" as const,
              title: r.title || r.name || "网页结果",
              content: r.snippet || r.content || r.description || "",
              highlight: r.title,
              score: r.score || 0.8,
              metadata: { source: "web", url: r.url || r.link },
            }),
          );
          setResults(webResults);
          setTotal(webResults.length);
        } else {
          setRagResults([]);
          const params = new URLSearchParams({
            q,
            type,
            page: String(p),
            page_size: String(PAGE_SIZE),
          });
          const res = await fetch(`/api/search?${params}`);
          const data: SearchResponse = await res.json();
          setResults(data.results || []);
          setTotal(data.total || 0);
        }
      } catch {
        setResults([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    },
    [ragMode, webSearch],
  );

  const handleSearch = () => {
    setPage(1);
    doSearch(query, typeFilter, 1);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  const handlePageChange = (p: number) => {
    setPage(p);
    doSearch(query, typeFilter, p);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  useEffect(() => {
    if (!searched) return;
    doSearch(query, typeFilter, page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typeFilter]);

  const totalPages = Math.ceil(total / PAGE_SIZE) || 1;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Search Bar */}
      <div className="mb-8">
        <h1 className="font-display text-2xl font-bold text-ink-800 mb-6">全局搜索</h1>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="搜索经验帖、知识文章、问答、暗知识..."
              className="w-full rounded-xl border border-paper-300 bg-white pl-12 pr-4 py-4 text-base text-ink-800 placeholder:text-ink-400 focus:border-brand-400 focus:ring-2 focus:ring-brand-200 focus:outline-none transition-colors shadow-sm"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={!query.trim() || loading}
            className="rounded-xl bg-brand-500 px-6 py-4 text-base font-medium text-white hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-brand-sm"
          >
            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : "搜索"}
          </button>
        </div>

        {/* Toggle & Filters */}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={() => setWebSearch(!webSearch)}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              webSearch
                ? "bg-brand-100 text-brand-700 ring-1 ring-brand-300"
                : "bg-paper-100 text-ink-500 hover:bg-paper-200",
            )}
          >
            <Globe className="h-4 w-4" />
            网页搜索
          </button>
          <button
            onClick={() => setRagMode(!ragMode)}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              ragMode
                ? "bg-purple-100 text-purple-700 ring-1 ring-purple-300"
                : "bg-paper-100 text-ink-500 hover:bg-paper-200",
            )}
          >
            <Sparkles className="h-4 w-4" />
            智能检索
          </button>
          {!webSearch && !ragMode && (
            <div className="flex gap-1">
              {TYPE_FILTERS.map((f) => (
                <button
                  key={f.key}
                  onClick={() => setTypeFilter(f.key)}
                  className={cn(
                    "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                    typeFilter === f.key
                      ? "bg-ink-800 text-paper-50"
                      : "bg-paper-100 text-ink-500 hover:bg-paper-200",
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="animate-pulse rounded-xl border border-paper-200 bg-white p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="h-5 w-24 rounded bg-slate-200" />
                <div className="h-5 w-16 rounded bg-slate-200" />
              </div>
              <div className="h-4 w-3/4 rounded bg-slate-200 mb-2" />
              <div className="h-4 w-1/2 rounded bg-slate-200" />
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !searched && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-paper-200 mb-5">
            <SearchIcon className="h-8 w-8 text-ink-300" strokeWidth={1.5} />
          </div>
          <p className="font-display text-lg font-medium text-ink-700">输入关键词开始搜索</p>
          <p className="mt-1.5 text-sm text-ink-400">
            支持搜索经验帖、知识文章、问答和暗知识内容
          </p>
        </div>
      )}

      {/* No Results */}
      {!loading && searched && results.length === 0 && ragResults.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-paper-200 mb-5">
            <SearchIcon className="h-8 w-8 text-ink-300" strokeWidth={1.5} />
          </div>
          <p className="font-display text-lg font-medium text-ink-700">未找到相关内容</p>
          <p className="mt-1.5 text-sm text-ink-400">试试其他关键词或切换搜索类型</p>
        </div>
      )}

      {/* Results */}
      {!loading && (results.length > 0 || ragResults.length > 0) && (
        <>
          <p className="mb-4 text-sm text-ink-500">
            找到 <span className="font-semibold text-ink-700">{total}</span> 条结果
            {ragMode && <span className="ml-2 text-purple-600">（智能检索模式）</span>}
          </p>
          <div className="space-y-3">
            {/* RAG results */}
            {ragResults.map((r) => (
              <Link
                key={r.id}
                href={r.url || getResultUrl(r.source || "experience", r.id, r.metadata)}
                target={r.metadata?.source === "web" ? "_blank" : undefined}
                className="block rounded-xl border border-paper-200 bg-white p-5 hover:border-purple-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Badge color={RAG_SOURCE_COLOR[r.source || ""] || "slate"}>
                    {RAG_SOURCE_LABEL[r.source || ""] || r.source || "未知"}
                  </Badge>
                  <span className="text-xs text-ink-400">
                    相关度 {(r.score * 100).toFixed(0)}%
                  </span>
                </div>
                <h3 className="font-display text-base font-semibold text-ink-800 mb-1.5 line-clamp-1">
                  <HighlightedContent text={r.title} query={query} />
                </h3>
                <p className="text-sm text-ink-500 line-clamp-2 leading-relaxed">
                  <HighlightedContent
                    text={
                      r.content.length > 200
                        ? r.content.replace(/!\[.*?\]\(.*?\)/g, "").slice(0, 200) + "..."
                        : r.content.replace(/!\[.*?\]\(.*?\)/g, "")
                    }
                    query={query}
                  />
                </p>
                {typeof r.metadata?.context === "string" && r.metadata.context && (
                  <p className="mt-2 text-xs text-ink-400 line-clamp-1 italic">
                    {r.metadata.context.slice(0, 120)}
                    {r.metadata.context.length > 120 ? "..." : ""}
                  </p>
                )}
              </Link>
            ))}
            {/* Standard results */}
            {results.map((r) => {
              const badge = TYPE_BADGE[r.type] || { label: r.type, className: "bg-slate-100 text-slate-600" };
              return (
                <Link
                  key={r.id}
                  href={getResultUrl(r.type, r.id, r.metadata)}
                  target={r.metadata?.source === "web" ? "_blank" : undefined}
                  className="block rounded-xl border border-paper-200 bg-white p-5 hover:border-brand-300 hover:shadow-sm transition-all"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className={cn("rounded-md px-2 py-0.5 text-xs font-medium", badge.className)}>
                      {badge.label}
                    </span>
                    {r.score > 0 && (
                      <span className="text-xs text-ink-400">
                        相关度 {(r.score * 100).toFixed(0)}%
                      </span>
                    )}
                    {r.metadata?.source === "web" && (
                      <span className="text-xs text-ink-400">网页结果</span>
                    )}
                  </div>
                  <h3 className="font-display text-base font-semibold text-ink-800 mb-1.5 line-clamp-1">
                    {r.highlight ? (
                      <HighlightedContent text={r.title} query={query} />
                    ) : (
                      r.title
                    )}
                  </h3>
                  <p className="text-sm text-ink-500 line-clamp-2 leading-relaxed">
                    <HighlightedContent
                      text={
                        r.content.length > 200
                          ? r.content.replace(/!\[.*?\]\(.*?\)/g, "").slice(0, 200) + "..."
                          : r.content.replace(/!\[.*?\]\(.*?\)/g, "")
                      }
                      query={query}
                    />
                  </p>
                  {Array.isArray(r.metadata?.tags) && (r.metadata!.tags as string[]).length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {(r.metadata.tags as string[]).slice(0, 4).map((tag) => (
                        <span
                          key={tag}
                          className="rounded bg-paper-100 px-1.5 py-0.5 text-xs text-ink-500"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </Link>
              );
            })}
          </div>

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1}
                className={cn(
                  "p-2 rounded-md text-ink-400 hover:bg-paper-200 hover:text-ink-600 disabled:opacity-30 disabled:cursor-not-allowed",
                )}
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm text-ink-500">
                第 {page} / {totalPages} 页（共 {total} 条）
              </span>
              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= totalPages}
                className={cn(
                  "p-2 rounded-md text-ink-400 hover:bg-paper-200 hover:text-ink-600 disabled:opacity-30 disabled:cursor-not-allowed",
                )}
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
