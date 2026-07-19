"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpen, Search, ChevronDown, ChevronUp, Lightbulb, AlertTriangle, CheckCircle } from "lucide-react";
import { gradIntelApi } from "@/lib/api";
import { EmptyState } from "@/components/ui/empty";
import { ListSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

const STAGES = [
  { value: "", label: "全部阶段" },
  { value: "information", label: "信息收集" },
  { value: "preparation", label: "备考准备" },
  { value: "exam", label: "考试阶段" },
  { value: "adjustment", label: "调剂阶段" },
  { value: "career", label: "职业发展" },
];

const IMPORTANCE_MAP: Record<string, { label: string; color: string; icon: typeof AlertTriangle }> = {
  critical: { label: "关键", color: "bg-red-100 text-red-700", icon: AlertTriangle },
  high: { label: "重要", color: "bg-orange-100 text-orange-700", icon: AlertTriangle },
  medium: { label: "一般", color: "bg-blue-100 text-blue-700", icon: Lightbulb },
  low: { label: "了解", color: "bg-gray-100 text-gray-600", icon: CheckCircle },
};

interface DarkKnowledgeItem {
  id: string;
  title: string;
  content: string;
  stage: string;
  category: string;
  importance: string;
  tags: string[];
  common_misconception?: string;
  actionable_advice?: string;
  verification_method?: string;
}

export default function KaoyanDarkKnowledgePage() {
  const toast = useToast();
  const [allItems, setAllItems] = useState<DarkKnowledgeItem[]>([]);
  const [items, setItems] = useState<DarkKnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [stage, setStage] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const PAGE_SIZE = 20;

  const load = useCallback(() => {
    setLoading(true);
    setPage(1);
    gradIntelApi
      .getDarkKnowledge(stage || undefined)
      .then((d: any) => {
        const raw = Array.isArray(d) ? d : (d.items || []);
        setAllItems(raw);
        setTotal(raw.length);
        setItems(raw.slice(0, PAGE_SIZE));
      })
      .catch(() => toast.push("加载暗知识失败", "error"))
      .finally(() => setLoading(false));
  }, [stage, toast]);

  // Client-side search + pagination
  useEffect(() => {
    const q = search.toLowerCase();
    const filtered = q
      ? allItems.filter(
          (item) =>
            item.title.toLowerCase().includes(q) ||
            item.content.toLowerCase().includes(q) ||
            item.tags?.some((t) => t.toLowerCase().includes(q)),
        )
      : allItems;
    setTotal(filtered.length);
    setPage(1);
    setItems(filtered.slice(0, PAGE_SIZE));
  }, [search, allItems]);

  const goToPage = (p: number) => {
    const q = search.toLowerCase();
    const filtered = q
      ? allItems.filter(
          (item) =>
            item.title.toLowerCase().includes(q) ||
            item.content.toLowerCase().includes(q) ||
            item.tags?.some((t) => t.toLowerCase().includes(q)),
        )
      : allItems;
    setPage(p);
    setItems(filtered.slice((p - 1) * PAGE_SIZE, p * PAGE_SIZE));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  useEffect(() => { load(); }, [load]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/15 text-amber-500">
          <BookOpen className="h-6 w-6" strokeWidth={2} />
        </div>
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-800">
            考研暗知识
          </h1>
          <p className="text-sm text-ink-500">
            那些没人告诉你的考研真相 · 共 {total.toLocaleString()} 条
            {search && ` · 搜索"${search}"`}
          </p>
        </div>
      </header>

      {/* Search + Stage Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索暗知识标题、内容、标签..."
            className="w-full rounded-lg border border-paper-300 bg-white pl-9 pr-3 py-2 text-sm text-ink-800 placeholder:text-ink-400 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-100"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {STAGES.map((s) => (
            <button
              key={s.value}
              onClick={() => setStage(s.value)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap",
                stage === s.value
                  ? "bg-amber-500 text-white"
                  : "bg-paper-200 text-ink-600 hover:bg-paper-300",
              )}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <ListSkeleton count={5} />
      ) : items.length === 0 ? (
        <EmptyState
          title={search ? `没有匹配"${search}"的暗知识` : "暂无暗知识"}
          description={search ? "换个关键词试试" : "换个阶段筛选试试"}
        />
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const imp = IMPORTANCE_MAP[item.importance] || IMPORTANCE_MAP.medium;
            const ImpIcon = imp.icon;
            const expanded = expandedId === item.id;
            return (
              <div
                key={item.id}
                className="rounded-xl border border-paper-200 bg-white overflow-hidden hover:shadow-sm transition-shadow"
              >
                <button
                  onClick={() => setExpandedId(expanded ? null : item.id)}
                  className="w-full text-left p-4 flex items-start gap-3"
                >
                  <span className={cn("mt-0.5 rounded px-2 py-0.5 text-xs font-medium flex items-center gap-1", imp.color)}>
                    <ImpIcon className="h-3 w-3" />
                    {imp.label}
                  </span>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-ink-800">{item.title}</h3>
                    <p className="text-sm text-ink-500 mt-0.5 line-clamp-2">{item.content}</p>
                  </div>
                  {expanded ? <ChevronUp className="h-4 w-4 text-ink-400 shrink-0" /> : <ChevronDown className="h-4 w-4 text-ink-400 shrink-0" />}
                </button>
                {expanded && (
                  <div className="px-4 pb-4 border-t border-paper-100 pt-3 space-y-3 text-sm">
                    <div className="text-ink-700 whitespace-pre-wrap">{item.content}</div>
                    {item.common_misconception && (
                      <div className="rounded-lg bg-red-50 p-3">
                        <p className="font-medium text-red-700 mb-1">常见误区</p>
                        <p className="text-red-600">{item.common_misconception}</p>
                      </div>
                    )}
                    {item.actionable_advice && (
                      <div className="rounded-lg bg-green-50 p-3">
                        <p className="font-medium text-green-700 mb-1">行动建议</p>
                        <p className="text-green-600">{item.actionable_advice}</p>
                      </div>
                    )}
                    {item.verification_method && (
                      <div className="rounded-lg bg-blue-50 p-3">
                        <p className="font-medium text-blue-700 mb-1">验证方法</p>
                        <p className="text-blue-600">{item.verification_method}</p>
                      </div>
                    )}
                    {item.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {item.tags.map((t: string) => (
                          <span key={t} className="rounded bg-paper-100 px-2 py-0.5 text-xs text-ink-500">{t}</span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => goToPage(page - 1)}
            disabled={page <= 1}
            className="px-3 py-1.5 rounded-lg text-sm border border-paper-300 disabled:opacity-30 hover:bg-paper-100"
          >
            上一页
          </button>
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            const start = Math.max(1, Math.min(page - 2, totalPages - 4));
            const p = start + i;
            if (p > totalPages) return null;
            return (
              <button
                key={p}
                onClick={() => goToPage(p)}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                  p === page ? "bg-amber-500 text-white" : "border border-paper-300 hover:bg-paper-100",
                )}
              >
                {p}
              </button>
            );
          })}
          <span className="text-sm text-ink-500 mx-2">
            {page}/{totalPages} 页
          </span>
          <button
            onClick={() => goToPage(page + 1)}
            disabled={page >= totalPages}
            className="px-3 py-1.5 rounded-lg text-sm border border-paper-300 disabled:opacity-30 hover:bg-paper-100"
          >
            下一页
          </button>
        </div>
      )}
    </div>
  );
}
