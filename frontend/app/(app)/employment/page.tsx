"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, useMemo, useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  Building2,
  DollarSign,
  Target,
  BarChart3,
  Lightbulb,
  MessageSquare,
  ChevronRight,
  ExternalLink,
  Briefcase,
  TrendingUp,
  AlertTriangle,
  Star,
  MapPin,
  GraduationCap,
  // 修复: 缺失 Search 图标导入，导致 L266 引用未定义变量
  Search,
  Compass,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { careerIntelApi } from "@/lib/api/ai";
import { employmentApi } from "@/lib/api/employment";
import { useApi } from "@/lib/api/swr-config";
import { useToast } from "@/components/ui/toast";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { ListSkeleton, CardSkeleton } from "@/components/ui/skeleton";
import {
  BarChart as ReBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type {
  CompanyIntelResponse,
  CareerPositioningResponse,
  CareerDarkKnowledgeResponse,
  CareerDarkKnowledgeStage,
  SalaryBenchmark,
  EmploymentStats,
} from "@/types";

// ===== Recharts 内联对象提取为模块级常量（A3 性能优化） =====
const SALARY_CHART_TICK = { fontSize: 12 } as const;
const SALARY_CHART_TOOLTIP_STYLE = {
  background: "white",
  border: "1px solid #e5e5e5",
  borderRadius: "8px",
} as const;
const SALARY_CHART_GRID_COLOR = "var(--color-paper-200, #f5f3ec)";

// ===== Tab 配置 =====
const tabs = [
  { id: "intel", label: "公司情报", icon: Building2, color: "text-blue-700", desc: "查看你保存的公司情报，了解加班强度、裁员风险、晋升前景等关键信息" },
  { id: "salary", label: "薪资查询", icon: DollarSign, color: "text-green-700", desc: "查询各公司岗位薪资数据，对比分析薪资分布" },
  { id: "positioning", label: "求职定位", icon: Target, color: "text-purple-700", desc: "基于你的背景进行竞争力评估，获取冲刺/目标/保底公司推荐" },
  { id: "employment", label: "就业数据", icon: BarChart3, color: "text-amber-700", desc: "查看各高校就业率、行业分布、去向统计等数据" },
  { id: "dark-knowledge", label: "暗知识", icon: Lightbulb, color: "text-rose-700", desc: "求职过程中那些没人告诉你的关键经验与教训" },
  { id: "interview", label: "面经库", icon: MessageSquare, color: "text-cyan-700", desc: "海量面试经验分享，助你充分准备每一场面试" },
  { id: "bright-outlook", label: "朝阳职业", icon: Sparkles, color: "text-orange-700", desc: "Bright Outlook 朝阳职业：高增长、快速扩张与新兴岗位标记，帮你瞄准正在变热的赛道" },
  { id: "salary-slice", label: "薪资透视", icon: DollarSign, color: "text-emerald-700", desc: "按岗位 × 城市查看薪资四分位分布，校准期望薪资" },
];

// ===== 标签颜色映射 =====
const overtimeColors: Record<string, string> = {
  none: "bg-green-100 text-green-700",
  mild: "bg-blue-100 text-blue-700",
  moderate: "bg-amber-100 text-amber-700",
  severe: "bg-red-100 text-red-700",
  unknown: "bg-ink-100 text-ink-500",
};

const overtimeLabels: Record<string, string> = {
  none: "无加班",
  mild: "轻度",
  moderate: "中度",
  severe: "严重",
  unknown: "未知",
};

const layoffColors: Record<string, string> = {
  none: "bg-green-100 text-green-700",
  low: "bg-blue-100 text-blue-700",
  moderate: "bg-amber-100 text-amber-700",
  high: "bg-red-100 text-red-700",
  unknown: "bg-ink-100 text-ink-500",
};

const layoffLabels: Record<string, string> = {
  none: "无风险",
  low: "低风险",
  moderate: "中等风险",
  high: "高风险",
  unknown: "未知",
};

const promotionColors: Record<string, string> = {
  good: "bg-green-100 text-green-700",
  fair: "bg-amber-100 text-amber-700",
  poor: "bg-red-100 text-red-700",
  unknown: "bg-ink-100 text-ink-500",
};

const promotionLabels: Record<string, string> = {
  good: "前景好",
  fair: "一般",
  poor: "较差",
  unknown: "未知",
};

const importanceColors: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high: "bg-amber-100 text-amber-700 border-amber-200",
  medium: "bg-blue-100 text-blue-700 border-blue-200",
};

const importanceLabels: Record<string, string> = {
  critical: "关键",
  high: "重要",
  medium: "一般",
};

// 修复: Tailwind 不能 JIT 动态类名 (如 `bg-${color}-50`)，必须用静态完整类名映射
// 否则这些类不会出现在最终 CSS 中，样式会失效
const iconBgColors: Record<string, string> = {
  blue: "bg-blue-50",
  green: "bg-green-50",
  purple: "bg-purple-50",
  amber: "bg-amber-50",
};

const iconTextColors: Record<string, string> = {
  blue: "text-blue-500",
  green: "text-green-500",
  purple: "text-purple-500",
  amber: "text-amber-500",
};

// ===== 朝阳职业数据（O*NET Bright Outlook 灵感） =====
type BrightOutlookColor = "red" | "orange" | "green" | "gray";
type BrightOutlookRole = {
  name: string;
  growth: number;
  badge: string;
  label: string;
  color: BrightOutlookColor;
  desc: string;
};

