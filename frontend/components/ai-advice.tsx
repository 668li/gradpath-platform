"use client";

import { useState } from "react";
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Lightbulb,
  Target,
  Star,
  ChevronDown,
  Loader2,
} from "lucide-react";
import { aiApi, type ApiError } from "@/lib/api";
import {
  DESTINATION_TYPE_LABEL,
  DESTINATION_TYPES,
  SALARY_RANGE_OPTIONS,
} from "@/lib/constants";
import { Button, Field, Input, Select } from "@/components/ui/form-controls";
import type { DecisionAdviceResponse, DestinationType } from "@/types";

interface AIAdvicePanelProps {
  // 组件内部管理状态，无外部 props
}

export function AIAdvicePanel(_: AIAdvicePanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DecisionAdviceResponse | null>(null);

  // 表单状态
  const [destinationType, setDestinationType] =
    useState<DestinationType>("employment");
  const [company, setCompany] = useState("");
  const [position, setPosition] = useState("");
  const [city, setCity] = useState("");
  const [expectedSalary, setExpectedSalary] = useState("");

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await aiApi.decisionAdvice({
        destination_type: destinationType,
        company: company.trim() || undefined,
        position: position.trim() || undefined,
        city: city.trim() || undefined,
        expected_salary: expectedSalary || undefined,
      });
      setResult(res);
    } catch (err) {
      const status = (err as ApiError).status;
      if (status === 503) {
        setError("AI 服务未配置，请联系管理员");
      } else if (status === 504) {
        setError("AI 分析超时，请稍后重试");
      } else {
        setError(err instanceof Error ? err.message : "分析失败，请稍后重试");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  return (
    <div className="card overflow-hidden">
      {/* 头部 / 展开切换 */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between gap-3 text-left"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <Sparkles className="h-5 w-5" />
          </span>
          <div>
            <h2 className="font-semibold text-slate-800">AI 决策分析</h2>
            <p className="text-xs text-slate-500">
              输入意向，获取个性化决策建议与市场分析
            </p>
          </div>
        </div>
        <ChevronDown
          className={`h-5 w-5 text-slate-400 transition-transform ${
            expanded ? "rotate-180" : ""
          }`}
        />
      </button>

      {expanded && (
        <div className="mt-4 space-y-4 border-t border-slate-100 pt-4">
          {/* 表单 */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="去向类型" required>
              <Select
                value={destinationType}
                onChange={(e) =>
                  setDestinationType(e.target.value as DestinationType)
                }
              >
                {DESTINATION_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {DESTINATION_TYPE_LABEL[t]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="期望薪资">
              <Select
                value={expectedSalary}
                onChange={(e) => setExpectedSalary(e.target.value)}
              >
                <option value="">不限</option>
                {SALARY_RANGE_OPTIONS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="公司">
              <Input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="如：腾讯"
              />
            </Field>
            <Field label="岗位">
              <Input
                value={position}
                onChange={(e) => setPosition(e.target.value)}
                placeholder="如：后端开发"
              />
            </Field>
            <Field label="城市">
              <Input
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="如：深圳"
              />
            </Field>
          </div>

          <div className="flex items-center gap-2">
            <Button onClick={handleAnalyze} loading={loading} disabled={loading}>
              <Sparkles className="h-4 w-4" /> 开始分析
            </Button>
            {(result || error) && (
              <Button variant="secondary" size="sm" onClick={handleReset}>
                清空结果
              </Button>
            )}
          </div>

          {/* 加载中 */}
          {loading && <LoadingSkeleton />}

          {/* 错误 */}
          {error && !loading && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
              <AlertTriangle className="h-5 w-5 shrink-0 text-red-600" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* 结果 */}
          {result && !loading && <AdviceResult result={result} />}
        </div>
      )}
    </div>
  );
}

/** 加载骨架屏 + 分析中文案 */
function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-brand-600">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="animate-pulse text-sm font-medium">
          AI 正在分析中…
        </span>
      </div>
      <div className="space-y-3">
        <div className="h-16 animate-pulse rounded-lg bg-slate-100" />
        <div className="grid grid-cols-2 gap-3">
          <div className="h-24 animate-pulse rounded-lg bg-slate-100" />
          <div className="h-24 animate-pulse rounded-lg bg-slate-100" />
        </div>
        <div className="h-20 animate-pulse rounded-lg bg-slate-100" />
      </div>
    </div>
  );
}

/** 分析结果展示 */
function AdviceResult({ result }: { result: DecisionAdviceResponse }) {
  const {
    summary,
    pros,
    cons,
    market_analysis,
    alternatives,
    skill_gap,
    confidence,
    advice,
  } = result;
  const safeConfidence = Math.max(0, Math.min(5, Math.round(confidence)));

  return (
    <div className="space-y-4">
      {/* 总览 - 高亮 */}
      <div className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3">
        <div className="flex items-center gap-2 text-brand-700">
          <Sparkles className="h-4 w-4" />
          <span className="text-sm font-semibold">总览</span>
        </div>
        <p className="mt-1 text-sm text-slate-700">{summary}</p>
      </div>

      {/* 信心度星级 */}
      <div className="flex items-center gap-2 text-sm text-slate-600">
        <Target className="h-4 w-4 text-brand-500" />
        <span>信心度</span>
        <span className="flex">
          {Array.from({ length: 5 }).map((_, i) => (
            <Star
              key={i}
              className={`h-4 w-4 ${
                i < safeConfidence
                  ? "fill-amber-400 text-amber-400"
                  : "text-slate-200"
              }`}
            />
          ))}
        </span>
        <span className="text-xs text-slate-400">{safeConfidence}/5</span>
      </div>

      {/* 优势 / 风险 两列对比 */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-green-200 bg-green-50/50 p-3">
          <div className="flex items-center gap-2 text-green-700">
            <CheckCircle2 className="h-4 w-4" />
            <span className="text-sm font-semibold">优势</span>
          </div>
          <ul className="mt-2 space-y-1.5">
            {pros.map((p, i) => (
              <li
                key={i}
                className="flex items-start gap-1.5 text-sm text-slate-600"
              >
                <span className="mt-0.5 text-green-500">•</span>
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50/50 p-3">
          <div className="flex items-center gap-2 text-red-700">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm font-semibold">风险</span>
          </div>
          <ul className="mt-2 space-y-1.5">
            {cons.map((c, i) => (
              <li
                key={i}
                className="flex items-start gap-1.5 text-sm text-slate-600"
              >
                <span className="mt-0.5 text-red-500">•</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* 市场分析 */}
      <div>
        <div className="flex items-center gap-2 text-slate-700">
          <TrendingUp className="h-4 w-4 text-blue-500" />
          <span className="text-sm font-semibold">市场分析</span>
        </div>
        <p className="mt-1 text-sm leading-relaxed text-slate-600">
          {market_analysis}
        </p>
      </div>

      {/* 备选方案 */}
      {alternatives.length > 0 && (
        <div>
          <div className="flex items-center gap-2 text-slate-700">
            <Lightbulb className="h-4 w-4 text-amber-500" />
            <span className="text-sm font-semibold">备选方案</span>
          </div>
          <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {alternatives.map((a, i) => (
              <div
                key={i}
                className="rounded-lg border border-slate-200 bg-slate-50 p-3"
              >
                <p className="text-sm font-medium text-slate-800">{a.option}</p>
                <p className="mt-1 text-xs text-slate-500">{a.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 技能差距 - 橙色标签云 */}
      {skill_gap.length > 0 && (
        <div>
          <div className="flex items-center gap-2 text-slate-700">
            <Target className="h-4 w-4 text-orange-500" />
            <span className="text-sm font-semibold">技能差距</span>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {skill_gap.map((s, i) => (
              <span
                key={i}
                className="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-700"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 建议 - 蓝色背景卡片 */}
      <div className="rounded-lg bg-blue-50 px-4 py-3">
        <div className="flex items-center gap-2 text-blue-700">
          <Lightbulb className="h-4 w-4" />
          <span className="text-sm font-semibold">建议</span>
        </div>
        <p className="mt-1 text-sm leading-relaxed text-slate-700">{advice}</p>
      </div>
    </div>
  );
}
