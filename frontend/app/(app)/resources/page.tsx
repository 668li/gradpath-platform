"use client";

// 资源导航中心（/resources，RN-2 2026-10-03）：引流+停留入口，与决策中心互补。
// 北极星：陌生人 30 秒内找到至少 1 个对他有用的站点，并知道为什么收录它。
// 收录纪律：只收实测可达站点 · 用户点名制 · 不搬运任何内容；
// pending 候选带「待站长终审」琥珀徽章外显，终审权在站长。

import { useEffect, useMemo, useState } from "react";
import { Compass, ExternalLink, Hourglass, Search, ShieldCheck, ShieldAlert } from "lucide-react";
import {
  RESOURCE_CATEGORY_LABELS,
  resourcesApi,
  type ResourceLink,
} from "@/lib/api/resources";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { cn } from "@/lib/utils";
const TABS = [
  { id: "", label: "全部" },
  { id: "kaoyan_resources", label: "考研干货" },
  { id: "official", label: "官方入口" },
  { id: "employment", label: "就业求职" },
  { id: "open_source", label: "开源精选" },
  { id: "tool", label: "工具" },
];

function PendingBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 ring-1 ring-amber-200">
      <Hourglass className="h-3 w-3" /> 待站长终审
    </span>
  );
}

function CopyrightBadge({ tier }: { tier: string }) {
  if (tier === "caution") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700">
        <ShieldAlert className="h-3 w-3" /> 版权灰区
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
      <ShieldCheck className="h-3 w-3" /> 原创/开源
    </span>
  );
}

function ResourceCard({ link }: { link: ResourceLink }) {
  let host = link.url;
  try {
    host = new URL(link.url).hostname;
  } catch {
    /* 保持原样 */
  }
  return (
    <a
      href={link.url}
      target="_blank"
      rel="noopener noreferrer nofollow"
      aria-label={`${link.name}，${link.note}`}
      className="group flex flex-col rounded-xl border border-paper-200 bg-white p-4 transition-all hover:border-brand-200 hover:shadow-md"
    >
      <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
        <span className="font-semibold text-ink-800">{link.name}</span>
        <ExternalLink className="ml-auto h-3.5 w-3.5 text-ink-300 group-hover:text-brand-500" />
      </div>
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <span className="text-xs px-1.5 py-0.5 rounded bg-paper-100 text-ink-500">
          {RESOURCE_CATEGORY_LABELS[link.category] ?? link.category}
        </span>
        <CopyrightBadge tier={link.copyright_tier} />
        {link.pending_review && <PendingBadge />}
        {link.recently_added && !link.pending_review && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-brand-50 text-brand-600">新收录</span>
        )}
      </div>
      {/* 为什么收录它：note 一句话定位 */}
      <p className="text-sm leading-relaxed text-ink-600">{link.note}</p>
      {link.risk_note && (
        <p className="mt-1.5 text-xs leading-relaxed text-amber-600">⚠ {link.risk_note}</p>
      )}
      <p className="mt-2 truncate text-xs text-ink-300">{host}</p>
    </a>
  );
}

export default function ResourcesPage() {
  const [links, setLinks] = useState<ResourceLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("");
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  // 300ms 防抖：避免每击键一发请求（对抗审查 P1-5）
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const params: { category?: string; q?: string } = {};
    if (activeTab) params.category = activeTab;
    if (debouncedQuery.trim()) params.q = debouncedQuery.trim();
    resourcesApi
      .list(params)
      .then((data) => {
        if (!cancelled) setLinks(data.items);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeTab, debouncedQuery]);

  const pendingCount = useMemo(() => links.filter((l) => l.pending_review).length, [links]);

  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50">
            <Compass className="h-5 w-5 text-brand-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-ink-800">资源导航</h1>
            <p className="mt-0.5 text-sm text-ink-500">
              考研/求职资源目录——我们替你逐条筛过、测过：个人匠人站 / 开源笔记仓库 / 常用官方入口，每条讲清为什么收
            </p>
          </div>
        </div>
        <p className="mt-3 rounded-lg bg-paper-100 px-3 py-2 text-xs text-ink-500">
          只收实测可达站点 · 用户点名制收录 · 不搬运任何内容——每条链接都经过
          HTTP 实测与内容性质核对，收录理由见卡片说明
        </p>
      </div>

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-300" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜资源名 / 定位关键词，如「408」「数学」「求职」"
            aria-label="搜索资源"
            className="w-full rounded-lg border border-paper-300 bg-white py-2 pl-9 pr-3 text-sm text-ink-700 outline-none focus:border-brand-400"
          />
        </div>
        {!loading && !error && (
          <p className="text-xs text-ink-400">
            {links.length} 条
            {pendingCount > 0 && ` · ${pendingCount} 条待站长终审`}
          </p>
        )}
      </div>

      <div
        className="mb-5 flex gap-2 overflow-x-auto border-b border-paper-300 pb-2"
        role="tablist"
        aria-label="资源分类"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "whitespace-nowrap rounded-t-lg px-4 py-2.5 text-sm font-medium transition-colors",
              activeTab === tab.id
                ? "border-b-2 border-brand-500 bg-white text-brand-600"
                : "text-ink-400 hover:bg-paper-200 hover:text-ink-600",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingState text="正在加载资源目录…" />
      ) : error ? (
        <EmptyState title="目录加载失败" description={error} />
      ) : links.length === 0 ? (
        <EmptyState
          title="没有匹配的资源"
          description="换个关键词试试，或切换分类。目录只收录实测可达的站点，宁缺毋滥。"
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {links.map((link) => (
            <ResourceCard key={link.id} link={link} />
          ))}
        </div>
      )}
    </div>
  );
}
