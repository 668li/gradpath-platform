"use client";

import { useState } from "react";
import {
  Shield,
  GitBranch,
  Scale,
  Check,
  AlertTriangle,
  Clock,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { pathConflictApi, useApi, useInvalidate } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { Badge, Button, Textarea } from "@/components/ui/form-controls";
import { Modal } from "@/components/ui/modal";
import { cn } from "@/lib/utils";
import type {
  PathConflictDetection,
  PathConflictResolution,
  PathConflictOption,
} from "@/types/decision-copilot";

// 选项图标映射：0=坚持现状(Shield), 1=转向推荐(GitBranch), 2=折中方案(Scale)
const OPTION_ICONS = [Shield, GitBranch, Scale];
const OPTION_COLORS = [
  { bg: "bg-blue-50", text: "text-blue-600", ring: "ring-blue-200" },
  { bg: "bg-purple-50", text: "text-purple-600", ring: "ring-purple-200" },
  { bg: "bg-amber-50", text: "text-amber-600", ring: "ring-amber-200" },
];

const RISK_BADGE: Record<string, { label: string; color: "green" | "amber" | "red" }> = {
  low: { label: "低风险", color: "green" },
  medium: { label: "中风险", color: "amber" },
  high: { label: "高风险", color: "red" },
};

interface PathConflictCardProps {
  /** 已检测到的冲突数据（由父组件通过 useApi 拉取后传入） */
  detection: PathConflictDetection;
  /** 关闭卡片回调（用户主动忽略或处理完成后调用） */
  onClose?: () => void;
  /** 调解完成回调（用户提交选择并收到行动计划后触发） */
  onResolved?: (resolution: PathConflictResolution) => void;
}

/**
 * 路径冲突调解卡片 — 展示测评与现状的冲突，提供 3 条路径让用户自主选择。
 *
 * 流程：
 * 1. 显示冲突摘要（测评结果 vs 当前现状）
 * 2. 3 张选项卡片并排展示
 * 3. 选中后弹出 reasoning 输入 modal
 * 4. 提交后显示系统生成的行动计划
 */
export function PathConflictCard({ detection, onClose, onResolved }: PathConflictCardProps) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [reasoning, setReasoning] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [resolution, setResolution] = useState<PathConflictResolution | null>(null);
  const toast = useToast();
  const invalidate = useInvalidate();

  // 已调解完成，展示行动计划
  if (resolution) {
    return (
      <ActionPlanView
        resolution={resolution}
        onReset={() => {
          setResolution(null);
          setSelectedId(null);
          setReasoning("");
          invalidate("/api/path-conflict/detect");
          onResolved?.(resolution);
        }}
      />
    );
  }

  const handleSubmit = async () => {
    if (selectedId === null || !detection.conflict_id) return;
    setSubmitting(true);
    try {
      const result = await pathConflictApi.resolve({
        conflict_id: detection.conflict_id,
        selected_option: selectedId,
        reasoning: reasoning.trim(),
      });
      setResolution(result);
      setModalOpen(false);
      toast.success("已生成你的专属行动计划");
    } catch (err) {
      const message = err instanceof Error ? err.message : "提交失败，请稍后重试";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50/50 to-white p-6 shadow-sm">
      {/* 头部 */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-amber-600">
            <AlertTriangle className="h-5 w-5" />
          </span>
          <div>
            <h2 className="text-lg font-semibold text-ink-800">路径冲突调解</h2>
            <p className="mt-0.5 text-sm text-ink-500">{detection.message}</p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-ink-300 hover:text-ink-500"
            aria-label="关闭"
          >
            ×
          </button>
        )}
      </div>

      {/* 冲突双方对比 */}
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <ConflictSide
          label="测评推荐"
          content={formatAssessment(detection.assessment_summary)}
        />
        <ConflictSide
          label="当前现状"
          content={formatSituation(detection.current_situation)}
        />
      </div>

      {/* 3 张选项卡片 */}
      <div className="mt-6">
        <p className="mb-3 text-sm font-medium text-ink-700">请选择一条路径：</p>
        <div className="grid gap-4 md:grid-cols-3">
          {detection.options.map((opt, idx) => (
            <OptionCard
              key={opt.id}
              option={opt}
              selected={selectedId === opt.id}
              onSelect={() => setSelectedId(opt.id)}
              iconIndex={idx}
            />
          ))}
        </div>
      </div>

      {/* 底部操作 */}
      <div className="mt-6 flex items-center justify-between border-t border-amber-100 pt-4">
        <p className="text-xs text-ink-400">
          {selectedId !== null
            ? `已选择「${detection.options.find((o) => o.id === selectedId)?.title || ""}」`
            : "请选择一条路径以继续"}
        </p>
        <Button
          disabled={selectedId === null}
          onClick={() => setModalOpen(true)}
          variant="primary"
        >
          生成行动计划
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>

      {/* reasoning 输入 modal */}
      <ReasoningModal
        open={modalOpen}
        option={selectedId !== null ? detection.options.find((o) => o.id === selectedId) || null : null}
        reasoning={reasoning}
        onReasoningChange={setReasoning}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSubmit}
        submitting={submitting}
      />
    </div>
  );
}

