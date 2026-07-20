"use client";

import { useCallback, useEffect, useState } from "react";
import {
  GraduationCap,
  RefreshCw,
  ArrowUpDown,
  BookOpen,
  MapPin,
  Star,
  AlertCircle,
  Mail,
  Phone,
  ExternalLink,
  TrendingUp,
  Shield,
  Search,
} from "lucide-react";
import { recommendationApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button, Input, Select, Field } from "@/components/ui/form-controls";
import { ErrorBoundary } from "@/components/error-boundary";
import type {
  SchoolRecommendation,
  AdjustmentRecommendation,
  DarkKnowledgeRecommendation,
} from "@/types";

type Tab = "schools" | "adjustments" | "dark-knowledge";

const TIER_OPTIONS = [
  { value: "", label: "全部层次" },
  { value: "985", label: "985" },
  { value: "211", label: "211" },
  { value: "双一流", label: "双一流" },
  { value: "普通", label: "普通" },
];

const STAGE_OPTIONS = [
  { value: "", label: "全部阶段" },
  { value: "decision", label: "决策阶段" },
  { value: "school_selection", label: "择校阶段" },
  { value: "preparation", label: "备考阶段" },
  { value: "exam", label: "考试阶段" },
  { value: "retest", label: "复试阶段" },
  { value: "transfer", label: "调剂阶段" },
];

function MatchBadge({ score }: { score: number }) {
  const color =
    score >= 70
      ? "bg-green-100 text-green-700 border-green-200"
      : score >= 40
      ? "bg-yellow-100 text-yellow-700 border-yellow-200"
      : "bg-paper-100 text-ink-500 border-paper-200";
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium", color)}>
      匹配度 {score}
    </span>
  );
}

function ImportanceBadge({ importance }: { importance: string }) {
  const color =
    importance === "critical"
      ? "bg-red-100 text-red-700 border-red-200"
      : importance === "high"
      ? "bg-orange-100 text-orange-700 border-orange-200"
      : "bg-blue-100 text-blue-700 border-blue-200";
  const label = importance === "critical" ? "关键" : importance === "high" ? "重要" : "一般";
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium", color)}>
      {label}
    </span>
  );
}

