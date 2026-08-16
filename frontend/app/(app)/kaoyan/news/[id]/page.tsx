"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Newspaper,
  ExternalLink,
  CalendarClock,
  Sparkles,
  Clock,
  ShieldCheck,
  FileText,
  AlertTriangle,
  BarChart3,
  BookText,
} from "lucide-react";
import { kaoyanNewsApi } from "@/lib/api";
import { Badge } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { SourceBadge } from "@/components/ui/source-badge";
import { QualityBadge } from "@/components/ui/quality-badge";
import { QualityFeedback } from "@/components/kaoyan/quality-feedback";
import { countdownOf, formatDate } from "../key-dates";
import type { KaoyanNewsResponse, KaoyanKeyDate, NewsStructuredMeta } from "@/types";
import { cn } from "@/lib/utils";

function KeyDateRow({ kd }: { kd: KaoyanKeyDate }) {
  const info = countdownOf(kd);
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 rounded-lg border px-3 py-2",
        info.expired
          ? "border-ink-200 bg-ink-50 opacity-70"
          : info.urgent
            ? "border-red-200 bg-red-50"
            : "border-paper-200 bg-white",
      )}
    >
      <div className="flex items-center gap-2">
        <CalendarClock
          className={cn(
            "h-4 w-4",
            info.expired ? "text-ink-400" : info.urgent ? "text-red-500" : "text-brand-600",
          )}
        />
        <div>
          <p className="text-sm font-medium text-ink-800">{kd.label}</p>
          <p className="text-xs text-ink-400">
            {kd.date}
            {kd.end_date ? ` 至 ${kd.end_date}` : ""}
          </p>
        </div>
      </div>
      <span
        className={cn(
          "text-sm font-semibold whitespace-nowrap",
          info.expired ? "text-ink-400" : info.urgent ? "text-red-600" : "text-brand-700",
        )}
      >
        {info.text}
      </span>
    </div>
  );
}

/** 决策数据卡（Phase G）：资讯结构化元信息（招生人数/考试科目/参考书目）。
 *  Phase I：+ 数据年份徽章（effective_year）+ 提取依据（evidence 原文证据）。
 *  规则抽取；所有维度全抽不到时不渲染（诚实降级），不影响 key_dates 逻辑。 */