const BRIGHT_OUTLOOK_ROLES: BrightOutlookRole[] = [
  { name: "AI工程师", growth: 35, badge: "🔥", label: "高增长", color: "red", desc: "大模型与应用层需求爆发，算法与工程复合人才紧缺" },
  { name: "数据科学家", growth: 28, badge: "🔥", label: "高增长", color: "red", desc: "数据驱动决策渗透各行业，建模与业务洞察双能力受追捧" },
  { name: "云计算工程师", growth: 25, badge: "⬆", label: "快速增长", color: "orange", desc: "企业上云持续深化，云原生与稳定性方向岗位扩张" },
  { name: "网络安全工程师", growth: 32, badge: "🔥", label: "高增长", color: "red", desc: "合规与攻防双轮驱动，安全人才缺口长期存在" },
  { name: "新能源工程师", growth: 30, badge: "🆕", label: "新兴", color: "green", desc: "光伏、储能、新能源汽车带动交叉学科岗位崛起" },
  { name: "芯片设计工程师", growth: 22, badge: "⬆", label: "快速增长", color: "orange", desc: "国产替代主线明确，数字/模拟/验证方向持续招人" },
  { name: "产品经理", growth: 15, badge: "⬆", label: "稳定增长", color: "orange", desc: "AI 产品与 B 端产品方向需求结构性走强" },
  { name: "全栈工程师", growth: 18, badge: "⬆", label: "快速增长", color: "orange", desc: "中小团队偏好端到端交付能力，全栈性价比凸显" },
  { name: "DevOps工程师", growth: 21, badge: "⬆", label: "快速增长", color: "orange", desc: "平台工程与可观测性方向稳定扩张" },
  { name: "用户研究师", growth: 19, badge: "⬆", label: "稳定增长", color: "orange", desc: "体验经济下用研介入产品全生命周期" },
  { name: "商业分析师", growth: 14, badge: "→", label: "平稳", color: "gray", desc: "SQL + 业务理解为基础岗，进阶需建模能力" },
  { name: "供应链管理", growth: 12, badge: "→", label: "平稳", color: "gray", desc: "制造业与跨境电商保持稳定吸纳" },
  { name: "数字营销", growth: 16, badge: "⬆", label: "稳定增长", color: "orange", desc: "内容种草与投流操盘手需求上行" },
  { name: "内容运营", growth: 10, badge: "→", label: "平稳", color: "gray", desc: "岗位总量大但门槛走低，差异化能力成关键" },
  { name: "人力资源", growth: 8, badge: "→", label: "平稳", color: "gray", desc: "HRBP 与组织发展方向相对稳健" },
];

const brightOutlookColorClasses: Record<BrightOutlookColor, string> = {
  red: "bg-red-100 text-red-700 border-red-200",
  orange: "bg-orange-100 text-orange-700 border-orange-200",
  green: "bg-green-100 text-green-700 border-green-200",
  gray: "bg-ink-100 text-ink-600 border-ink-200",
};

const brightOutlookBarColors: Record<BrightOutlookColor, string> = {
  red: "#ef4444",
  orange: "#f97316",
  green: "#22c55e",
  gray: "#9ca3af",
};

// 模糊匹配岗位名，命中则返回朝阳职业信息（用于现有公司/岗位列表加标记）
function findBrightOutlook(position: string | null | undefined): BrightOutlookRole | null {
  if (!position) return null;
  const p = position.toLowerCase();
  return BRIGHT_OUTLOOK_ROLES.find((r) => p.includes(r.name.toLowerCase())) ?? null;
}

// ===== 薪资透视数据（Glassdoor 灵感：按城市切片） =====
type SalarySlice = { p25: string; p50: string; p75: string; p90: string };
const SALARY_DATA: Record<string, Record<string, SalarySlice>> = {
  软件工程师: {
    北京: { p25: "18万", p50: "25万", p75: "35万", p90: "50万" },
    上海: { p25: "17万", p50: "24万", p75: "34万", p90: "48万" },
    深圳: { p25: "16万", p50: "23万", p75: "32万", p90: "45万" },
    杭州: { p25: "15万", p50: "22万", p75: "30万", p90: "42万" },
    成都: { p25: "12万", p50: "18万", p75: "25万", p90: "35万" },
  },
  数据科学家: {
    北京: { p25: "20万", p50: "30万", p75: "45万", p90: "65万" },
    上海: { p25: "19万", p50: "28万", p75: "42万", p90: "60万" },
    深圳: { p25: "18万", p50: "27万", p75: "40万", p90: "55万" },
    杭州: { p25: "16万", p50: "25万", p75: "38万", p90: "52万" },
    成都: { p25: "13万", p50: "20万", p75: "30万", p90: "42万" },
  },
  AI工程师: {
    北京: { p25: "25万", p50: "38万", p75: "55万", p90: "80万" },
    上海: { p25: "23万", p50: "35万", p75: "52万", p90: "75万" },
    深圳: { p25: "22万", p50: "34万", p75: "50万", p90: "72万" },
    杭州: { p25: "20万", p50: "32万", p75: "48万", p90: "68万" },
    成都: { p25: "15万", p50: "24万", p75: "36万", p90: "50万" },
  },
  算法工程师: {
    北京: { p25: "22万", p50: "33万", p75: "50万", p90: "72万" },
    上海: { p25: "20万", p50: "31万", p75: "46万", p90: "66万" },
    深圳: { p25: "19万", p50: "30万", p75: "44万", p90: "63万" },
    杭州: { p25: "18万", p50: "28万", p75: "42万", p90: "60万" },
    成都: { p25: "14万", p50: "22万", p75: "32万", p90: "45万" },
  },
  产品经理: {
    北京: { p25: "18万", p50: "26万", p75: "38万", p90: "55万" },
    上海: { p25: "17万", p50: "25万", p75: "36万", p90: "52万" },
    深圳: { p25: "16万", p50: "24万", p75: "34万", p90: "48万" },
    杭州: { p25: "15万", p50: "22万", p75: "32万", p90: "45万" },
    成都: { p25: "12万", p50: "18万", p75: "26万", p90: "36万" },
  },
  前端工程师: {
    北京: { p25: "16万", p50: "23万", p75: "32万", p90: "45万" },
    上海: { p25: "15万", p50: "22万", p75: "31万", p90: "43万" },
    深圳: { p25: "14万", p50: "21万", p75: "30万", p90: "42万" },
    杭州: { p25: "13万", p50: "20万", p75: "28万", p90: "40万" },
    成都: { p25: "10万", p50: "16万", p75: "22万", p90: "32万" },
  },
  后端工程师: {
    北京: { p25: "17万", p50: "25万", p75: "35万", p90: "50万" },
    上海: { p25: "16万", p50: "24万", p75: "34万", p90: "48万" },
    深圳: { p25: "15万", p50: "23万", p75: "32万", p90: "46万" },
    杭州: { p25: "14万", p50: "21万", p75: "30万", p90: "42万" },
    成都: { p25: "11万", p50: "17万", p75: "24万", p90: "34万" },
  },
  测试工程师: {
    北京: { p25: "12万", p50: "18万", p75: "25万", p90: "35万" },
    上海: { p25: "11万", p50: "17万", p75: "24万", p90: "33万" },
    深圳: { p25: "10万", p50: "16万", p75: "23万", p90: "32万" },
    杭州: { p25: "10万", p50: "15万", p75: "22万", p90: "30万" },
    成都: { p25: "8万", p50: "13万", p75: "18万", p90: "26万" },
  },
  运维工程师: {
    北京: { p25: "14万", p50: "21万", p75: "30万", p90: "42万" },
    上海: { p25: "13万", p50: "20万", p75: "28万", p90: "40万" },
    深圳: { p25: "12万", p50: "19万", p75: "27万", p90: "38万" },
    杭州: { p25: "11万", p50: "17万", p75: "25万", p90: "35万" },
    成都: { p25: "9万", p50: "14万", p75: "20万", p90: "28万" },
  },
  UI设计师: {
    北京: { p25: "13万", p50: "19万", p75: "27万", p90: "38万" },
    上海: { p25: "12万", p50: "18万", p75: "26万", p90: "36万" },
    深圳: { p25: "11万", p50: "17万", p75: "24万", p90: "34万" },
    杭州: { p25: "10万", p50: "16万", p75: "22万", p90: "32万" },
    成都: { p25: "8万", p50: "13万", p75: "18万", p90: "26万" },
  },
};


