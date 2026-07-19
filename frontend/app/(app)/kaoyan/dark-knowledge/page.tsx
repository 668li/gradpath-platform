"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpen, Filter, ChevronDown, ChevronUp, Lightbulb, AlertTriangle, CheckCircle } from "lucide-react";
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
  const [items, setItems] = useState<DarkKnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [stage, setStage] = useState("");
  const [total, setTotal] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    gradIntelApi
      .getDarkKnowledge(stage || undefined)
      .then((d: any) => {
        const items = Array.isArray(d) ? d : (d.items || []);
        setItems(items);
        setTotal(items.length);
      })
      .catch(() => toast.push("加载暗知识失败", "error"))
      .finally(() => setLoading(false));
  }, [stage, toast]);

  useEffect(() => { load(); }, [load]);

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
            那些没人告诉你的考研真相 · {total.toLocaleString()} 条
          </p>
        </div>
      </header>

      {/* Stage Filter */}
      <div className="flex gap-2 flex-wrap">
        {STAGES.map((s) => (
          <button
            key={s.value}
            onClick={() => setStage(s.value)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
              stage === s.value
                ? "bg-amber-500 text-white"
                : "bg-paper-200 text-ink-600 hover:bg-paper-300",
            )}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <ListSkeleton count={5} />
      ) : items.length === 0 ? (
        <EmptyState title="暂无暗知识" description="换个阶段筛选试试" />
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
    </div>
  );
}
