"use client";

/**
 * QualityFeedback — 质量反馈闭环（Phase I）：双键快捷反馈。
 *
 * 👍有帮助 / 👎不准确 + 选填原因（≤200 字），点击即提交（后端 upsert，
 * 同用户同条目只留最新一条）；未登录时提示先登录。
 * P0 仅采集存储（管理端统计 P1 再做）。
 */
import { useState } from "react";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";
import { qualityFeedbackApi } from "@/lib/api/kaoyan";
import { cn } from "@/lib/utils";
import type { QualityFeedbackTargetType, QualityFeedbackType } from "@/types";

interface QualityFeedbackProps {
  targetType: QualityFeedbackTargetType;
  targetId: string;
  className?: string;
}

const BUTTONS: { type: QualityFeedbackType; label: string; icon: typeof ThumbsUp; active: string }[] = [
  { type: "helpful", label: "有帮助", icon: ThumbsUp, active: "border-green-300 bg-green-50 text-green-700" },
  { type: "unhelpful", label: "不准确", icon: ThumbsDown, active: "border-red-300 bg-red-50 text-red-700" },
];

export function QualityFeedback({ targetType, targetId, className }: QualityFeedbackProps) {
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const [selected, setSelected] = useState<QualityFeedbackType | null>(null);
  const [reasonOpen, setReasonOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async (type: QualityFeedbackType) => {
    if (!user) {
      toast.push("请先登录", "error");
      return;
    }
    setSubmitting(true);
    try {
      await qualityFeedbackApi.post({
        target_type: targetType,
        target_id: targetId,
        feedback_type: type,
        reason: reason.trim() ? reason.trim() : null,
      });
      setSelected(type);
      setReasonOpen(true);
      toast.push(type === "helpful" ? "感谢反馈" : "已收到反馈", "success");
    } catch {
      toast.push("反馈提交失败", "error");
    } finally {
      setSubmitting(false);
    }
  };

  /** 原因更新：重新提交（后端 upsert 同一反馈） */
  const saveReason = async () => {
    if (!selected || !reason.trim()) return;
    setSubmitting(true);
    try {
      await qualityFeedbackApi.post({
        target_type: targetType,
        target_id: targetId,
        feedback_type: selected,
        reason: reason.trim(),
      });
      toast.push("原因已保存", "success");
      setReasonOpen(false);
    } catch {
      toast.push("原因保存失败", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={cn("inline-flex flex-wrap items-center gap-1.5", className)}>
      {BUTTONS.map(({ type, label, icon: Icon, active }) => (
        <button
          key={type}
          type="button"
          disabled={submitting}
          onClick={() => submit(type)}
          className={cn(
            "inline-flex items-center gap-1 rounded-md border border-paper-200 px-1.5 py-0.5 text-xs text-ink-500",
            "transition-colors hover:border-brand-300 hover:text-brand-600",
            selected === type && active,
          )}
          title={`这个内容${type === "helpful" ? "对你有帮助" : "不准确/有误导"}`}
        >
          <Icon className="h-3 w-3" />
          {label}
        </button>
      ))}

      {reasonOpen && (
        <div className="flex w-full items-center gap-1.5 pt-1">
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={200}
            placeholder={`选填原因（≤200 字），为什么觉得${
              selected === "helpful" ? "有帮助" : "不准确"
            }…`}
            className="min-w-0 flex-1 rounded-md border border-paper-200 px-2 py-1 text-xs text-ink-700 outline-none focus:border-brand-300"
          />
          <button
            type="button"
            disabled={submitting || !reason.trim()}
            onClick={saveReason}
            className="shrink-0 rounded-md border border-paper-200 px-2 py-1 text-xs text-ink-600 hover:border-brand-300 hover:text-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            提交
          </button>
        </div>
      )}
    </div>
  );
}
