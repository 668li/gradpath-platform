"use client";

import { memo, useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  Lightbulb,
  Eye,
  XCircle,
  ChevronRight,
  BookOpen,
  Compass,
  Target,
  Brain,
  Send,
} from "lucide-react";
import { gradIntelApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Badge } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { ErrorBoundary } from "@/components/error-boundary";
import type { DarkKnowledgeResponse, DarkKnowledgeStage } from "@/types";

const IMPORTANCE_COLORS: Record<string, "red" | "amber" | "slate"> = {
  critical: "red",
  high: "amber",
  medium: "slate",
};

const STAGE_INFO: Record<string, { name: string; icon: typeof Compass; desc: string }> = {
  decision: { name: "决策期", icon: Compass, desc: "要不要考研？考什么？" },
  school_selection: { name: "选校期", icon: Target, desc: "选哪些学校和专业？" },
  preparation: { name: "备考期", icon: Brain, desc: "怎么高效复习？" },
  exam: { name: "初试期", icon: BookOpen, desc: "报名、考试、出分" },
  retest: { name: "复试期", icon: Send, desc: "复试、调剂、录取" },
};

function DarkKnowledgeCard({ item }: { item: DarkKnowledgeResponse }) {
  const [expanded, setExpanded] = useState(false);
  const importanceColor = IMPORTANCE_COLORS[item.importance] || "slate";
  const importanceLabel = item.importance === "critical" ? "致命" : item.importance === "high" ? "重要" : "了解";

  return (
    <div className="rounded-xl border border-paper-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Badge color={importanceColor}>{importanceLabel}</Badge>
            <span className="text-xs text-ink-400">{item.category}</span>
          </div>
          <h3 className="text-base font-semibold text-ink-800">{item.title}</h3>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
          aria-label={expanded ? "收起详情" : "展开详情"}
          className="flex-shrink-0 rounded-lg p-1 text-ink-400 hover:bg-paper-100 hover:text-ink-600 transition-colors"
        >
          <ChevronRight className={cn("h-5 w-5 transition-transform", expanded && "rotate-90")} />
        </button>
      </div>

      <p className="text-sm text-ink-600 leading-relaxed">{item.content}</p>

      {expanded && (
        <div className="mt-3 space-y-3 border-t border-paper-100 pt-3">
          {item.common_misconception && (
            <div className="rounded-lg bg-red-50 border border-red-100 p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <XCircle className="h-4 w-4 text-red-500" />
                <span className="text-sm font-semibold text-red-700">常见误区</span>
              </div>
              <p className="text-sm text-red-600">{item.common_misconception}</p>
            </div>
          )}
          {item.actionable_advice && (
            <div className="rounded-lg bg-brand-50 border border-brand-100 p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <Lightbulb className="h-4 w-4 text-brand-600" />
                <span className="text-sm font-semibold text-brand-700">行动建议</span>
              </div>
              <p className="text-sm text-brand-600">{item.actionable_advice}</p>
            </div>
          )}
          {item.verification_method && (
            <div className="rounded-lg bg-blue-50 border border-blue-100 p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <Eye className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-semibold text-blue-700">验证方法</span>
              </div>
              <p className="text-sm text-blue-600">{item.verification_method}</p>
            </div>
          )}
        </div>
      )}

      {item.tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {item.tags.map((t, i) => (
            <span key={`${t}-${i}`} className="text-xs text-ink-400">#{t}</span>
          ))}
        </div>
      )}
    </div>
  );
}

export const DarkKnowledge = memo(function DarkKnowledge() {
  const toast = useToast();
  const [stages, setStages] = useState<DarkKnowledgeStage[]>([]);
  const [activeStage, setActiveStage] = useState<string>("");
  const [items, setItems] = useState<DarkKnowledgeResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async (stage?: string) => {
    setLoading(true);
    try {
      const [stageList, itemList] = await Promise.all([
        gradIntelApi.getDarkKnowledgeStages(),
        gradIntelApi.getDarkKnowledge(stage ? { stage } : undefined),
      ]);
      setStages(stageList);
      setItems(itemList);
      if (!activeStage && stageList.length > 0) {
        setActiveStage(stageList[0].stage);
      }
    } catch {
      toast.push("加载暗知识失败", "error");
    } finally {
      setLoading(false);
    }
  }, [activeStage, toast]);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleStageChange = async (stage: string) => {
    setActiveStage(stage);
    setLoading(true);
    try {
      const itemList = await gradIntelApi.getDarkKnowledge({ stage });
      setItems(itemList);
    } catch {
      toast.push("加载失败", "error");
    } finally {
      setLoading(false);
    }
  };

  if (loading && stages.length === 0) {
    return <LoadingState text="加载暗知识地图…" />;
  }

  return (
    <ErrorBoundary>
      <div className="space-y-4">
        <div className="rounded-xl border border-paper-200 bg-gradient-to-br from-ink-50 to-white p-4">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-ink-700 text-paper-50">
              <BookOpen className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-ink-800">考研暗知识地图</h2>
              <p className="text-sm text-ink-500 mt-0.5">
                那些「没人告诉你但决定成败」的知识。每条都附常见误区、行动建议和验证方法。
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2" role="tablist" aria-label="考研阶段筛选">
          {stages.map((s) => {
            const info = STAGE_INFO[s.stage] || { name: s.stage, icon: BookOpen, desc: "" };
            const Icon = info.icon;
            return (
              <button
                key={s.stage}
                role="tab"
                aria-selected={activeStage === s.stage}
                aria-label={`${info.name}，${s.count}条暗知识`}
                onClick={() => handleStageChange(s.stage)}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-all",
                  activeStage === s.stage
                    ? "bg-brand-600 text-white shadow-brand-sm"
                    : "bg-white text-ink-600 border border-paper-200 hover:border-brand-300",
                )}
              >
                <Icon className="h-4 w-4" strokeWidth={2} />
                {info.name}
                <span className={cn(
                  "ml-0.5 rounded-full px-1.5 py-0.5 text-xs",
                  activeStage === s.stage ? "bg-white/20" : "bg-ink-100",
                )}>
                  {s.count}
                </span>
              </button>
            );
          })}
        </div>

        {loading ? (
          <LoadingState />
        ) : items.length === 0 ? (
          <EmptyState title="该阶段暂无暗知识" description="试试其他阶段" />
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <DarkKnowledgeCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
});