function SchoolCard({ item }: { item: SchoolRecommendation }) {
  return (
    <div className="rounded-xl border border-paper-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50">
            <GraduationCap className="h-5 w-5 text-brand-600" />
          </div>
          <div>
            <h4 className="font-medium text-ink-800">{item.name}</h4>
            <div className="mt-0.5 flex items-center gap-2 text-sm text-ink-400">
              {item.province && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {item.province}
                </span>
              )}
              {item.level && (
                <span className="rounded bg-brand-50 px-1.5 py-0.5 text-xs font-medium text-brand-600">
                  {item.level}
                </span>
              )}
            </div>
          </div>
        </div>
        <MatchBadge score={item.match_score} />
      </div>

      {item.score_line != null && (
        <div className="mt-3 flex items-center gap-1.5 text-sm text-ink-500">
          <TrendingUp className="h-3.5 w-3.5" />
          <span>复试线: <strong className="text-ink-700">{item.score_line}</strong> 分</span>
        </div>
      )}

      {item.adjustment_available && (
        <div className="mt-2 flex items-center gap-1.5 text-sm text-green-600">
          <ArrowUpDown className="h-3.5 w-3.5" />
          <span>有调剂机会</span>
        </div>
      )}

      {item.match_reasons.length > 0 && (
        <div className="mt-3 space-y-1">
          {item.match_reasons.slice(0, 3).map((reason, i) => (
            <div key={`reason-${i}`} className="flex items-start gap-1.5 text-xs text-ink-400">
              <Star className="mt-0.5 h-3 w-3 flex-shrink-0 text-brand-400" />
              <span>{reason}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AdjustmentCard({ item }: { item: AdjustmentRecommendation }) {
  return (
    <div className="rounded-xl border border-paper-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-ink-800">{item.university_name}</h4>
          <p className="mt-0.5 text-sm text-ink-500">{item.department} · {item.major_name}</p>
        </div>
        <MatchBadge score={item.match_score} />
      </div>

      <div className="mt-3 flex flex-wrap gap-2 text-sm">
        {item.adjustment_quota != null && (
          <span className="rounded bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
            名额: {item.adjustment_quota}
          </span>
        )}
        {item.deadline && (
          <span className="rounded bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700">
            截止: {item.deadline}
          </span>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-3 text-sm text-ink-500">
        {item.contact_email && (
          <span className="flex items-center gap-1">
            <Mail className="h-3.5 w-3.5" />
            {item.contact_email}
          </span>
        )}
        {item.contact_phone && (
          <span className="flex items-center gap-1">
            <Phone className="h-3.5 w-3.5" />
            {item.contact_phone}
          </span>
        )}
      </div>

      {item.source_url && (
        <a
          href={item.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-flex items-center gap-1 text-sm text-brand-600 hover:text-brand-700"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          查看来源
        </a>
      )}

      {item.match_reasons.length > 0 && (
        <div className="mt-3 space-y-1">
          {item.match_reasons.slice(0, 3).map((reason, i) => (
            <div key={`reason-${i}`} className="flex items-start gap-1.5 text-xs text-ink-400">
              <Star className="mt-0.5 h-3 w-3 flex-shrink-0 text-brand-400" />
              <span>{reason}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DarkKnowledgeCard({ item }: { item: DarkKnowledgeRecommendation }) {
  return (
    <div className="rounded-xl border border-paper-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-50">
            <BookOpen className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h4 className="font-medium text-ink-800">{item.title}</h4>
            <p className="text-sm text-ink-400">{item.category}</p>
          </div>
        </div>
        <ImportanceBadge importance={item.importance} />
      </div>

      <p className="mt-3 text-sm text-ink-600 leading-relaxed">{item.content}</p>

      {item.common_misconception && (
        <div className="mt-3 rounded-lg bg-red-50 p-3">
          <div className="flex items-center gap-1.5 text-sm font-medium text-red-700">
            <AlertCircle className="h-4 w-4" />
            常见误区
          </div>
          <p className="mt-1 text-sm text-red-600">{item.common_misconception}</p>
        </div>
      )}

      {item.actionable_advice && (
        <div className="mt-3 rounded-lg bg-green-50 p-3">
          <div className="flex items-center gap-1.5 text-sm font-medium text-green-700">
            <Shield className="h-4 w-4" />
            行动建议
          </div>
          <p className="mt-1 text-sm text-green-600">{item.actionable_advice}</p>
        </div>
      )}
    </div>
  );
}

function SchoolTab() {
  const [score, setScore] = useState("");
  const [tier, setTier] = useState("");
  const [region, setRegion] = useState("");
  const [major, setMajor] = useState("");
  const [items, setItems] = useState<SchoolRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSchools = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await recommendationApi.recommendSchools({
        target_score: score ? Number(score) : undefined,
        target_tier: tier || undefined,
        target_region: region || undefined,
        target_major: major || undefined,
        top_n: 15,
      });
      setItems(res.items);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }, [score, tier, region, major]);

  useEffect(() => {
    fetchSchools();
  }, []);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-paper-200 bg-white p-4 shadow-sm">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Field label="目标分数">
            <Input
              type="number"
              placeholder="如 370"
              value={score}
              onChange={(e) => setScore(e.target.value)}
            />
          </Field>
          <Field label="目标层次">
            <Select value={tier} onChange={(e) => setTier(e.target.value)}>
              {TIER_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </Select>
          </Field>
          <Field label="目标地区">
            <Input
              placeholder="如 北京"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
            />
          </Field>
          <Field label="目标专业">
            <Input
              placeholder="如 计算机"
              value={major}
              onChange={(e) => setMajor(e.target.value)}
            />
          </Field>
        </div>
        <div className="mt-3 flex justify-end">
          <Button onClick={fetchSchools} disabled={loading}>
            <Search className="mr-1.5 h-4 w-4" />
            {loading ? "搜索中…" : "搜索推荐"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          {error}
        </div>
      )}

      {loading ? (
        <LoadingState text="正在匹配推荐院校…" />
      ) : items.length === 0 ? (
        <EmptyState title="暂无匹配结果" description="请调整筛选条件后重试" />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {items.map((item, i) => (
            <SchoolCard key={`${item.name}-${i}`} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function AdjustmentTab() {
  const [score, setScore] = useState("");
  const [major, setMajor] = useState("");
  const [region, setRegion] = useState("");
  const [items, setItems] = useState<AdjustmentRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAdjustments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await recommendationApi.recommendAdjustments({
        target_score: score ? Number(score) : undefined,
        target_major: major || undefined,
        target_region: region || undefined,
        top_n: 15,
      });
      setItems(res.items);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }, [score, major, region]);

  useEffect(() => {
    fetchAdjustments();
  }, []);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-paper-200 bg-white p-4 shadow-sm">
        <div className="grid grid-cols-3 gap-3">
          <Field label="目标分数">
            <Input
              type="number"
              placeholder="如 350"
              value={score}
              onChange={(e) => setScore(e.target.value)}
            />
          </Field>
          <Field label="目标专业">
            <Input
              placeholder="如 管理学"
              value={major}
              onChange={(e) => setMajor(e.target.value)}
            />
          </Field>
          <Field label="目标地区">
            <Input
              placeholder="如 上海"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
            />
          </Field>
        </div>
        <div className="mt-3 flex justify-end">
          <Button onClick={fetchAdjustments} disabled={loading}>
            <ArrowUpDown className="mr-1.5 h-4 w-4" />
            {loading ? "搜索中…" : "搜索调剂"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          {error}
        </div>
      )}

      {loading ? (
        <LoadingState text="正在匹配调剂机会…" />
      ) : items.length === 0 ? (
        <EmptyState title="暂无调剂推荐" description="请调整筛选条件后重试" />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {items.map((item, i) => (
            <AdjustmentCard key={`${item.university_name}-${item.major_name}-${i}`} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function DarkKnowledgeTab() {
  const [stage, setStage] = useState("");
  const [items, setItems] = useState<DarkKnowledgeRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchKnowledge = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await recommendationApi.recommendDarkKnowledge({
        stage: stage || undefined,
        top_n: 15,
      });
      setItems(res.items);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }, [stage]);

  useEffect(() => {
    fetchKnowledge();
  }, []);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-paper-200 bg-white p-4 shadow-sm">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Field label="备考阶段">
            <Select value={stage} onChange={(e) => setStage(e.target.value)}>
              {STAGE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="mt-3 flex justify-end">
          <Button onClick={fetchKnowledge} disabled={loading}>
            <BookOpen className="mr-1.5 h-4 w-4" />
            {loading ? "加载中…" : "查看推荐"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          {error}
        </div>
      )}

      {loading ? (
        <LoadingState text="正在加载暗知识…" />
      ) : items.length === 0 ? (
        <EmptyState title="暂无暗知识" description="请尝试其他阶段" />
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <DarkKnowledgeCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

export function RecommendPanel() {
  const [tab, setTab] = useState<Tab>("schools");

  const tabs: { key: Tab; label: string; icon: React.ElementType }[] = [
    { key: "schools", label: "院校推荐", icon: GraduationCap },
    { key: "adjustments", label: "调剂推荐", icon: ArrowUpDown },
    { key: "dark-knowledge", label: "暗知识", icon: BookOpen },
  ];

  return (
    <ErrorBoundary>
      <div className="space-y-4">
        <div className="flex items-center gap-1 rounded-xl border border-paper-200 bg-white p-1 shadow-sm">
          {tabs.map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={cn(
                  "flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  tab === t.key
                    ? "bg-brand-50 text-brand-700"
                    : "text-ink-500 hover:text-ink-700 hover:bg-paper-50",
                )}
              >
                <Icon className="h-4 w-4" />
                {t.label}
              </button>
            );
          })}
        </div>

        {tab === "schools" && <SchoolTab />}
        {tab === "adjustments" && <AdjustmentTab />}
        {tab === "dark-knowledge" && <DarkKnowledgeTab />}
      </div>
    </ErrorBoundary>
  );
}
