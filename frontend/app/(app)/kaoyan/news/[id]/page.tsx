"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Calendar, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/form-controls";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Markdown } from "@/components/ui/markdown";
import { QualityBadge } from "@/components/ui/quality-badge";
import { SourceBadge } from "@/components/ui/source-badge";
import { kaoyanNewsApi } from "@/lib/api";
import type { KaoyanNewsResponse } from "@/types";

function hasSource(news: KaoyanNewsResponse): boolean {
  return Boolean(news.source_url && news.source_url.trim());
}

function formatDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleDateString("zh-CN");
}

export default function KaoyanNewsDetailPage() {
  const params = useParams<{ id: string }>();
  const id = typeof params?.id === "string" ? params.id : "";
  const [news, setNews] = useState<KaoyanNewsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) {
      setError("缺少资讯 ID");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setNews(await kaoyanNewsApi.get(id));
    } catch {
      setError("加载资讯详情失败，请稍后重试");
      setNews(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-3xl px-4 py-6 md:py-8">
        <Link
          href="/kaoyan/news"
          className="mb-5 inline-flex items-center gap-1.5 text-sm text-ink-500 transition-colors hover:text-brand-600"
        >
          <ArrowLeft className="h-4 w-4" />
          返回资讯中心
        </Link>

        {loading ? (
          <LoadingState text="加载资讯详情…" />
        ) : error || !news ? (
          <EmptyState
            title="资讯不可用"
            description={error ?? "该资讯可能已被移除。"}
            action={
              <Link href="/kaoyan/news">
                <span className="text-sm font-medium text-brand-600 hover:text-brand-700">返回列表</span>
              </Link>
            }
          />
        ) : (
          <article className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
            <div className="mb-3 flex items-start justify-between gap-3">
              <h1 className="font-display text-xl font-bold leading-snug text-ink-900 sm:text-2xl">
                {news.title}
              </h1>
              <QualityBadge
                grade={news.quality_grade}
                score={news.quality_score}
                reasons={news.quality_reasons}
              />
            </div>

            <div className="mb-5 flex flex-wrap items-center gap-2 text-xs text-ink-400">
              {hasSource(news) ? (
                <SourceBadge sourceUrl={news.source_url} sourcePlatform={news.source_platform} />
              ) : (
                <span title="该条目未收录 source_url，无可核对原文">
                  <Badge color="red">无原文链接</Badge>
                </span>
              )}
              {(formatDate(news.published_at) ?? formatDate(news.crawled_at)) && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  {formatDate(news.published_at) ?? formatDate(news.crawled_at)}
                </span>
              )}
              {news.category && news.category !== "general" && <Badge color="blue">{news.category}</Badge>}
              {news.is_expired && <Badge color="amber">已过期</Badge>}
              {news.tags?.map((tag) => (
                <Badge key={tag} color="slate">
                  {tag}
                </Badge>
              ))}
            </div>

            {news.key_dates && news.key_dates.length > 0 && (
              <div className="mb-5 rounded-lg border border-paper-200 bg-paper-50 p-4">
                <h2 className="mb-2 text-sm font-semibold text-ink-700">关键时间节点</h2>
                <ul className="space-y-1 text-sm text-ink-600">
                  {news.key_dates.map((item) => (
                    <li key={`${item.label}-${item.date}`}>
                      {item.label}：{item.date}
                      {item.end_date ? ` — ${item.end_date}` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {news.ai_summary && (
              <div className="mb-5 rounded-lg border border-brand-100 bg-brand-50/50 p-4">
                <h2 className="mb-1 text-sm font-semibold text-ink-700">AI 摘要（模型生成，仅供参考）</h2>
                <p className="text-sm leading-relaxed text-ink-600">{news.ai_summary}</p>
              </div>
            )}

            {news.summary && !news.ai_summary && (
              <p className="mb-5 text-sm leading-relaxed text-ink-600">{news.summary}</p>
            )}

            {news.content ? (
              <Markdown content={news.content} />
            ) : (
              <EmptyState
                title="仅收录摘要"
                description="该条目未抓取到正文，请通过原文链接核对完整内容。"
                className="py-8"
              />
            )}

            <div className="mt-6 border-t border-paper-200 pt-4">
              {hasSource(news) ? (
                <a
                  href={news.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-brand-600 hover:text-brand-700"
                >
                  查看原文
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              ) : (
                <p className="text-sm text-ink-400">该条目未收录原文链接，无法溯源核对。</p>
              )}
            </div>
          </article>
        )}
      </div>
    </div>
  );
}
