"use client";

import { memo, useCallback, useEffect, useState } from "react";
import {
  Search,
  Save,
  Trash2,
  Shield,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ChevronRight,
  Brain,
  Bookmark,
} from "lucide-react";
import { gradIntelApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button, Input, Field, Badge } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { ErrorBoundary } from "@/components/error-boundary";
import type { AIIntelResult, IntelResponse } from "@/types";

const DISCRIM_COLORS: Record<string, { label: string; color: "green" | "amber" | "red" | "slate"; icon: typeof CheckCircle2 }> = {
  none: { label: "不卡", color: "green", icon: CheckCircle2 },
  mild: { label: "轻微", color: "amber", icon: AlertTriangle },
  moderate: { label: "中等", color: "amber", icon: AlertTriangle },
  severe: { label: "严重", color: "red", icon: XCircle },
  unknown: { label: "待查", color: "slate", icon: HelpCircle },
};

const PROTECTION_COLORS: Record<string, { label: string; color: "green" | "amber" | "red" | "slate"; icon: typeof Shield }> = {
  yes: { label: "保护一志愿", color: "green", icon: Shield },
  no: { label: "不保护", color: "red", icon: AlertTriangle },
  partial: { label: "部分保护", color: "amber", icon: Shield },
  unknown: { label: "待查", color: "slate", icon: HelpCircle },
};

const SUPPRESSION_COLORS: Record<string, { label: string; color: "green" | "amber" | "red" | "slate" }> = {
  none: { label: "不压分", color: "green" },
  mild: { label: "轻微压分", color: "amber" },
  moderate: { label: "有压分", color: "amber" },
  severe: { label: "严重压分", color: "red" },
  unknown: { label: "待查", color: "slate" },
};

const TRANSFER_COLORS: Record<string, { label: string; color: "green" | "amber" | "red" | "slate" }> = {
  friendly: { label: "调剂友好", color: "green" },
  neutral: { label: "一般", color: "amber" },
  unfriendly: { label: "不友好", color: "red" },
  unknown: { label: "待查", color: "slate" },
};

function IntelBadge({
  label,
  config,
}: {
  label: string;
  config: { label: string; color: "green" | "amber" | "red" | "slate"; icon: typeof CheckCircle2 };
}) {
  const Icon = config.icon;
  return (
    <div className={cn(
      "rounded-lg border p-2.5 text-center",
      config.color === "green" && "bg-brand-50 border-brand-200",
      config.color === "amber" && "bg-amber-50 border-amber-200",
      config.color === "red" && "bg-red-50 border-red-200",
      config.color === "slate" && "bg-paper-50 border-paper-200",
    )}>
      <Icon className={cn(
        "mx-auto mb-1 h-4 w-4",
        config.color === "green" && "text-brand-600",
        config.color === "amber" && "text-amber-600",
        config.color === "red" && "text-red-600",
        config.color === "slate" && "text-ink-400",
      )} />
      <div className="text-xs text-ink-400">{label}</div>
      <div className={cn(
        "text-sm font-semibold",
        config.color === "green" && "text-brand-700",
        config.color === "amber" && "text-amber-700",
        config.color === "red" && "text-red-700",
        config.color === "slate" && "text-ink-500",
      )}>
        {config.label}
      </div>
    </div>
  );
}

function DataCell({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-lg bg-paper-50 p-2.5">
      <div className="text-xs text-ink-400">{label}</div>
      <div className="text-sm font-semibold text-ink-700">
        {value || <span className="text-ink-300 font-normal">—</span>}
      </div>
    </div>
  );
}

