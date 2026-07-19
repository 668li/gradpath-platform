// 统一图表库入口。
// 用旧组件名做别名重导出，便于调用方零改动迁移：
//   import { DestinationPie } from "@/components/charts";  // 实际指向新 PieChart
//
// 注意：旧文件中存在两个同名 DestinationPie（charts.tsx 与 employment-charts.tsx）。
// 这里将 charts.tsx 的同名组件保留为 DestinationPie（name/value 形态），
// 将 employment-charts.tsx 的版本保留为 EmploymentDestinationPie（EmploymentRecord 形态）。

export { PieChart } from "./PieChart";
export { RadarChart } from "./RadarChart";
export { LineChart } from "./LineChart";
export { BarChart } from "./BarChart";

// —— 旧名别名映射 ——
export { PieChart as AdmissionPieChart } from "./PieChart";
export { PieChart as DestinationPie } from "./PieChart";
export { PieChart as EmploymentDestinationPie } from "./PieChart";

export { RadarChart as SchoolRadarChart } from "./RadarChart";
export { RadarChart as SkillRadar } from "./RadarChart";
export { RadarChart as HollandRadar } from "./RadarChart";
export { RadarChart as LifeWheelRadar } from "./RadarChart";

export { LineChart as ScoreTrendChart } from "./LineChart";
export { LineChart as TrendLine } from "./LineChart";

export { BarChart as ScoreDistributionChart } from "./BarChart";
export { BarChart as RankingBar } from "./BarChart";

// —— 基础原语（可选直接使用）——
export { ChartCard, ChartEmpty } from "./primitives/ChartCard";
export { ChartTooltip, SrOnly, tooltipStyle, tooltipStyleNeutral } from "./primitives/ChartTooltip";
export * from "./primitives/colors";

// —— 类型导出（便于调用方复用 props 形态）——
export type { PieDatum } from "./PieChart";
export type { SchoolRadarSeries, RadarPoint } from "./RadarChart";
export type { ScorePoint } from "./LineChart";
export type { DistributionPoint, RankPoint } from "./BarChart";
