// 统一图表容器卡片：承载标题、副标题、描述与图表区域。
// 旧组件直接返回裸 ResponsiveContainer 或带 aria-label 的 div，
// 这里把"卡片外观 + 无障碍外框"抽象出来复用。

import type { ReactNode } from "react";

interface ChartCardProps {
  /** 卡片标题 */
  title?: ReactNode;
  /** 标题下方说明文字 */
  description?: ReactNode;
  /** 右上角附加内容（如图例、筛选器） */
  extra?: ReactNode;
  /** 提供给读屏的整图无障碍描述；传入后会渲染 role=img + aria-label */
  ariaLabel?: string;
  /** 图表主体 */
  children: ReactNode;
  className?: string;
}

export function ChartCard({
  title,
  description,
  extra,
  ariaLabel,
  children,
  className,
}: ChartCardProps) {
  return (
    <div
      className={`rounded-xl border border-paper-200 bg-white p-4 shadow-sm ${className ?? ""}`}
      role={ariaLabel ? "img" : undefined}
      aria-label={ariaLabel}
    >
      {(title || extra) && (
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            {title && (
              <h3 className="text-sm font-semibold text-ink-700">{title}</h3>
            )}
            {description && (
              <p className="mt-0.5 text-xs text-ink-400">{description}</p>
            )}
          </div>
          {extra && <div className="shrink-0">{extra}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

/** 空数据占位：旧组件统一的"暂无 X 数据"文案 + 居中布局 */
export function ChartEmpty({
  message = "暂无数据",
  height = 300,
}: {
  message?: string;
  height?: number;
}) {
  return (
    <div
      className="flex items-center justify-center text-sm text-ink-400"
      style={{ height }}
      role="status"
    >
      {message}
    </div>
  );
}