// ----------------------------------------------------------------------
// 子组件：冲突单方展示
// ----------------------------------------------------------------------
function ConflictSide({ label, content }: { label: string; content: string }) {
  return (
    <div className="rounded-xl border border-paper-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-400">{label}</p>
      <p className="mt-1.5 text-sm text-ink-700">{content || "暂无数据"}</p>
    </div>
  );
}

// ----------------------------------------------------------------------
// 子组件：单张选项卡片
// ----------------------------------------------------------------------
function OptionCard({
  option,
  selected,
  onSelect,
  iconIndex,
}: {
  option: PathConflictOption;
  selected: boolean;
  onSelect: () => void;
  iconIndex: number;
}) {
  const Icon = OPTION_ICONS[iconIndex] || Shield;
  const color = OPTION_COLORS[iconIndex] || OPTION_COLORS[0];
  const risk = RISK_BADGE[option.risk_level] || RISK_BADGE.medium;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "relative flex h-full flex-col rounded-xl border bg-white p-5 text-left transition-all hover:shadow-md",
        selected
          ? `border-transparent ring-2 ${color.ring} shadow-md`
          : "border-paper-200 hover:border-paper-300",
      )}
    >
      {/* 选中标记 */}
      {selected && (
        <span className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-brand-500 text-white">
          <Check className="h-3.5 w-3.5" />
        </span>
      )}

      {/* 标题区 */}
      <div className="flex items-center gap-2">
        <span className={cn("flex h-8 w-8 items-center justify-center rounded-lg", color.bg, color.text)}>
          <Icon className="h-4 w-4" />
        </span>
        <h3 className="font-semibold text-ink-800">{option.title}</h3>
      </div>

      {/* 描述 */}
      <p className="mt-2 text-sm text-ink-500 line-clamp-3">{option.description}</p>

      {/* 优势 */}
      {option.pros.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-green-700">优势</p>
          <ul className="mt-1 space-y-0.5">
            {option.pros.slice(0, 3).map((p, i) => (
              <li key={i} className="flex items-start gap-1 text-xs text-ink-600">
                <span className="mt-0.5 text-green-500">+</span>
                <span className="line-clamp-2">{p}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 劣势 */}
      {option.cons.length > 0 && (
        <div className="mt-2">
          <p className="text-xs font-medium text-red-700">劣势</p>
          <ul className="mt-1 space-y-0.5">
            {option.cons.slice(0, 2).map((c, i) => (
              <li key={i} className="flex items-start gap-1 text-xs text-ink-600">
                <span className="mt-0.5 text-red-500">−</span>
                <span className="line-clamp-2">{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 时间线 + 风险 */}
      <div className="mt-auto flex items-center justify-between gap-2 border-t border-paper-100 pt-3 text-xs">
        <span className="flex items-center gap-1 text-ink-400">
          <Clock className="h-3 w-3" />
          <span className="line-clamp-1">{option.estimated_timeline || "未指定"}</span>
        </span>
        <Badge color={risk.color}>{risk.label}</Badge>
      </div>
    </button>
  );
}

// ----------------------------------------------------------------------
// 子组件：reasoning 输入 modal
// ----------------------------------------------------------------------
function ReasoningModal({
  open,
  option,
  reasoning,
  onReasoningChange,
  onClose,
  onSubmit,
  submitting,
}: {
  open: boolean;
  option: PathConflictOption | null;
  reasoning: string;
  onReasoningChange: (v: string) => void;
  onClose: () => void;
  onSubmit: () => void;
  submitting: boolean;
}) {
  return (
    <Modal open={open} onClose={onClose} title="请填写你的选择理由">
      <div className="space-y-4">
        {option && (
          <div className="rounded-lg bg-paper-100 p-3">
            <p className="text-sm font-medium text-ink-800">已选择：{option.title}</p>
            <p className="mt-1 text-xs text-ink-500 line-clamp-2">{option.description}</p>
          </div>
        )}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-ink-700">
            选择理由 <span className="text-ink-400">（可选，建议填写以获得更精准的行动计划）</span>
          </label>
          <Textarea
            value={reasoning}
            onChange={(e) => onReasoningChange(e.target.value)}
            placeholder="例如：家庭希望我考公，但我对技术开发更感兴趣，想先尝试折中方案..."
            className="min-h-[120px]"
            maxLength={2000}
          />
          <p className="mt-1 text-right text-xs text-ink-400">{reasoning.length}/2000</p>
        </div>
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            取消
          </Button>
          <Button onClick={onSubmit} loading={submitting}>
            提交并生成行动计划
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ----------------------------------------------------------------------
// 子组件：行动计划视图
// ----------------------------------------------------------------------
function ActionPlanView({
  resolution,
  onReset,
}: {
  resolution: PathConflictResolution;
  onReset: () => void;
}) {
  const plan = resolution.action_plan || {};
  const selectedOption = resolution.options.find((o) => o.id === resolution.selected_option);
  const milestones = (plan.milestones as Array<{ phase?: string; goal?: string }>) || [];
  const resources = (plan.resources as string[]) || [];
  const risks = (plan.risks as string[]) || [];

  return (
    <div className="rounded-2xl border border-brand-200 bg-gradient-to-br from-brand-50/30 to-white p-6 shadow-sm">
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
          <Sparkles className="h-5 w-5" />
        </span>
        <div className="flex-1">
          <h2 className="text-lg font-semibold text-ink-800">你的行动计划</h2>
          <p className="mt-0.5 text-sm text-ink-500">
            基于你选择的「{selectedOption?.title || "路径"}」生成
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onReset}>
          完成
        </Button>
      </div>

      {/* 摘要 */}
      {plan.summary && (
        <div className="mt-5 rounded-xl bg-white p-4 border border-paper-200">
          <p className="text-sm text-ink-700">{plan.summary as string}</p>
        </div>
      )}

      {/* 里程碑 */}
      {milestones.length > 0 && (
        <div className="mt-5">
          <h3 className="mb-3 text-sm font-semibold text-ink-800">关键里程碑</h3>
          <div className="space-y-2">
            {milestones.map((m, i) => (
              <div key={i} className="flex items-start gap-3 rounded-lg bg-white p-3 border border-paper-200">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700">
                  {i + 1}
                </span>
                <div className="min-w-0">
                  {m.phase && <p className="text-xs font-medium text-brand-700">{m.phase}</p>}
                  {m.goal && <p className="text-sm text-ink-700">{m.goal}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 资源与风险 双栏 */}
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        {resources.length > 0 && (
          <div className="rounded-xl bg-white p-4 border border-paper-200">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-500">推荐资源</h4>
            <ul className="mt-2 space-y-1">
              {resources.map((r, i) => (
                <li key={i} className="flex items-start gap-1.5 text-xs text-ink-600">
                  <span className="mt-0.5 text-brand-500">▸</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {risks.length > 0 && (
          <div className="rounded-xl bg-white p-4 border border-paper-200">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-500">风险提示</h4>
            <ul className="mt-2 space-y-1">
              {risks.map((r, i) => (
                <li key={i} className="flex items-start gap-1.5 text-xs text-ink-600">
                  <span className="mt-0.5 text-amber-500">!</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* 用户理由回显 */}
      {resolution.reasoning && (
        <div className="mt-5 rounded-xl bg-amber-50 p-4 border border-amber-100">
          <p className="text-xs font-medium text-amber-700">你的选择理由</p>
          <p className="mt-1 text-sm text-ink-700">{resolution.reasoning}</p>
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------
// 工具函数
// ----------------------------------------------------------------------
function formatAssessment(a: PathConflictDetection["assessment_summary"]): string {
  if (!a || Object.keys(a).length === 0) return "";
  const parts: string[] = [];
  if (a.type) parts.push(a.type === "holland" ? "霍兰德" : a.type.toUpperCase());
  if (a.result_code) parts.push(`代码 ${a.result_code}`);
  if (a.directions && a.directions.length > 0) {
    parts.push(`推荐：${a.directions.slice(0, 3).join("、")}`);
  }
  return parts.join(" · ");
}

function formatSituation(s: PathConflictDetection["current_situation"]): string {
  if (!s || Object.keys(s).length === 0) return "";
  const parts: string[] = [];
  if (s.destination_type_label) parts.push(s.destination_type_label);
  else if (s.destination_type) parts.push(s.destination_type);
  if (s.status_label) parts.push(s.status_label);
  else if (s.status) parts.push(s.status);
  if (s.confidence !== undefined) parts.push(`置信度 ${s.confidence}/5`);
  return parts.join(" · ");
}

// ----------------------------------------------------------------------
// 集成用包装组件 — 直接拉取 detect 接口
// ----------------------------------------------------------------------
export function PathConflictSection() {
  const { data, error, isLoading, mutate } = useApi<PathConflictDetection>(
    "/api/path-conflict/detect",
  );
  const [dismissed, setDismissed] = useState(false);

  // 加载中或出错：不显示
  if (isLoading || error) return null;

  // 无数据或无冲突：显示提示
  if (!data || !data.has_conflict) {
    return (
      <div className="rounded-xl border border-paper-200 bg-white p-4">
        <div className="flex items-center gap-2 text-sm text-ink-500">
          <Shield className="h-4 w-4 text-green-500" />
          <span>暂无路径冲突 — 测评推荐方向与当前现状一致</span>
        </div>
      </div>
    );
  }

  // 用户主动忽略
  if (dismissed) return null;

  return (
    <PathConflictCard
      detection={data}
      onClose={() => setDismissed(true)}
      onResolved={() => {
        // 调解完成后重新检测（生成新冲突或确认无冲突）
        mutate();
      }}
    />
  );
}