function IntelResultCard({
  result,
  onSave,
  saving,
}: {
  result: AIIntelResult;
  onSave: () => void;
  saving: boolean;
}) {
  return (
    <div className="rounded-xl border border-brand-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-ink-900">
            {result.school_name} · {result.major_name}
          </h3>
          {result.school_tier && (
            <Badge color="purple">{result.school_tier}</Badge>
          )}
        </div>
        <Button size="sm" variant="secondary" onClick={onSave} loading={saving}>
          <Save className="h-3.5 w-3.5" />
          保存
        </Button>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <IntelBadge
          label="卡学历"
          config={DISCRIM_COLORS[result.background_discrimination] || DISCRIM_COLORS.unknown}
        />
        <IntelBadge
          label="保护一志愿"
          config={PROTECTION_COLORS[result.first_choice_protection] || PROTECTION_COLORS.unknown}
        />
        <IntelBadge
          label="压分情况"
          config={{ ...SUPPRESSION_COLORS[result.score_suppression] || SUPPRESSION_COLORS.unknown, icon: AlertTriangle }}
        />
        <IntelBadge
          label="调剂友好度"
          config={{ ...TRANSFER_COLORS[result.transfer_friendly] || TRANSFER_COLORS.unknown, icon: ChevronRight }}
        />
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <DataCell label="报录比" value={result.admission_ratio} />
        <DataCell label="推免占比" value={result.push_ratio} />
        <DataCell label="实际招生" value={result.actual_quota != null ? `${result.actual_quota} 人` : null} />
        <DataCell label="分数线" value={result.score_line != null ? `${result.score_line} 分` : null} />
        <DataCell label="复试权重" value={result.retest_weight} />
        <DataCell label="复试形式" value={result.retest_format} />
      </div>

      {result.insider_notes && (
        <div className="mb-4 rounded-lg bg-amber-50 border border-amber-200 p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <span className="text-sm font-semibold text-amber-800">内部消息</span>
          </div>
          <p className="text-sm text-amber-700 whitespace-pre-line">{result.insider_notes}</p>
        </div>
      )}

      {result.ai_summary && (
        <div className="rounded-lg bg-brand-50 border border-brand-200 p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <Brain className="h-4 w-4 text-brand-600" />
            <span className="text-sm font-semibold text-brand-800">AI 分析总结</span>
          </div>
          <p className="text-sm text-brand-700 whitespace-pre-line">{result.ai_summary}</p>
        </div>
      )}

      {result.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {result.tags.map((tag, i) => (
            <Badge key={`${tag}-${i}`} color="slate">{tag}</Badge>
          ))}
        </div>
      )}

      {result.data_sources.length > 0 && (
        <div className="mt-3 text-xs text-ink-400">
          数据来源：{result.data_sources.join("、")}
        </div>
      )}
    </div>
  );
}

