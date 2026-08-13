// 动态导入版本的图表组件：ssr: false + loading fallback。
// 用于在页面级别按需加载 recharts，减小首屏 JS 体积。
//
// 注意：BarChart / LineChart / PieChart / RadarChart 均为「命名导出」，
// 因此使用 .then(mod => mod.X) 模式从模块中取出对应命名导出。
//
// 调用方迁移示例：
//   import { DynamicBarChart } from "@/components/charts/dynamic";
// 替换原有：
//   import { BarChart } from "@/components/charts";

import dynamic from "next/dynamic";

const LoadingFallback = () => (
  <div className="h-64 w-full animate-pulse rounded-xl bg-paper-100" />
);

export const DynamicBarChart = dynamic(
  () => import("./BarChart").then((mod) => mod.BarChart),
  {
    ssr: false,
    loading: () => <LoadingFallback />,
  },
);

export const DynamicLineChart = dynamic(
  () => import("./LineChart").then((mod) => mod.LineChart),
  {
    ssr: false,
    loading: () => <LoadingFallback />,
  },
);

export const DynamicPieChart = dynamic(
  () => import("./PieChart").then((mod) => mod.PieChart),
  {
    ssr: false,
    loading: () => <LoadingFallback />,
  },
);

export const DynamicRadarChart = dynamic(
  () => import("./RadarChart").then((mod) => mod.RadarChart),
  {
    ssr: false,
    loading: () => <LoadingFallback />,
  },
);
