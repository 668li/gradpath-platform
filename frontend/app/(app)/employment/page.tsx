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
  { id: "intel", label: "公司情报", icon: Building2, color: "text-blue-500", desc: "查看你保存的公司情报，了解加班强度、裁员风险、晋升前景等关键信息" },
  { id: "salary", label: "薪资查询", icon: DollarSign, color: "text-green-500", desc: "查询各公司岗位薪资数据，对比分析薪资分布" },
  { id: "positioning", label: "求职定位", icon: Target, color: "text-purple-500", desc: "基于你的背景进行竞争力评估，获取冲刺/目标/保底公司推荐" },
  { id: "employment", label: "就业数据", icon: BarChart3, color: "text-amber-500", desc: "查看各高校就业率、行业分布、去向统计等数据" },
  { id: "dark-knowledge", label: "暗知识", icon: Lightbulb, color: "text-rose-500", desc: "求职过程中那些没人告诉你的关键经验与教训" },
  { id: "interview", label: "面经库", icon: MessageSquare, color: "text-cyan-500", desc: "海量面试经验分享，助你充分准备每一场面试" },
];

// ===== 标签颜色映射 =====
const overtimeColors: Record<string, string> = {
  none: "bg-green-100 text-green-700",
  mild: "bg-blue-100 text-blue-700",
  moderate: "bg-amber-100 text-amber-700",
  severe: "bg-red-100 text-red-700",
  unknown: "bg-gray-100 text-gray-500",
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
  unknown: "bg-gray-100 text-gray-500",
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
  unknown: "bg-gray-100 text-gray-500",
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
        title="暂无公司情报"
        description="在求职作战室查询并保存公司情报后，可在此查看"
        action={
          <a href="/war-room" className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:opacity-90">
            前往求职作战室
            <ChevronRight className="h-4 w-4" />
          </a>
        }
      />
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {list.map((intel) => (
        <div key={intel.id} className="bg-white rounded-xl border border-paper-200 p-5 hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="font-bold text-ink-800 text-lg">{intel.company_name}</h3>
              <p className="text-sm text-ink-500">{intel.position_name} · {intel.industry}</p>
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

          {intel.risk_warnings.length > 0 && (
            <div className="mt-3 flex items-start gap-2 text-sm text-amber-600">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{intel.risk_warnings[0]}</span>
            </div>
          )}
        </div>
      ))}
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
    return Object.entries(grouped).map(([position, data]) => ({
      position,
      min: data.min,
      max: data.max,
      median: Math.round(data.median),
    }));
  }, [salaries]);

  if (isLoading) return <ListSkeleton count={3} />;

  if (salaries.length === 0) {
    return (
      <EmptyState
        title="暂无薪资数据"
        description="系统正在持续收集薪资数据，请稍后查看"
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
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-400" />
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
          <h3 className="font-bold text-ink-800 mb-4">岗位薪资分布（单位：k）</h3>
          <ResponsiveContainer width="100%" height={300}>
            <ReBarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={SALARY_CHART_GRID_COLOR} />
              <XAxis dataKey="position" tick={SALARY_CHART_TICK} />
              <YAxis tick={SALARY_CHART_TICK} />
              <Tooltip
                contentStyle={SALARY_CHART_TOOLTIP_STYLE}
                formatter={(value: number) => [`${value}k`, ""]}
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

// ===== 薪资表格虚拟滚动组件 =====
function SalaryTable({
  salaries,
  totalCount,
}: {
  salaries: SalaryBenchmark[];
  totalCount: number;
}) {
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
                    <td className="px-4 py-3 text-ink-600">{s.position}</td>
                    <td className="px-4 py-3 text-ink-600">{s.city || "-"}</td>
                    <td className="px-4 py-3 text-ink-600">{s.experience_level}</td>
                    <td className="px-4 py-3 text-right text-ink-800">{s.salary_min}-{s.salary_max}k</td>
                    <td className="px-4 py-3 text-right font-medium text-green-600">{s.salary_median}k</td>
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
        title="暂无求职定位"
        description="完成求职定位评估，获取个性化竞争力分析和公司推荐"
        action={
          <a href="/war-room" className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:opacity-90">
            开始求职定位评估
            <ChevronRight className="h-4 w-4" />
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
        <p className="text-ink-500">公司情报 · 薪资查询 · 求职定位 · 就业数据 · 暗知识 · 面经库</p>
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
      </div>
    </div>
  );
}