function SavedIntelCard({
  intel,
  onDelete,
}: {
  intel: IntelResponse;
  onDelete: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const discrim = DISCRIM_COLORS[intel.background_discrimination] || DISCRIM_COLORS.unknown;
  const protect = PROTECTION_COLORS[intel.first_choice_protection] || PROTECTION_COLORS.unknown;

  return (
    <div className="rounded-lg border border-paper-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-ink-800 truncate">
            {intel.school_name}
          </p>
          <p className="text-sm text-ink-500 truncate">{intel.major_name}</p>
        </div>
        <button
          onClick={() => onDelete(intel.id)}
          aria-label={`删除 ${intel.school_name} 情报`}
          className="flex-shrink-0 rounded p-1 text-ink-300 hover:bg-red-50 hover:text-red-500 transition-colors"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Badge color={discrim.color}>卡学历: {discrim.label}</Badge>
        <Badge color={protect.color}>一志愿: {protect.label}</Badge>
      </div>
      {expanded && (
        <div className="mt-3 space-y-2 border-t border-paper-100 pt-3 text-sm">
          {intel.score_line != null && <div className="text-ink-600">分数线: {intel.score_line}</div>}
          {intel.admission_ratio && <div className="text-ink-600">报录比: {intel.admission_ratio}</div>}
          {intel.ai_summary && <div className="text-ink-500 text-xs mt-2">{intel.ai_summary}</div>}
        </div>
      )}
      <button
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        className="mt-2 text-xs text-brand-600 hover:text-brand-700 font-medium"
      >
        {expanded ? "收起" : "展开详情"}
      </button>
    </div>
  );
}

export const SchoolIntel = memo(function SchoolIntel() {
  const toast = useToast();
  const [schoolName, setSchoolName] = useState("");
  const [majorName, setMajorName] = useState("");
  const [querying, setQuerying] = useState(false);
  const [result, setResult] = useState<AIIntelResult | null>(null);
  const [savedList, setSavedList] = useState<IntelResponse[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadList = useCallback(async () => {
    setLoadingList(true);
    setListError(false);
    try {
      const list = await gradIntelApi.listIntel();
      setSavedList(list);
    } catch {
      try {
        const list = await gradIntelApi.listPublicIntel();
        setSavedList(list);
      } catch {
        setListError(true);
      }
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    loadList();
  }, [loadList]);

  const handleQuery = async () => {
    if (!schoolName.trim() || !majorName.trim()) {
      toast.push("请输入院校名称和专业名称", "info");
      return;
    }
    setQuerying(true);
    setResult(null);
    try {
      const res = await gradIntelApi.queryIntel({
        school_name: schoolName.trim(),
        major_name: majorName.trim(),
      });
      setResult(res);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "查询失败";
      toast.push(msg, "error");
    } finally {
      setQuerying(false);
    }
  };

  const handleSave = async () => {
    if (!result) return;
    setSaving(true);
    try {
      await gradIntelApi.saveIntel({
        ...result,
        is_ai_generated: true,
      });
      toast.push("情报已保存", "success");
      loadList();
    } catch {
      toast.push("保存失败", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await gradIntelApi.deleteIntel(id);
      toast.push("已删除", "success");
      loadList();
    } catch {
      toast.push("删除失败", "error");
    }
  };

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <div className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
          <h2 className="mb-1 text-base font-semibold text-ink-800">AI 院校情报查询</h2>
          <p className="mb-4 text-sm text-ink-400">
            输入目标院校和专业，AI 帮你分析卡学历、保护一志愿、压分、调剂等关键情报。
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="w-full sm:flex-1">
              <Field label="院校名称" required>
                <Input
                  value={schoolName}
                  onChange={(e) => setSchoolName(e.target.value)}
                  placeholder="如：浙江大学"
                  onKeyDown={(e) => e.key === "Enter" && handleQuery()}
                />
              </Field>
            </div>
            <div className="w-full sm:flex-1">
              <Field label="专业名称" required>
                <Input
                  value={majorName}
                  onChange={(e) => setMajorName(e.target.value)}
                  placeholder="如：计算机科学与技术"
                  onKeyDown={(e) => e.key === "Enter" && handleQuery()}
                />
              </Field>
            </div>
            <Button onClick={handleQuery} loading={querying} className="sm:mb-[2px]">
              <Search className="h-4 w-4" />
              情报查询
            </Button>
          </div>
        </div>

        {querying && (
          <div className="rounded-xl border border-paper-200 bg-white p-8">
            <LoadingState text="AI 正在收集院校情报…" />
          </div>
        )}

        {result && !querying && (
          <IntelResultCard result={result} onSave={handleSave} saving={saving} />
        )}

        <div>
          <div className="mb-3 flex items-center gap-2">
            <Bookmark className="h-4 w-4 text-ink-400" />
            <h2 className="text-sm font-semibold text-ink-700">已保存的情报</h2>
            <span className="text-xs text-ink-400">({savedList.length})</span>
          </div>
          {loadingList ? (
            <LoadingState />
          ) : listError ? (
            <EmptyState
              title="加载失败"
              description="无法加载已保存的情报"
              action={
                <Button size="sm" variant="secondary" onClick={loadList}>
                  重试
                </Button>
              }
            />
          ) : savedList.length === 0 ? (
            <EmptyState title="还没有保存的情报" description="查询后点击保存即可在此查看" />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {savedList.map((intel) => (
                <SavedIntelCard key={intel.id} intel={intel} onDelete={handleDelete} />
              ))}
            </div>
          )}
        </div>
      </div>
    </ErrorBoundary>
  );
});
