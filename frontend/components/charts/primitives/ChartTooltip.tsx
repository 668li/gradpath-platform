// 统一 tooltip 样式与组件。
// 旧组件每处都重复写了同样的 contentStyle（圆角 8、浅边框、13px），
// 这里抽成共享常量 + 可选自定义 formatter 的组件。

import type { ReactNode } from "react";

// 各旧组件共用的 tooltip 外观
export const tooltipStyle: React.CSSProperties = {
  borderRadius: 8,
  border: "1px solid var(--color-paper-200, #f5f3ec)",
  fontSize: 13,
};

// 旧 employment 图表用的中性灰边框版本
export const tooltipStyleNeutral: React.CSSProperties = {
  borderRadius: 8,
  border: "1px solid #e2e0db",
  fontSize: 13,
};

interface ChartTooltipProps {
  /** 自定义渲染内容；省略时使用 recharts 默认 tooltip */
  children?: ReactNode;
  /** 使用中性灰边框版本（兼容就业类图表旧外观） */
  neutral?: boolean;
}

/**
 * 统一 tooltip 容器。
 * 大多数情况下直接把 props.style = tooltipStyle 传给 recharts <Tooltip> 即可；
 * 本组件用于需要额外包裹 / 自定义内容的场景。
 */
export function ChartTooltip({ children, neutral }: ChartTooltipProps) {
  return (
    <div style={neutral ? tooltipStyleNeutral : tooltipStyle}>{children}</div>
  );
}

/** 仅供读屏 / 文本浏览器使用的隐藏文本（sr-only），旧 employment 图表依赖它做无障碍摘要 */
export function SrOnly({ text }: { text: string }) {
  return <span className="sr-only">{text}</span>;
}