// ===== 子组件 =====

function Tab1Intel() {
  const toast = useToast();
  const { data: intelList, error, isLoading } = useApi<CompanyIntelResponse[]>(
    "/api/career-intel/intel/list",
    { fallbackData: [] },
  );

  useEffect(() => {
    if (error) toast.push(error.message || "加载公司情报失败", "error");
  }, [error, toast]);

  if (isLoading) return <ListSkeleton count={3} />;

  const list = intelList ?? [];

  if (list.length === 0) {
    return (
      <EmptyState
        title="探索你的第一家公司"
        description="输入目标公司名，AI 帮你分析加班强度、裁员风险、晋升前景、薪资竞争力等关键情报，保存后随时回看。"
        action={
          <a href="/war-room" className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors">
            <Search className="h-4 w-4" />
            搜索公司，生成情报
          </a>
        }
      />
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {list.map((intel) => {
        const bo = findBrightOutlook(intel.position_name);
        return (
        <div key={intel.id} className="bg-white rounded-xl border border-paper-200 p-5 hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="font-bold text-ink-800 text-lg">{intel.company_name}</h3>
              <div className="flex items-center gap-2 flex-wrap">
                <p className="text-sm text-ink-500">{intel.position_name} · {intel.industry}</p>
                {bo && <BrightOutlookBadge role={bo} compact />}
              </div>
            </div>
            {intel.salary_range && (
              <span className="text-sm font-medium text-green-600 bg-green-50 px-2 py-1 rounded">
                {intel.salary_range}
              </span>
            )}
          </div>

          <div className="flex flex-wrap gap-2 mb-3">
            <span className={cn("text-xs px-2 py-1 rounded-full", overtimeColors[intel.overtime_intensity] || overtimeColors.unknown)}>
              加班: {overtimeLabels[intel.overtime_intensity] || "未知"}
            </span>
            <span className={cn("text-xs px-2 py-1 rounded-full", layoffColors[intel.layoff_risk] || layoffColors.unknown)}>
              裁员: {layoffLabels[intel.layoff_risk] || "未知"}
            </span>
            <span className={cn("text-xs px-2 py-1 rounded-full", promotionColors[intel.promotion_outlook] || promotionColors.unknown)}>
              晋升: {promotionLabels[intel.promotion_outlook] || "未知"}
            </span>
          </div>

          {intel.insider_notes && (
            <p className="text-sm text-ink-600 line-clamp-2">{intel.insider_notes}</p>
          )}

          {/* 情报时效标注 — 诚实规则：过时就说可能过时 */}
          {(() => {
            const ageDays = Math.floor((Date.now() - new Date(intel.created_at).getTime()) / 86400000);
            if (!Number.isFinite(ageDays) || ageDays < 0) return null;
            const stale = ageDays > 180;
            return (
              <p className={cn("mt-2 text-[11px]", stale ? "text-amber-600" : "text-ink-400")}>
                情报生成于 {new Date(intel.created_at).toLocaleDateString("zh-CN")}
                （{ageDays === 0 ? "今天" : `${ageDays} 天前`}）
                {stale && " · 已超过半年，市场环境可能已变化，建议交叉验证"}
              </p>
            );
          })()}

          {intel.risk_warnings.length > 0 && (
            <div className="mt-3 flex items-start gap-2 text-sm text-amber-600">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{intel.risk_warnings[0]}</span>
            </div>
          )}

          <div className="mt-4 pt-3 border-t border-paper-100 flex items-center justify-between gap-2">
            <span className="text-xs text-ink-400">不确定这个岗位适不适合你？</span>
            {intel.position_name && <VirtualTrialButton role={intel.position_name} />}
          </div>
        </div>
        );
      })}
    </div>
  );
}

function Tab2Salary() {
  const toast = useToast();
  const [searchText, setSearchText] = useState("");

  // 修复 P0 bug: 后端可能返回 null/非数组，导致 salaries.forEach/filter 崩溃
  const { data: rawData, error, isLoading } = useApi<SalaryBenchmark[]>(
    "/api/salary-benchmarks",
    { fallbackData: [] },
  );

  useEffect(() => {
    if (error) toast.push(error.message || "加载薪资数据失败", "error");
  }, [error, toast]);

  const salaries = useMemo(
    () => (Array.isArray(rawData) ? rawData : []),
    [rawData],
  );

  const filtered = searchText
    ? salaries.filter(
        (s) =>
          s.position?.toLowerCase().includes(searchText.toLowerCase()) ||
          s.company?.toLowerCase().includes(searchText.toLowerCase()) ||
          s.city?.toLowerCase().includes(searchText.toLowerCase()),
      )
    : salaries;

  const chartData = useMemo(() => {
    const grouped: Record<string, { min: number; max: number; median: number; count: number }> = {};
    // 修复 P2 bug: 薪资字段可能为 null/undefined，导致 NaN 显示
    salaries.forEach((s) => {
      if (s.salary_min == null || s.salary_max == null || s.salary_median == null) return;
      if (!grouped[s.position]) {
        grouped[s.position] = { min: s.salary_min, max: s.salary_max, median: s.salary_median, count: 1 };
      } else {
        grouped[s.position].min = Math.min(grouped[s.position].min, s.salary_min);
        grouped[s.position].max = Math.max(grouped[s.position].max, s.salary_max);
        grouped[s.position].median = (grouped[s.position].median * grouped[s.position].count + s.salary_median) / (grouped[s.position].count + 1);
        grouped[s.position].count++;
      }
    });
    // 统一换算为万元/年（数据库存储单位为元）
    return Object.entries(grouped).map(([position, data]) => ({
      position,
      min: Math.round(data.min / 1000) / 10,
      max: Math.round(data.max / 1000) / 10,
      median: Math.round(data.median / 1000) / 10,
    }));
  }, [salaries]);

  if (isLoading) return <ListSkeleton count={3} />;

  if (salaries.length === 0) {
    return (
      <EmptyState
        title="薪资数据即将呈现"
        description="系统已收录 2880 条薪资基准数据。如果此处为空，可能是筛选条件过严——试试清除搜索关键词，或前往求职作战室查询特定岗位薪资。"
        action={
          <a href="/war-room" className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors">
            <DollarSign className="h-4 w-4" />
            去作战室查薪资
          </a>
        }
      />
    );
  }

  const filteredChart = searchText
    ? chartData.filter(
        (d) =>
          d.position.toLowerCase().includes(searchText.toLowerCase()),
      )
    : chartData;

  return (
    <div className="space-y-6">
      {/* 搜索 */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -tranink-y-1/2 h-4 w-4 text-ink-400" />
        <input
          type="text"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          placeholder="搜索岗位、公司、城市..."
          className="w-full rounded-lg border border-paper-300 bg-white pl-9 pr-3 py-2 text-sm text-ink-800 placeholder:text-ink-400 focus:border-green-500 focus:outline-none focus:ring-2 focus:ring-green-100"
        />
      </div>
      {/* 薪资分布图 */}
      {filteredChart.length > 0 && (
        <div className="bg-white rounded-xl border border-paper-200 p-5">
          <h3 className="font-bold text-ink-800 mb-4">岗位薪资分布（单位：万元/年）</h3>
          <ResponsiveContainer width="100%" height={300}>
            <ReBarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={SALARY_CHART_GRID_COLOR} />
              <XAxis dataKey="position" tick={SALARY_CHART_TICK} />
              <YAxis tick={SALARY_CHART_TICK} />
              <Tooltip
                contentStyle={SALARY_CHART_TOOLTIP_STYLE}
                formatter={(value: number) => [`${value.toFixed(1)}万`, ""]}
              />
              <Bar dataKey="median" fill="#3377f6" radius={[4, 4, 0, 0]} name="中位数" />
            </ReBarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* 薪资表格（虚拟滚动） */}
      <SalaryTable salaries={filtered} totalCount={salaries.length} />
    </div>
  );
}

/** 移动端（<768px）检测：窄屏上 6 列表格挤成竖排不可读，改用卡片列表 */
function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const update = () => setIsMobile(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return isMobile;
}

// ===== 薪资表格虚拟滚动组件 =====
function SalaryTable({
  salaries,
  totalCount,
}: {
  salaries: SalaryBenchmark[];
  totalCount: number;
}) {
  const isMobile = useIsMobile();
  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: salaries.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 52,
    overscan: 8,
  });

  if (salaries.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-paper-200 p-8 text-center text-sm text-ink-400">
        暂无匹配的薪资数据
      </div>
    );
  }

  // 移动端：卡片列表（表格在 375px 宽度下逐字竖排、表头表体错位）
  if (isMobile) {
    const shown = salaries.slice(0, 50);
    return (
      <div className="bg-white rounded-xl border border-paper-200 p-4 space-y-3">
        {salaries.length > 50 && (
          <p className="text-xs text-ink-400">
            共 {salaries.length} 条匹配，仅显示前 50 条——试试用上方搜索缩小范围
          </p>
        )}
        {shown.map((s) => {
          const bo = findBrightOutlook(s.position);
          return (
            <div key={s.id} className="rounded-lg border border-paper-200 p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-ink-800">{s.company}</p>
                  <p className="mt-0.5 flex items-center gap-1.5 text-xs text-ink-600">
                    {s.position}
                    {bo && <BrightOutlookBadge role={bo} compact />}
                  </p>
                </div>
                <p className="shrink-0 text-right text-sm font-semibold text-green-600">
                  {(s.salary_median / 10000).toFixed(1)}万
                  <span className="block text-[10px] font-normal text-ink-400">中位数/年</span>
                </p>
              </div>
              <div className="mt-2 flex items-center justify-between text-xs text-ink-500">
                <span>{[s.city, s.experience_level].filter(Boolean).join(" · ") || "-"}</span>
                <span>
                  {(s.salary_min / 10000).toFixed(1)}-{(s.salary_max / 10000).toFixed(1)}万
                </span>
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-paper-200 overflow-hidden">
      {/* 表头（sticky） */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-paper-200 bg-paper-50">
              <th className="px-4 py-3 text-left font-medium text-ink-600">公司</th>
              <th className="px-4 py-3 text-left font-medium text-ink-600">岗位</th>
              <th className="px-4 py-3 text-left font-medium text-ink-600">城市</th>
              <th className="px-4 py-3 text-left font-medium text-ink-600">经验级别</th>
              <th className="px-4 py-3 text-right font-medium text-ink-600">薪资范围</th>
              <th className="px-4 py-3 text-right font-medium text-ink-600">中位数</th>
            </tr>
          </thead>
        </table>
      </div>
      {/* 虚拟滚动 body */}
      <div ref={parentRef} style={{ height: "500px", overflow: "auto" }}>
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            position: "relative",
            width: "100%",
          }}
        >
          <table className="w-full text-sm">
            <tbody>
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const s = salaries[virtualRow.index];
                const bo = findBrightOutlook(s.position);
                return (
                  <tr
                    key={s.id}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      transform: `translateY(${virtualRow.start}px)`,
                      display: "table-row",
                    }}
                    className="border-b border-paper-100 hover:bg-paper-50/50"
                  >
                    <td className="px-4 py-3 font-medium text-ink-800">{s.company}</td>
                    <td className="px-4 py-3 text-ink-600">
                      <span className="inline-flex items-center gap-1.5">
                        {s.position}
                        {bo && <BrightOutlookBadge role={bo} compact />}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-ink-600">{s.city || "-"}</td>
                    <td className="px-4 py-3 text-ink-600">{s.experience_level}</td>
                    <td className="px-4 py-3 text-right text-ink-800">{(s.salary_min / 10000).toFixed(1)}-{(s.salary_max / 10000).toFixed(1)}万</td>
                    <td className="px-4 py-3 text-right font-medium text-green-600">{(s.salary_median / 10000).toFixed(1)}万</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      {totalCount > salaries.length && (
        <p className="text-center text-sm text-ink-400 py-3">
          显示 {salaries.length} 条（共 {totalCount} 条数据）
        </p>
      )}
    </div>
  );
}

function Tab3Positioning() {
  const toast = useToast();
  const [positioning, setPositioning] = useState<CareerPositioningResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await careerIntelApi.getLatestPositioning();
        setPositioning(data);
      } catch (err) {
        toast.push(err instanceof Error ? err.message : "加载求职定位失败", "error");
      } finally {
        setLoading(false);
      }
    })();
  }, [toast]);

  if (loading) return <ListSkeleton count={2} />;

  if (!positioning) {
    return (
      <EmptyState
        title="找到你的求职定位"
        description="告诉 AI 你的学校、专业、实习经历和目标岗位，30 秒生成竞争力评分 + 冲刺/目标/保底三档公司推荐。"
        action={
          <a href="/war-room" className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors">
            <Target className="h-4 w-4" />
            开始求职定位评估
          </a>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* 竞争力评分 */}
      <div className="bg-gradient-to-r from-purple-50 to-purple-100 rounded-xl p-6 border border-purple-200">
        <div className="flex items-center gap-3 mb-2">
          <Target className="h-6 w-6 text-purple-600" />
          <h3 className="font-bold text-purple-900 text-lg">竞争力评估</h3>
        </div>
        {positioning.competitiveness_score != null && (
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-purple-700">{positioning.competitiveness_score}</span>
            <span className="text-sm text-purple-600">/ 100</span>
          </div>
        )}
        {positioning.ai_assessment && (
          <p className="mt-3 text-sm text-purple-800 leading-relaxed">{positioning.ai_assessment}</p>
        )}
      </div>

      {/* 公司推荐 */}
      <div className="grid gap-4 md:grid-cols-3">
        {[
          { label: "冲刺公司", data: positioning.reach_companies, color: "amber", icon: TrendingUp },
          { label: "目标公司", data: positioning.target_companies, color: "blue", icon: Target },
          { label: "保底公司", data: positioning.safety_companies, color: "green", icon: Star },
        ].map(({ label, data, color, icon: Icon }) => (
          <div key={label} className="bg-white rounded-xl border border-paper-200 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Icon className={cn("h-5 w-5", iconTextColors[color])} />
              <h4 className="font-bold text-ink-800">{label}</h4>
            </div>
            {data.length === 0 ? (
              <p className="text-sm text-ink-400">暂无推荐</p>
            ) : (
              <div className="space-y-2">
                {data.slice(0, 3).map((c, i) => (
                  <div key={`${c.name}-${c.position}-${i}`} className="text-sm">
                    <div className="font-medium text-ink-800">{c.name}</div>
                    <div className="text-ink-500">{c.position} · 概率 {Math.round(c.probability * 100)}%</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 技能差距 */}
      {positioning.skill_gaps.length > 0 && (
        <div className="bg-white rounded-xl border border-paper-200 p-5">
          <h3 className="font-bold text-ink-800 mb-3">技能差距分析</h3>
          <div className="space-y-3">
            {positioning.skill_gaps.map((gap, i) => (
              <div key={`${gap.skill}-${i}`} className="flex items-start gap-3">
                <div className="h-6 w-6 shrink-0 rounded-full bg-amber-100 flex items-center justify-center text-amber-600 text-xs font-bold">
                  {i + 1}
                </div>
                <div>
                  <div className="font-medium text-ink-800">{gap.skill}</div>
                  <div className="text-sm text-ink-500">{gap.suggestion}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Tab4Employment() {
  const toast = useToast();
  const [stats, setStats] = useState<EmploymentStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await employmentApi.stats();
        setStats(data);
      } catch (err) {
        toast.push(err instanceof Error ? err.message : "加载就业数据失败", "error");
      } finally {
        setLoading(false);
      }
    })();
  }, [toast]);

  if (loading) return <ListSkeleton count={2} />;

  if (!stats) {
    return (
      <EmptyState
        title="暂无就业数据"
        description="系统正在持续收录就业数据，请稍后查看"
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* 数据概览 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "收录院校", value: stats.school_count, icon: GraduationCap, color: "blue" },
          { label: "数据报告", value: stats.report_count, icon: BarChart3, color: "green" },
          { label: "专业覆盖", value: stats.major_count, icon: Briefcase, color: "purple" },
          { label: "数据年份", value: stats.year_range[0] && stats.year_range[1] ? `${stats.year_range[0]}-${stats.year_range[1]}` : "-", icon: TrendingUp, color: "amber" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl border border-paper-200 p-4">
            <div className={cn("h-10 w-10 rounded-lg flex items-center justify-center mb-3", iconBgColors[color])}>
              <Icon className={cn("h-5 w-5", iconTextColors[color])} />
            </div>
            <div className="text-2xl font-bold text-ink-800">{value}</div>
            <div className="text-sm text-ink-500">{label}</div>
          </div>
        ))}
      </div>

      {/* 快速搜索入口 */}
      <div className="bg-white rounded-xl border border-paper-200 p-6">
        <h3 className="font-bold text-ink-800 mb-2">查询就业数据</h3>
        <p className="text-sm text-ink-500 mb-4">搜索特定高校的就业率、行业分布、去向统计等详细数据</p>
        <a
          href="/employment/search"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-amber-600 text-white rounded-lg font-medium text-sm hover:opacity-90"
        >
          开始搜索
          <ChevronRight className="h-4 w-4" />
        </a>
      </div>
    </div>
  );
}

function Tab5DarkKnowledge() {
  const toast = useToast();
  const [stages, setStages] = useState<CareerDarkKnowledgeStage[]>([]);
  const [knowledge, setKnowledge] = useState<CareerDarkKnowledgeResponse[]>([]);
  const [selectedStage, setSelectedStage] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [stageData, knowledgeData] = await Promise.all([
          careerIntelApi.getDarkKnowledgeStages(),
          careerIntelApi.getDarkKnowledge(),
        ]);
        setStages(stageData);
        setKnowledge(knowledgeData);
        if (stageData.length > 0) setSelectedStage(stageData[0].stage);
      } catch (err) {
        toast.push(err instanceof Error ? err.message : "加载暗知识失败", "error");
      } finally {
        setLoading(false);
      }
    })();
  }, [toast]);

  const handleStageChange = async (stage: string) => {
    setSelectedStage(stage);
    try {
      const data = await careerIntelApi.getDarkKnowledge(stage);
      setKnowledge(data);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    }
  };

  if (loading) return <ListSkeleton count={3} />;

  const filteredKnowledge = selectedStage
    ? knowledge.filter((k) => k.stage === selectedStage)
    : knowledge;

  return (
    <div className="space-y-6">
      {/* 阶段切换 */}
      {stages.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {stages.map((s) => (
            <button
              key={s.stage}
              onClick={() => handleStageChange(s.stage)}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                selectedStage === s.stage
                  ? "bg-rose-600 text-white"
                  : "bg-white border border-paper-200 text-ink-600 hover:bg-paper-50"
              )}
            >
              {s.stage_name} ({s.count})
            </button>
          ))}
        </div>
      )}

      {/* 暗知识卡片 */}
      {filteredKnowledge.length === 0 ? (
        <EmptyState
          title="该阶段暂无暗知识"
          description="试试其他阶段"
        />
      ) : (
        <div className="space-y-4">
          {filteredKnowledge.map((item) => (
            <div
              key={item.id}
              className={cn(
                "bg-white rounded-xl border p-5 hover:shadow-md transition-shadow",
                importanceColors[item.importance] || "border-paper-200"
              )}
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-bold text-ink-800">{item.title}</h3>
                <span className={cn(
                  "text-xs px-2 py-1 rounded-full shrink-0",
                  importanceColors[item.importance]
                )}>
                  {importanceLabels[item.importance] || item.importance}
                </span>
              </div>

              <p className="text-sm text-ink-600 leading-relaxed mb-3">{item.content}</p>

              {item.common_misconception && (
                <div className="bg-amber-50 rounded-lg p-3 mb-3">
                  <p className="text-xs font-medium text-amber-700 mb-1">常见误解</p>
                  <p className="text-sm text-amber-800">{item.common_misconception}</p>
                </div>
              )}

              {item.actionable_advice && (
                <div className="bg-green-50 rounded-lg p-3">
                  <p className="text-xs font-medium text-green-700 mb-1">实操建议</p>
                  <p className="text-sm text-green-800">{item.actionable_advice}</p>
                </div>
              )}

              {item.tags.length > 0 && (
                <div className="flex gap-1 mt-3 flex-wrap">
                  {item.tags.map((tag) => (
                    <span key={tag} className="text-xs bg-paper-100 text-ink-500 px-2 py-0.5 rounded">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Tab6Interview() {
  return (
    <div className="space-y-6">
      {/* 面经库引导 */}
      <div className="bg-gradient-to-r from-cyan-50 to-cyan-100 rounded-xl p-6 border border-cyan-200">
        <div className="flex items-center gap-3 mb-3">
          <MessageSquare className="h-6 w-6 text-cyan-600" />
          <h3 className="font-bold text-cyan-900 text-lg">面经库</h3>
        </div>
        <p className="text-sm text-cyan-800 leading-relaxed mb-4">
          海量面试经验分享，覆盖技术面、HR面、群面等多种面试形式。搜索你目标公司的面经，提前做好充分准备。
        </p>
        <a
          href="/interview"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-cyan-600 text-white rounded-lg font-medium text-sm hover:opacity-90"
        >
          进入面经库
          <ExternalLink className="h-4 w-4" />
        </a>
      </div>

      {/* 快捷入口卡片 */}
      <div className="grid gap-4 md:grid-cols-2">
        {[
          { title: "搜索面经", desc: "按公司、岗位搜索面试经验", href: "/interview?tab=search", color: "blue" },
          { title: "提交面经", desc: "分享你的面试经验，帮助后来者", href: "/interview?tab=submit", color: "green" },
          { title: "我的面经", desc: "查看你提交的面经记录", href: "/interview?tab=mine", color: "purple" },
          { title: "面经统计", desc: "查看各公司面经热度排行", href: "/interview?tab=stats", color: "amber" },
        ].map(({ title, desc, href, color }) => (
          <a
            key={title}
            href={href}
            className="bg-white rounded-xl border border-paper-200 p-5 hover:shadow-md transition-shadow group"
          >
            <div className="flex items-start justify-between">
              <div>
                <h4 className="font-bold text-ink-800 mb-1 group-hover:text-cyan-600 transition-colors">{title}</h4>
                <p className="text-sm text-ink-500">{desc}</p>
              </div>
              <ChevronRight className="h-5 w-5 text-ink-300 group-hover:text-cyan-500 transition-colors" />
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

// ===== 朝阳职业标记徽章（用于现有列表与新 Tab） =====
function BrightOutlookBadge({
  role,
  compact,
}: {
  role: BrightOutlookRole;
  compact?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border text-xs font-medium",
        brightOutlookColorClasses[role.color],
        compact ? "px-1.5 py-0.5" : "px-2 py-1",
      )}
      title={`${role.label} · 增长率 ${role.growth}%`}
    >
      <span>{role.badge}</span>
      <span>{role.label}</span>
      {!compact && <span className="opacity-70">+{role.growth}%</span>}
    </span>
  );
}

// ===== 虚拟试岗入口（Forage 灵感） =====
function VirtualTrialButton({ role, size = "sm" }: { role: string; size?: "sm" | "md" }) {
  const href = `/career-simulator?from=employment&role=${encodeURIComponent(role)}`;
  return (
    <a
      href={href}
      title="不确定这个岗位适不适合你？先试驾体验一天"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg bg-purple-600 text-white font-medium hover:opacity-90 transition-opacity",
        size === "sm" ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm",
      )}
    >
      <Compass className={size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4"} />
      虚拟试岗
    </a>
  );
}

// ===== Tab7: 朝阳职业（Bright Outlook） =====
function Tab7BrightOutlook() {
  const [keyword, setKeyword] = useState("");
  const filtered = keyword
    ? BRIGHT_OUTLOOK_ROLES.filter(
        (r) => r.name.includes(keyword) || r.label.includes(keyword),
      )
    : BRIGHT_OUTLOOK_ROLES;
  const sorted = [...filtered].sort((a, b) => b.growth - a.growth);
  const maxGrowth = Math.max(...BRIGHT_OUTLOOK_ROLES.map((r) => r.growth));

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl p-5 border border-orange-200">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="h-5 w-5 text-orange-600" />
          <h3 className="font-bold text-orange-900">Bright Outlook 朝阳职业</h3>
        </div>
        <p className="text-sm text-orange-800">
          参考 O*NET Bright Outlook，标记 2024-2025 高增长、快速扩张与新兴职业，帮你把目光投向正在变热的赛道。
        </p>
        <div className="flex flex-wrap gap-3 mt-3 text-xs">
          <span className="inline-flex items-center gap-1 text-red-700">🔥 高增长</span>
          <span className="inline-flex items-center gap-1 text-orange-700">⬆ 快速/稳定增长</span>
          <span className="inline-flex items-center gap-1 text-green-700">🆕 新兴</span>
          <span className="inline-flex items-center gap-1 text-ink-600">→ 平稳</span>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -tranink-y-1/2 h-4 w-4 text-ink-400" />
        <input
          type="text"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="筛选岗位名或标签..."
          className="w-full rounded-lg border border-paper-300 bg-white pl-9 pr-3 py-2 text-sm text-ink-800 placeholder:text-ink-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-100"
        />
      </div>

      {sorted.length === 0 ? (
        <EmptyState title="未匹配到朝阳职业" description="换个关键词试试" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {sorted.map((role) => (
            <div
              key={role.name}
              className="bg-white rounded-xl border border-paper-200 p-5 hover:shadow-md transition-shadow flex flex-col"
            >
              <div className="flex items-start justify-between mb-2 gap-2">
                <div className="min-w-0">
                  <h4 className="font-bold text-ink-800 text-lg">{role.name}</h4>
                  <p className="text-xs text-ink-500 mt-0.5">{role.desc}</p>
                </div>
                <BrightOutlookBadge role={role} />
              </div>

              <div className="mt-3 mb-4">
                <div className="flex items-center justify-between text-xs text-ink-500 mb-1">
                  <span>预计增长率</span>
                  <span className="font-medium" style={{ color: brightOutlookBarColors[role.color] }}>
                    +{role.growth}%
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-paper-100 overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(role.growth / maxGrowth) * 100}%`,
                      backgroundColor: brightOutlookBarColors[role.color],
                    }}
                  />
                </div>
              </div>

              <div className="mt-auto pt-3 border-t border-paper-100 flex items-center justify-between">
                <span className="text-xs text-ink-400">不确定是否适合？</span>
                <VirtualTrialButton role={role.name} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ===== Tab8: 薪资透视（按城市切片） =====
function SalarySliceBar({ data }: { data: SalarySlice }) {
  const parse = (s: string) => Number(s.replace("万", ""));
  const p25 = parse(data.p25);
  const p50 = parse(data.p50);
  const p75 = parse(data.p75);
  const p90 = parse(data.p90);
  const max = p90 || 1;
  const W = 480;
  const xOf = (v: number) => (v / max) * W;
  const wOf = (v1: number, v2: number) => ((v2 - v1) / max) * W;
  const segments = [
    { label: "P25", value: data.p25, v1: 0, v2: p25, color: "#dbeafe" },
    { label: "P50", value: data.p50, v1: p25, v2: p50, color: "#93c5fd" },
    { label: "P75", value: data.p75, v1: p50, v2: p75, color: "#3b82f6" },
    { label: "P90", value: data.p90, v1: p75, v2: p90, color: "#1d4ed8" },
  ];
  return (
    <div>
      <svg viewBox={`0 0 ${W} 40`} className="w-full" role="img" aria-label="薪资分布条">
        {segments.map((seg, i) => (
          <rect
            key={seg.label}
            x={xOf(seg.v1)}
            y={8}
            width={Math.max(0, wOf(seg.v1, seg.v2))}
            height={24}
            fill={seg.color}
            rx={i === 0 || i === segments.length - 1 ? 4 : 0}
          />
        ))}
      </svg>
      <div className="grid grid-cols-4 gap-2 mt-2">
        {segments.map((seg) => (
          <div key={seg.label} className="flex items-center gap-1.5 text-xs">
            <span className="h-2.5 w-2.5 rounded-sm shrink-0" style={{ backgroundColor: seg.color }} />
            <span className="text-ink-500">{seg.label}</span>
            <span className="font-medium text-ink-800">{seg.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Tab8SalarySlice() {
  const positions = Object.keys(SALARY_DATA);
  const [position, setPosition] = useState(positions[0]);
  const cities = Object.keys(SALARY_DATA[position]);
  const [city, setCity] = useState(cities[0]);
  const data = SALARY_DATA[position][city];
  const maxMed = Math.max(
    ...cities.map((c) => Number(SALARY_DATA[position][c].p50.replace("万", ""))),
  );

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-5 border border-green-200">
        <div className="flex items-center gap-2 mb-2">
          <DollarSign className="h-5 w-5 text-green-600" />
          <h3 className="font-bold text-green-900">薪资透视</h3>
        </div>
        <p className="text-sm text-green-800">
          参考 Glassdoor 真实薪资切片，按岗位 × 城市查看 P25 / P50 / P75 / P90 四分位分布，帮你校准期望薪资。
        </p>
      </div>

      <div className="bg-white rounded-xl border border-paper-200 p-5">
        <div className="grid gap-4 md:grid-cols-2 mb-5">
          <div>
            <label className="text-xs font-medium text-ink-500 mb-1.5 block">选择岗位</label>
            <select
              value={position}
              onChange={(e) => {
                setPosition(e.target.value);
                const c = Object.keys(SALARY_DATA[e.target.value]);
                if (!c.includes(city)) setCity(c[0]);
              }}
              className="w-full rounded-lg border border-paper-300 bg-white px-3 py-2 text-sm text-ink-800 focus:border-green-500 focus:outline-none focus:ring-2 focus:ring-green-100"
            >
              {positions.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-ink-500 mb-1.5 block">选择城市</label>
            <select
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="w-full rounded-lg border border-paper-300 bg-white px-3 py-2 text-sm text-ink-800 focus:border-green-500 focus:outline-none focus:ring-2 focus:ring-green-100"
            >
              {cities.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="rounded-lg bg-paper-50 p-4">
          <div className="flex items-baseline justify-between mb-3">
            <h4 className="font-bold text-ink-800">{position} · {city}</h4>
            <span className="text-sm text-ink-500">中位数 <span className="font-semibold text-green-600">{data.p50}</span></span>
          </div>
          <SalarySliceBar data={data} />
        </div>

        <div className="mt-5">
          <h4 className="text-sm font-medium text-ink-700 mb-2">{position} 各城市中位数对比</h4>
          <div className="space-y-2">
            {cities.map((c) => {
              const d = SALARY_DATA[position][c];
              const med = Number(d.p50.replace("万", ""));
              return (
                <div key={c} className="flex items-center gap-3 text-xs">
                  <span className="w-12 text-ink-600 shrink-0">{c}</span>
                  <div className="flex-1 h-3 rounded-full bg-paper-100 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-green-500"
                      style={{ width: `${(med / maxMed) * 100}%` }}
                    />
                  </div>
                  <span className={cn("w-12 text-right font-medium", c === city ? "text-green-600" : "text-ink-700")}>{d.p50}</span>
                </div>
              );
            })}
          </div>
        </div>

        <p className="text-xs text-ink-400 mt-5">数据来源：2024 招聘市场调研，仅供参考</p>
      </div>
    </div>
  );
}

// ===== 主页面 =====

export default function EmploymentPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <EmploymentPageContent />
    </Suspense>
  );
}

function EmploymentPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = searchParams.get("tab") || "intel";
  const current = tabs.find((t) => t.id === activeTab) || tabs[0];

  const handleTabChange = (id: string) => {
    router.push(`/employment?tab=${id}`);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* 页面标题 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-ink-800 mb-2">就业中心</h1>
        <p className="text-ink-500">公司情报 · 薪资查询 · 求职定位 · 就业数据 · 暗知识 · 面经库 · 灵感案例</p>
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-2 mb-8 border-b border-paper-200 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={cn(
                "flex items-center gap-2 px-6 py-3 font-medium transition-all border-b-2 whitespace-nowrap",
                activeTab === tab.id
                  ? `${tab.color} border-current`
                  : "text-ink-400 border-transparent hover:text-ink-600"
              )}
            >
              <Icon className="h-5 w-5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* 当前 Tab 描述 */}
      <div className="mb-6">
        <p className="text-sm text-ink-500">{current.desc}</p>
      </div>

      {/* Tab 内容区域 */}
      <div>
        {activeTab === "intel" && <Tab1Intel />}
        {activeTab === "salary" && <Tab2Salary />}
        {activeTab === "positioning" && <Tab3Positioning />}
        {activeTab === "employment" && <Tab4Employment />}
        {activeTab === "dark-knowledge" && <Tab5DarkKnowledge />}
        {activeTab === "interview" && <Tab6Interview />}
        {activeTab === "bright-outlook" && <Tab7BrightOutlook />}
        {activeTab === "salary-slice" && <Tab8SalarySlice />}
      </div>
    </div>
  );
}
