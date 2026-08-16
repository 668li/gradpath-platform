"use client";

/**
 * QualityBadge — 资讯质量徽章（A/B/C/D 信息差升级）。
 *
 * 对应后端 quality.py 分级：A≥75 / B≥55 / C≥35 / D<35。
 * 无质量分（quality_grade 为空，如历史数据）时不渲染。
 *
 * Phase I 可解释性：传入 quality_reasons（逐维扣分原因数组）时，
 * hover title 显示实际扣分原因（每行一条）；未传入时回退通用文案。
 */
import { Badge } from "@/components/ui/form-controls";

const QUALITY_META: Record<string, { label: string; color: "green" | "blue" | "amber" | "red" | "slate"; title: string }> = {
  A: {
    label: "A 优质",
    color: "green",
    title: "权威来源 + 新鲜 + 内容完整（质量分 ≥75）",
  },
  B: {
    label: "B 良好",
    color: "blue",
    title: "较可靠来源 + 较新 + 内容较完整（质量分 ≥55）",
  },
  C: {
    label: "C 一般",
    color: "amber",
    title: "来源或时效一般，仅供参考（质量分 ≥35）",
  },
  D: {
    label: "D 低质",
    color: "red",
    title: "来源弱 / 内容不完整，谨慎参考（质量分 <35）",
  },
};

interface QualityBadgeProps {
  grade?: string | null;
  score?: number | null;
  /** Phase I 逐维扣分原因（如 ["内容完整度 24/30：正文约 600 字", …]）；空则回退通用文案 */
  reasons?: string[] | null;
  className?: string;
}

export function QualityBadge({ grade, score, reasons, className }: QualityBadgeProps) {
  if (!grade) return null;
  const meta = QUALITY_META[grade.toUpperCase()];
  if (!meta) return null;

  const hasReasons = Array.isArray(reasons) && reasons.length > 0;
  const title = hasReasons ? reasons!.join("\n") : meta.title;

  return (
    <span className={`inline-flex items-center gap-1 ${className ?? ""}`} title={title}>
      <Badge color={meta.color} className="text-xs font-semibold">
        {meta.label}
      </Badge>
      {typeof score === "number" && (
        <span className="text-xs text-ink-400" title={hasReasons ? title : `质量分 ${score}/100`}>
          {score}
        </span>
      )}
    </span>
  );
}