function NewsStructuredCard({ meta }: { meta?: NewsStructuredMeta | null }) {
  if (!meta) return null;
  const evidenceEntries = meta.evidence ? Object.entries(meta.evidence) : [];
  const has =
    meta.enrollment_count != null ||
    (meta.exam_subjects?.length ?? 0) > 0 ||
    (meta.reference_books?.length ?? 0) > 0 ||
    meta.effective_year != null ||
    evidenceEntries.length > 0;
  if (!has) return null;
  return (
    <section className="px-5 mt-5">
      <h2 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-ink-800">
        <BarChart3 className="h-4 w-4 text-brand-600" />
        决策数据卡
        {meta.effective_year != null && (
          <span
            className="inline-flex items-center rounded-md border border-brand-200 bg-brand-50 px-1.5 py-0.5 text-xs font-medium text-brand-700"
            title="数据对应年份（规则抽取，抽不到不展示）"
          >
            {meta.effective_year} 年数据
          </span>
        )}
      </h2>
      <div className="space-y-3 rounded-lg border border-paper-200 bg-paper-50/60 p-4">
        {meta.enrollment_count != null && (
          <div className="flex items-baseline gap-2">
            <span className="w-16 shrink-0 text-xs text-ink-400">招生人数</span>
            <span className="text-lg font-bold text-brand-700">
              {meta.enrollment_count}
              <span className="ml-1 text-xs font-normal text-ink-400">人</span>
            </span>
          </div>
        )}
        {meta.exam_subjects && meta.exam_subjects.length > 0 && (
          <div className="flex items-start gap-2">
            <span className="w-16 shrink-0 pt-0.5 text-xs text-ink-400">考试科目</span>
            <div className="flex flex-wrap gap-1.5">
              {meta.exam_subjects.map((s) => (
                <Badge key={s} color="blue" className="text-xs">
                  {s}
                </Badge>
              ))}
            </div>
          </div>
        )}
        {meta.reference_books && meta.reference_books.length > 0 && (
          <div className="flex items-start gap-2">
            <span className="w-16 shrink-0 pt-0.5 text-xs text-ink-400">参考书目</span>
            <ul className="space-y-1">
              {meta.reference_books.map((b) => (
                <li key={b} className="inline-flex items-center gap-1 text-sm text-ink-700">
                  <BookText className="h-3.5 w-3.5 shrink-0 text-ink-400" />
                  《{b}》
                </li>
              ))}
            </ul>
          </div>
        )}
        {evidenceEntries.length > 0 && (
          <details className="rounded-md border border-paper-200 bg-white px-2 py-1.5 text-xs text-ink-600">
            <summary className="cursor-pointer font-medium text-ink-700">
              提取依据（原文证据 · 置信度）
            </summary>
            <ul className="mt-1 space-y-0.5">
              {evidenceEntries.map(([field, snippet]) => (
                <li key={field}>
                  {field} · 原文「{snippet}」
                  {meta.confidence?.[field] != null && (
                    <span className="text-ink-400">
                      {" "}
                      · 置信度 {Math.round(meta.confidence![field] * 100)}%
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </section>
  );
}

export default function KaoyanNewsDetailPage() {
  const params = useParams();
  const router = useRouter();
  const newsId = params.id as string;

  const [news, setNews] = useState<KaoyanNewsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await kaoyanNewsApi.get(newsId);
      setNews(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [newsId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <LoadingState text="正在加载资讯详情…" />
      </div>
    );
  }

  if (error || !news) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <EmptyState
          title="资讯不存在"
          description="该资讯可能已被移除，或链接有误"
          action={
            <button
              onClick={() => router.push("/kaoyan/news")}
              className="text-sm text-brand-600 hover:underline"
            >
              返回资讯中心
            </button>
          }
        />
      </div>
    );
  }

  const dateText = formatDate(news.published_at) ?? formatDate(news.crawled_at);
  const crawledText = formatDate(news.crawled_at);

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <Link
        href="/kaoyan/news"
        className="mb-4 inline-flex items-center gap-1 text-sm text-ink-500 hover:text-brand-600"
      >
        <ArrowLeft className="h-4 w-4" />
        返回资讯中心
      </Link>

      <article className="rounded-xl border border-paper-200 bg-white shadow-sm">
        {/* 头部 */}
        <header className="border-b border-paper-100 p-5">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <QualityBadge
              grade={news.quality_grade}
              score={news.quality_score}
              reasons={news.quality_reasons}
            />
            {news.category && news.category !== "general" && (
              <Badge color="blue" className="text-xs">{news.category}</Badge>
            )}
            {news.is_expired && (
              <span title="关键时间点已过或超过 180 天">
                <Badge color="slate" className="text-xs">
                  <AlertTriangle className="h-3 w-3 mr-1" /> 已过期
                </Badge>
              </span>
            )}
            <div className="ml-auto">
              <QualityFeedback targetType="kaoyan_news" targetId={news.id} />
            </div>
          </div>

          <h1 className="text-xl font-bold text-ink-900 leading-snug mb-3">
            <span className="inline-flex items-start gap-2">
              <Newspaper className="h-5 w-5 text-brand-600 mt-1 shrink-0" />
              {news.title}
            </span>
          </h1>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-400">
            <SourceBadge sourceUrl={news.source_url} sourcePlatform={news.source_platform} />
            {dateText && (
              <span className="inline-flex items-center gap-1">
                <Clock className="h-3 w-3" />
                发布 {dateText}
              </span>
            )}
          </div>
        </header>

        {/* AI 解读（提纯卖点） */}
        {news.ai_summary && (
          <section className="mx-5 mt-5 rounded-lg border border-brand-100 bg-brand-50/60 p-4">
            <h2 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-brand-700">
              <Sparkles className="h-4 w-4" />
              AI 解读
            </h2>
            <p className="text-sm leading-relaxed text-ink-700">{news.ai_summary}</p>
          </section>
        )}

        {/* 关键时间点 */}
        {news.key_dates && news.key_dates.length > 0 && (
          <section className="px-5 mt-5">
            <h2 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-ink-800">
              <CalendarClock className="h-4 w-4 text-brand-600" />
              关键时间点
            </h2>
            <div className="space-y-2">
              {news.key_dates.map((kd, i) => (
                <KeyDateRow key={`${kd.label}-${kd.date}-${i}`} kd={kd} />
              ))}
            </div>
          </section>
        )}

        {/* 决策数据卡（Phase G：招生人数/科目/参考书，抽不到不渲染） */}
        <NewsStructuredCard meta={news.structured_meta} />

        {/* 正文 */}
        <section className="p-5">
          <h2 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-ink-800">
            <FileText className="h-4 w-4 text-brand-600" />
            正文
          </h2>
          {news.content ? (
            <div className="prose prose-sm max-w-none text-ink-700 leading-relaxed whitespace-pre-wrap">
              {news.content}
            </div>
          ) : news.summary ? (
            <p className="text-sm leading-relaxed text-ink-600">{news.summary}</p>
          ) : (
            <p className="text-sm text-ink-400">（该资讯无正文内容，请访问来源页查看）</p>
          )}
        </section>

        {/* 来源溯源卡 */}
        <footer className="mx-5 mb-5 rounded-lg border border-paper-200 bg-paper-50 p-4">
          <h2 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-ink-800">
            <ShieldCheck className="h-4 w-4 text-green-600" />
            来源溯源
          </h2>
          <dl className="grid gap-1.5 text-xs text-ink-500 sm:grid-cols-2">
            <div>
              <dt className="text-ink-400">来源可信度</dt>
              <dd className="mt-0.5">
                <SourceBadge sourceUrl={news.source_url} sourcePlatform={news.source_platform} showPlatform={false} />
              </dd>
            </div>
            <div>
              <dt className="text-ink-400">抓取时间</dt>
              <dd className="mt-0.5">{crawledText ?? "-"}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-ink-400">来源地址</dt>
              <dd className="mt-0.5">
                <a
                  href={news.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-brand-600 hover:underline break-all"
                >
                  <ExternalLink className="h-3 w-3 shrink-0" />
                  {news.source_url}
                </a>
              </dd>
            </div>
          </dl>
          <p className="mt-2 text-xs text-ink-400">
            资讯为外部公开渠道内容自动聚合；质量分基于来源权威度、时效与完整度计算，仅供参考。
          </p>
        </footer>
      </article>
    </div>
  );
}
