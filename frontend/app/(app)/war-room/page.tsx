"use client";

import { Suspense, useEffect, useState, useMemo, memo, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  GraduationCap,
  Briefcase,
  Landmark,
  Search,
  School as SchoolIcon,
  MapPin,
  Users,
  TrendingUp,
  AlertTriangle,
  Lightbulb,
  ChevronRight,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/lib/api/swr-config";
import { useToast } from "@/components/ui/toast";
import { LoadingState } from "@/components/ui/empty";
import type {
  IntelResponse,
  DarkKnowledgeResponse,
  PostIntelResponse,
  CivilServiceDarkKnowledgeResponse,
  Company,
  SalaryBenchmark,
} from "@/types";

type WarRoomTab = "grad" | "civil" | "career" | "interview";

export default function WarRoomPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <WarRoomPageContent />
    </Suspense>
  );
}

function WarRoomPageContent() {
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as WarRoomTab) || "grad";
  const [activeTab, setActiveTab] = useState<WarRoomTab>(
    ["grad", "civil", "career", "interview"].includes(initialTab) ? initialTab : "grad",
  );

  const tabs = [
    { id: "grad" as const, label: "考研作战室", icon: GraduationCap, color: "text-blue-500" },
    { id: "civil" as const, label: "考公作战室", icon: Landmark, color: "text-red-500" },
    { id: "career" as const, label: "求职作战室", icon: Briefcase, color: "text-green-500" },
    { id: "interview" as const, label: "面经库", icon: Briefcase, color: "text-amber-500" },
  ];

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-ink-800 mb-2">作战室</h1>
        <p className="text-ink-500">选择你的目标方向，获取精准情报和备考策略</p>
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-2 mb-8 border-b border-paper-200">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              data-testid={`${tab.id}-tab`}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-6 py-3 font-medium transition-all border-b-2",
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

      {/* 内容区域 */}
      <div className="mt-8">
        {activeTab === "grad" && <GradWarRoom />}
        {activeTab === "civil" && <CivilWarRoom />}
        {activeTab === "career" && <CareerWarRoom />}
        {activeTab === "interview" && <InterviewSection />}
      </div>
    </div>
  );
}

// ======================================================================
// 考研作战室
// ======================================================================

function GradWarRoom() {
  const toast = useToast();
  const [searchSchool, setSearchSchool] = useState("");
  const [searchMajor, setSearchMajor] = useState("");
  const [filterTier, setFilterTier] = useState("");
  const [activeStage, setActiveStage] = useState<string>("all");

  const intelParentRef = useRef<HTMLDivElement>(null);
  const darkKnowledgeParentRef = useRef<HTMLDivElement>(null);

  // SWR 替代原 useEffect+Promise.all：自动去重/缓存，全局已禁用 focus 重验证
  const { data: intelData, error: intelError, isLoading: intelLoading } = useApi<IntelResponse[]>(
    "/api/grad-intel/intel/public?limit=300",
    { fallbackData: [] },
  );
  const { data: darkData, error: darkError, isLoading: darkLoading } = useApi<any>(
    "/api/grad-intel/dark-knowledge/list",
    { fallbackData: { items: [] as DarkKnowledgeResponse[] } },
  );

  useEffect(() => {
    if (intelError) toast.push(intelError.message || "加载数据失败", "error");
  }, [intelError, toast]);
  useEffect(() => {
    if (darkError) toast.push(darkError.message || "加载数据失败", "error");
  }, [darkError, toast]);

  const intelList = intelData ?? [];
  const darkKnowledge: DarkKnowledgeResponse[] = useMemo(
    () => (Array.isArray(darkData) ? darkData : darkData?.items ?? []),
    [darkData],
  );
  const loading = intelLoading || darkLoading;

  const filteredIntel = useMemo(() => {
    return intelList.filter((item) => {
      if (searchSchool && !item.school_name.includes(searchSchool)) return false;
      if (searchMajor && !item.major_name.includes(searchMajor)) return false;
      if (filterTier && item.school_tier !== filterTier) return false;
      return true;
    });
  }, [intelList, searchSchool, searchMajor, filterTier]);

  const stages = useMemo(() => {
    const stageMap = new Map<string, number>();
    darkKnowledge.forEach((dk) => {
      stageMap.set(dk.stage, (stageMap.get(dk.stage) || 0) + 1);
    });
    const stageNames: Record<string, string> = {
      decision: "决策阶段",
      school_selection: "择校阶段",
      preparation: "备考阶段",
      exam: "初试后",
      retest: "复试阶段",
    };
    return Array.from(stageMap.entries()).map(([stage, count]) => ({
      stage,
      name: stageNames[stage] || stage,
      count,
    }));
  }, [darkKnowledge]);

  const filteredDarkKnowledge = useMemo(() => {
    if (activeStage === "all") return darkKnowledge;
    return darkKnowledge.filter((dk) => dk.stage === activeStage);
  }, [darkKnowledge, activeStage]);

  // 院校情报两列分组，用于虚拟滚动
  const intelRows = useMemo(() => {
    const rows: IntelResponse[][] = [];
    for (let i = 0; i < filteredIntel.length; i += 2) {
      rows.push(filteredIntel.slice(i, i + 2));
    }
    return rows;
  }, [filteredIntel]);

  const intelRowVirtualizer = useVirtualizer({
    count: intelRows.length,
    getScrollElement: () => intelParentRef.current,
    estimateSize: () => 220,
    overscan: 4,
  });

  const darkKnowledgeRowVirtualizer = useVirtualizer({
    count: filteredDarkKnowledge.length,
    getScrollElement: () => darkKnowledgeParentRef.current,
    estimateSize: () => 140,
    overscan: 4,
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  const tierStats = intelList.reduce(
    (acc, item) => {
      acc[item.school_tier] = (acc[item.school_tier] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <div className="space-y-6">
      {/* 头部统计 */}
      <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-xl p-6 border border-blue-200">
        <h2 className="text-2xl font-bold text-blue-900 mb-2">考研作战室</h2>
        <p className="text-blue-700 mb-4">覆盖 {intelList.length} 条院校专业情报 · {darkKnowledge.length} 条暗知识</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-white/70 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-blue-700">{tierStats["985"] || 0}</p>
            <p className="text-xs text-blue-600">985 情报</p>
          </div>
          <div className="bg-white/70 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-blue-700">{tierStats["211"] || 0}</p>
            <p className="text-xs text-blue-600">211 情报</p>
          </div>
          <div className="bg-white/70 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-blue-700">{tierStats["双一流"] || 0}</p>
            <p className="text-xs text-blue-600">双一流情报</p>
          </div>
          <div className="bg-white/70 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-blue-700">{darkKnowledge.length}</p>
            <p className="text-xs text-blue-600">暗知识条目</p>
          </div>
        </div>
      </div>

      {/* 搜索栏 */}
      <div className="bg-white rounded-lg p-4 border border-paper-200">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="flex-1">
            <label className="block text-xs font-medium text-ink-500 mb-1">院校名称</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-300" />
              <input
                type="text"
                value={searchSchool}
                onChange={(e) => setSearchSchool(e.target.value)}
                placeholder="如：清华大学"
                className="w-full rounded-lg border border-paper-200 pl-9 pr-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
              />
            </div>
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-ink-500 mb-1">专业名称</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-300" />
              <input
                type="text"
                value={searchMajor}
                onChange={(e) => setSearchMajor(e.target.value)}
                placeholder="如：计算机"
                className="w-full rounded-lg border border-paper-200 pl-9 pr-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
              />
            </div>
          </div>
          <div className="md:w-40">
            <label className="block text-xs font-medium text-ink-500 mb-1">院校层次</label>
            <select
              value={filterTier}
              onChange={(e) => setFilterTier(e.target.value)}
              className="w-full rounded-lg border border-paper-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
            >
              <option value="">全部</option>
              <option value="985">985</option>
              <option value="211">211</option>
              <option value="双一流">双一流</option>
              <option value="普通">普通</option>
            </select>
          </div>
        </div>
      </div>

      {/* 院校情报列表 */}
      <div>
        <h3 className="text-lg font-bold text-ink-800 mb-3 flex items-center gap-2">
          <SchoolIcon className="h-5 w-5 text-blue-500" />
          院校情报（{filteredIntel.length} 条）
        </h3>
        {filteredIntel.length === 0 ? (
          <div className="text-center py-10 text-ink-400">
            <SchoolIcon className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p>没有找到匹配的情报，试试调整搜索条件</p>
          </div>
        ) : (
          <div
            ref={intelParentRef}
            style={{ height: "600px", overflow: "auto" }}
            className="rounded-lg"
          >
            <div
              style={{
                height: `${intelRowVirtualizer.getTotalSize()}px`,
                position: "relative",
              }}
            >
              {intelRowVirtualizer.getVirtualItems().map((virtualRow) => {
                const rowItems = intelRows[virtualRow.index];
                return (
                  <div
                    key={`intel-row-${virtualRow.index}`}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                  >
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 px-0.5">
                      {rowItems.map((intel) => (
                        <IntelCardMemo key={intel.id} intel={intel} />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* 暗知识 */}
      <div>
        <h3 className="text-lg font-bold text-ink-800 mb-3 flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-amber-500" />
          考研暗知识（{darkKnowledge.length} 条）
        </h3>
        <div className="flex gap-2 mb-4 flex-wrap">
          <button
            onClick={() => setActiveStage("all")}
            className={cn(
              "px-3 py-1.5 rounded-full text-sm transition-colors",
              activeStage === "all"
                ? "bg-blue-600 text-white"
                : "bg-paper-100 text-ink-500 hover:bg-paper-200"
            )}
          >
            全部（{darkKnowledge.length}）
          </button>
          {stages.map((s) => (
            <button
              key={s.stage}
              onClick={() => setActiveStage(s.stage)}
              className={cn(
                "px-3 py-1.5 rounded-full text-sm transition-colors",
                activeStage === s.stage
                  ? "bg-blue-600 text-white"
                  : "bg-paper-100 text-ink-500 hover:bg-paper-200"
              )}
            >
              {s.name}（{s.count}）
            </button>
          ))}
        </div>
        {filteredDarkKnowledge.length === 0 ? (
          <div className="text-center py-10 text-ink-400">
            <Lightbulb className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p>该阶段暂无暗知识</p>
          </div>
        ) : (
          <div
            ref={darkKnowledgeParentRef}
            style={{ height: "600px", overflow: "auto" }}
            className="rounded-lg"
          >
            <div
              style={{
                height: `${darkKnowledgeRowVirtualizer.getTotalSize()}px`,
                position: "relative",
              }}
            >
              {darkKnowledgeRowVirtualizer.getVirtualItems().map((virtualRow) => {
                const dk = filteredDarkKnowledge[virtualRow.index];
                return (
                  <div
                    key={dk.id}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                  >
                    <DarkKnowledgeCardMemo dk={dk} color="blue" />
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function IntelCard({ intel }: { intel: IntelResponse }) {
  const [expanded, setExpanded] = useState(false);

  const discriminationLabel: Record<string, string> = {
    none: "不歧视",
    mild: "轻微歧视",
    moderate: "中度歧视",
    severe: "严重歧视",
    unknown: "未知",
  };

  const protectionLabel: Record<string, string> = {
    yes: "保护一志愿",
    partial: "部分保护",
    no: "不保护",
    unknown: "未知",
  };

  return (
    <div className="bg-white rounded-lg p-4 border border-paper-200 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <div>
          <h4 className="font-semibold text-ink-800">{intel.school_name}</h4>
          <p className="text-sm text-ink-500">{intel.major_name}</p>
        </div>
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700">
          {intel.school_tier}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs text-ink-600 mt-3">
        <div className="flex justify-between">
          <span>报录比</span>
          <span className="font-medium text-ink-800">{intel.admission_ratio || "—"}</span>
        </div>
        <div className="flex justify-between">
          <span>复试线</span>
          <span className="font-medium text-ink-800">{intel.score_line || "—"}</span>
        </div>
        <div className="flex justify-between">
          <span>推免占比</span>
          <span className="font-medium text-ink-800">{intel.push_ratio || "—"}</span>
        </div>
        <div className="flex justify-between">
          <span>统考名额</span>
          <span className="font-medium text-ink-800">{intel.actual_quota || "—"}</span>
        </div>
        <div className="flex justify-between">
          <span>学历歧视</span>
          <span className={cn(
            "font-medium",
            intel.background_discrimination === "severe" ? "text-red-600" :
            intel.background_discrimination === "moderate" ? "text-amber-600" :
            "text-green-600"
          )}>
            {discriminationLabel[intel.background_discrimination] || intel.background_discrimination}
          </span>
        </div>
        <div className="flex justify-between">
          <span>一志愿保护</span>
          <span className={cn(
            "font-medium",
            intel.first_choice_protection === "yes" ? "text-green-600" :
            intel.first_choice_protection === "no" ? "text-red-600" :
            "text-amber-600"
          )}>
            {protectionLabel[intel.first_choice_protection] || intel.first_choice_protection}
          </span>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-paper-100 space-y-2 text-xs">
          {intel.retest_weight && (
            <div className="flex justify-between">
              <span className="text-ink-500">复试占比</span>
              <span className="text-ink-700">{intel.retest_weight}</span>
            </div>
          )}
          {intel.retest_format && (
            <div className="flex justify-between">
              <span className="text-ink-500">复试形式</span>
              <span className="text-ink-700">{intel.retest_format}</span>
            </div>
          )}
          {intel.insider_notes && (
            <div className="bg-amber-50 rounded p-2 text-ink-600">
              <p className="font-medium text-amber-700 mb-1">内部消息</p>
              {intel.insider_notes}
            </div>
          )}
          {intel.tags && intel.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {intel.tags.map((tag, i) => (
                <span key={`${intel.id}-tag-${i}`} className="px-1.5 py-0.5 bg-paper-100 rounded text-[10px] text-ink-500">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-3 text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
      >
        {expanded ? "收起" : "查看详情"}
        <ChevronRight className={cn("h-3 w-3 transition-transform", expanded && "rotate-90")} />
      </button>
    </div>
  );
}
const IntelCardMemo = memo(IntelCard);

// ======================================================================
// 考公作战室
// ======================================================================

function CivilWarRoom() {
  const toast = useToast();
  const [searchRegion, setSearchRegion] = useState("");
  const [searchDept, setSearchDept] = useState("");
  const [filterTier, setFilterTier] = useState("");
  const [activeStage, setActiveStage] = useState<string>("all");

  const postParentRef = useRef<HTMLDivElement>(null);
  const darkKnowledgeParentRef = useRef<HTMLDivElement>(null);

  // SWR 替代原 useEffect+Promise.all
  const { data: postData, error: postError, isLoading: postLoading } = useApi<PostIntelResponse[]>(
    "/api/civil-service/post-intel/public?limit=200",
    { fallbackData: [] },
  );
  const { data: darkData, error: darkError, isLoading: darkLoading } = useApi<any>(
    "/api/civil-service/dark-knowledge",
    { fallbackData: [] },
  );

  useEffect(() => {
    if (postError) toast.push(postError.message || "加载数据失败", "error");
  }, [postError, toast]);
  useEffect(() => {
    if (darkError) toast.push(darkError.message || "加载数据失败", "error");
  }, [darkError, toast]);

  const postIntel = postData ?? [];
  const darkKnowledge: CivilServiceDarkKnowledgeResponse[] = useMemo(
    () => (Array.isArray(darkData) ? darkData : darkData?.items ?? []),
    [darkData],
  );
  const loading = postLoading || darkLoading;

  const filteredPosts = useMemo(() => {
    return postIntel.filter((item) => {
      if (searchRegion && !item.region.includes(searchRegion)) return false;
      if (searchDept && !item.department.includes(searchDept)) return false;
      if (filterTier && item.department_tier !== filterTier) return false;
      return true;
    });
  }, [postIntel, searchRegion, searchDept, filterTier]);

  const stages = useMemo(() => {
    const stageMap = new Map<string, number>();
    darkKnowledge.forEach((dk) => {
      stageMap.set(dk.stage, (stageMap.get(dk.stage) || 0) + 1);
    });
    const stageNames: Record<string, string> = {
      decision: "决策阶段",
      position_selection: "选岗阶段",
      written_exam: "笔试阶段",
      interview: "面试阶段",
      physical: "体检政审",
      onboarding: "入职适应",
    };
    return Array.from(stageMap.entries()).map(([stage, count]) => ({
      stage,
      name: stageNames[stage] || stage,
      count,
    }));
  }, [darkKnowledge]);

  const filteredDarkKnowledge = useMemo(() => {
    if (activeStage === "all") return darkKnowledge;
    return darkKnowledge.filter((dk) => dk.stage === activeStage);
  }, [darkKnowledge, activeStage]);

  const postRows = useMemo(() => {
    const rows: PostIntelResponse[][] = [];
    for (let i = 0; i < filteredPosts.length; i += 2) {
      rows.push(filteredPosts.slice(i, i + 2));
    }
    return rows;
  }, [filteredPosts]);

  const postRowVirtualizer = useVirtualizer({
    count: postRows.length,
    getScrollElement: () => postParentRef.current,
    estimateSize: () => 240,
    overscan: 4,
  });

  const darkKnowledgeRowVirtualizer = useVirtualizer({
    count: filteredDarkKnowledge.length,
    getScrollElement: () => darkKnowledgeParentRef.current,
    estimateSize: () => 140,
    overscan: 4,
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-red-500" />
      </div>
    );
  }

  const tierStats = postIntel.reduce(
    (acc, item) => {
      const tier = item.department_tier || "其他";
      acc[tier] = (acc[tier] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <div className="space-y-6">
      {/* 头部统计 */}
      <div className="bg-gradient-to-r from-red-50 to-red-100 rounded-xl p-6 border border-red-200">
        <h2 className="text-2xl font-bold text-red-900 mb-2">考公作战室</h2>
        <p className="text-red-700 mb-4">覆盖 {postIntel.length} 条岗位情报 · {darkKnowledge.length} 条暗知识</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-white/70 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-red-700">{tierStats["中央部委"] || 0}</p>
            <p className="text-xs text-red-600">中央部委</p>
          </div>
          <div className="bg-white/70 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-red-700">{tierStats["省级机关"] || 0}</p>
            <p className="text-xs text-red-600">省级机关</p>
          </div>
          <div className="bg-white/70 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-red-700">{tierStats["市级机关"] || 0}</p>
            <p className="text-xs text-red-600">市级机关</p>
          </div>
          <div className="bg-white/70 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-red-700">{tierStats["县区基层"] || 0}</p>
            <p className="text-xs text-red-600">县区基层</p>
          </div>
        </div>
      </div>

      {/* 搜索栏 */}
      <div className="bg-white rounded-lg p-4 border border-paper-200">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="flex-1">
            <label className="block text-xs font-medium text-ink-500 mb-1">地区</label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-300" />
              <input
                type="text"
                value={searchRegion}
                onChange={(e) => setSearchRegion(e.target.value)}
                placeholder="如：北京"
                className="w-full rounded-lg border border-paper-200 pl-9 pr-3 py-2 text-sm focus:border-red-400 focus:outline-none"
              />
            </div>
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-ink-500 mb-1">部门</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-300" />
              <input
                type="text"
                value={searchDept}
                onChange={(e) => setSearchDept(e.target.value)}
                placeholder="如：税务局"
                className="w-full rounded-lg border border-paper-200 pl-9 pr-3 py-2 text-sm focus:border-red-400 focus:outline-none"
              />
            </div>
          </div>
          <div className="md:w-40">
            <label className="block text-xs font-medium text-ink-500 mb-1">机关层级</label>
            <select
              value={filterTier}
              onChange={(e) => setFilterTier(e.target.value)}
              className="w-full rounded-lg border border-paper-200 px-3 py-2 text-sm focus:border-red-400 focus:outline-none"
            >
              <option value="">全部</option>
              <option value="中央部委">中央部委</option>
              <option value="省级机关">省级机关</option>
              <option value="市级机关">市级机关</option>
              <option value="县区基层">县区基层</option>
            </select>
          </div>
        </div>
      </div>

      {/* 岗位情报列表 */}
      <div>
        <h3 className="text-lg font-bold text-ink-800 mb-3 flex items-center gap-2">
          <Landmark className="h-5 w-5 text-red-500" />
          岗位情报（{filteredPosts.length} 条）
        </h3>
        {filteredPosts.length === 0 ? (
          <div className="text-center py-10 text-ink-400">
            <Landmark className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p>没有找到匹配的岗位情报，试试调整搜索条件</p>
          </div>
        ) : (
          <div
            ref={postParentRef}
            style={{ height: "600px", overflow: "auto" }}
            className="rounded-lg"
          >
            <div
              style={{
                height: `${postRowVirtualizer.getTotalSize()}px`,
                position: "relative",
              }}
            >
              {postRowVirtualizer.getVirtualItems().map((virtualRow) => {
                const rowItems = postRows[virtualRow.index];
                return (
                  <div
                    key={`post-row-${virtualRow.index}`}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                  >
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 px-0.5">
                      {rowItems.map((post) => (
                        <PostIntelCardMemo key={post.id} post={post} />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* 暗知识 */}
      <div>
        <h3 className="text-lg font-bold text-ink-800 mb-3 flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-amber-500" />
          考公暗知识（{darkKnowledge.length} 条）
        </h3>
        <div className="flex gap-2 mb-4 flex-wrap">
          <button
            onClick={() => setActiveStage("all")}
            className={cn(
              "px-3 py-1.5 rounded-full text-sm transition-colors",
              activeStage === "all"
                ? "bg-red-600 text-white"
                : "bg-paper-100 text-ink-500 hover:bg-paper-200"
            )}
          >
            全部（{darkKnowledge.length}）
          </button>
          {stages.map((s) => (
            <button
              key={s.stage}
              onClick={() => setActiveStage(s.stage)}
              className={cn(
                "px-3 py-1.5 rounded-full text-sm transition-colors",
                activeStage === s.stage
                  ? "bg-red-600 text-white"
                  : "bg-paper-100 text-ink-500 hover:bg-paper-200"
              )}
            >
              {s.name}（{s.count}）
            </button>
          ))}
        </div>
        {filteredDarkKnowledge.length === 0 ? (
          <div className="text-center py-10 text-ink-400">
            <Lightbulb className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p>该阶段暂无暗知识</p>
          </div>
        ) : (
          <div
            ref={darkKnowledgeParentRef}
            style={{ height: "600px", overflow: "auto" }}
            className="rounded-lg"
          >
            <div
              style={{
                height: `${darkKnowledgeRowVirtualizer.getTotalSize()}px`,
                position: "relative",
              }}
            >
              {darkKnowledgeRowVirtualizer.getVirtualItems().map((virtualRow) => {
                const dk = filteredDarkKnowledge[virtualRow.index];
                return (
                  <div
                    key={dk.id}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                  >
                    <CivilDarkKnowledgeCardMemo dk={dk} />
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function PostIntelCard({ post }: { post: PostIntelResponse }) {
  const [expanded, setExpanded] = useState(false);

  const competitionLabel: Record<string, string> = {
    low: "竞争较小",
    medium: "竞争适中",
    high: "竞争激烈",
    extreme: "竞争极端",
    unknown: "未知",
  };

  const treatmentLabel: Record<string, string> = {
    low: "待遇一般",
    medium: "待遇中等",
    high: "待遇优厚",
    unknown: "未知",
  };

  return (
    <div className="bg-white rounded-lg p-4 border border-paper-200 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <div>
          <h4 className="font-semibold text-ink-800">{post.department}</h4>
          <p className="text-sm text-ink-500">{post.post_name}</p>
        </div>
        {post.department_tier && (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700">
            {post.department_tier}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2 text-xs text-ink-500 mb-3">
        <MapPin className="h-3 w-3" />
        <span>{post.region}</span>
        <span>·</span>
        <span>{post.exam_type}</span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs text-ink-600">
        <div className="flex justify-between">
          <span>报录比</span>
          <span className="font-medium text-ink-800">{post.admission_ratio || "—"}</span>
        </div>
        <div className="flex justify-between">
          <span>进面分</span>
          <span className="font-medium text-ink-800">{post.cutoff_score || "—"}</span>
        </div>
        <div className="flex justify-between">
          <span>竞争程度</span>
          <span className={cn(
            "font-medium",
            post.real_competition === "extreme" || post.real_competition === "high" ? "text-red-600" :
            post.real_competition === "medium" ? "text-amber-600" :
            "text-green-600"
          )}>
            {competitionLabel[post.real_competition] || post.real_competition}
          </span>
        </div>
        <div className="flex justify-between">
          <span>待遇水平</span>
          <span className="font-medium text-green-600">
            {treatmentLabel[post.treatment_level] || post.treatment_level}
          </span>
        </div>
        {post.salary_estimate && (
          <div className="flex justify-between">
            <span>薪资范围</span>
            <span className="font-medium text-ink-800">{post.salary_estimate}</span>
          </div>
        )}
        <div className="flex justify-between">
          <span>服务期</span>
          <span className="font-medium text-ink-800">{post.service_period || "—"}</span>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-paper-100 space-y-2 text-xs">
          {post.work_content && (
            <div>
              <p className="font-medium text-ink-700 mb-1">工作内容</p>
              <p className="text-ink-500">{post.work_content}</p>
            </div>
          )}
          {post.insider_notes && (
            <div className="bg-amber-50 rounded p-2 text-ink-600">
              <p className="font-medium text-amber-700 mb-1">内部消息</p>
              {post.insider_notes}
            </div>
          )}
          {post.risk_warnings && post.risk_warnings.length > 0 && (
            <div className="bg-red-50 rounded p-2">
              <p className="font-medium text-red-700 mb-1 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                风险提示
              </p>
              <ul className="text-red-600 space-y-0.5">
                {post.risk_warnings.map((w, i) => (
                  <li key={`${post.id}-warn-${i}`}>· {w}</li>
                ))}
              </ul>
            </div>
          )}
          {post.tags && post.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {post.tags.map((tag, i) => (
                <span key={`${post.id}-tag-${i}`} className="px-1.5 py-0.5 bg-paper-100 rounded text-[10px] text-ink-500">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-3 text-xs text-red-600 hover:text-red-700 flex items-center gap-1"
      >
        {expanded ? "收起" : "查看详情"}
        <ChevronRight className={cn("h-3 w-3 transition-transform", expanded && "rotate-90")} />
      </button>
    </div>
  );
}
const PostIntelCardMemo = memo(PostIntelCard);

// ======================================================================
// 求职作战室
// ======================================================================

function CareerWarRoom() {
  const toast = useToast();
  const [searchCompany, setSearchCompany] = useState("");
  const [filterIndustry, setFilterIndustry] = useState("");

  const companyParentRef = useRef<HTMLDivElement>(null);
  const salaryParentRef = useRef<HTMLDivElement>(null);

  // SWR 替代原 useEffect+Promise.all
  const { data: companiesData, error: companiesError, isLoading: companiesLoading } = useApi<Company[]>(
    "/api/companies",
    { fallbackData: [] },
  );
  const { data: salariesData, error: salariesError, isLoading: salariesLoading } = useApi<SalaryBenchmark[]>(
    "/api/salary-benchmarks",
    { fallbackData: [] },
  );

  useEffect(() => {
    if (companiesError) toast.push(companiesError.message || "加载数据失败", "error");
  }, [companiesError, toast]);
  useEffect(() => {
    if (salariesError) toast.push(salariesError.message || "加载数据失败", "error");
  }, [salariesError, toast]);

  const companies = companiesData ?? [];
  const salaries = salariesData ?? [];
  const loading = companiesLoading || salariesLoading;

  const industries = useMemo(() => {
    const set = new Set<string>();
    companies.forEach((c) => set.add(c.industry));
    return Array.from(set).sort();
  }, [companies]);

  const filteredCompanies = useMemo(() => {
    return companies.filter((c) => {
      if (searchCompany && !c.name.includes(searchCompany)) return false;
      if (filterIndustry && c.industry !== filterIndustry) return false;
      return true;
    });
  }, [companies, searchCompany, filterIndustry]);

  const filteredSalaries = useMemo(() => {
    return salaries.filter((s) => {
      if (searchCompany && !s.company.includes(searchCompany)) return false;
      return true;
    });
  }, [salaries, searchCompany]);

  // 公司卡片按 3 列分组
  const companyRows = useMemo(() => {
    const rows: Company[][] = [];
    for (let i = 0; i < filteredCompanies.length; i += 3) {
      rows.push(filteredCompanies.slice(i, i + 3));
    }
    return rows;
  }, [filteredCompanies]);

  const companyRowVirtualizer = useVirtualizer({
    count: companyRows.length,
    getScrollElement: () => companyParentRef.current,
    estimateSize: () => 200,
    overscan: 4,
  });

  const salaryRowVirtualizer = useVirtualizer({
    count: filteredSalaries.length,
    getScrollElement: () => salaryParentRef.current,
    estimateSize: () => 52,
    overscan: 8,
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-green-500" />
      </div>
    );
  }

  const industryStats = companies.reduce(
    (acc, c) => {
      acc[c.industry] = (acc[c.industry] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <div className="space-y-6">
      {/* 头部统计 */}
      <div className="bg-gradient-to-r from-green-50 to-green-100 rounded-xl p-6 border border-green-200">
        <h2 className="text-2xl font-bold text-green-900 mb-2">求职作战室</h2>
        <p className="text-green-700 mb-4">覆盖 {companies.length} 家公司 · {salaries.length} 条薪资记录</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(industryStats).slice(0, 4).map(([industry, count]) => (
            <div key={industry} className="bg-white/70 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-green-700">{count}</p>
              <p className="text-xs text-green-600 truncate">{industry}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 搜索栏 */}
      <div className="bg-white rounded-lg p-4 border border-paper-200">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="flex-1">
            <label className="block text-xs font-medium text-ink-500 mb-1">公司名称</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-300" />
              <input
                type="text"
                value={searchCompany}
                onChange={(e) => setSearchCompany(e.target.value)}
                placeholder="如：腾讯"
                data-testid="company-input"
                className="w-full rounded-lg border border-paper-200 pl-9 pr-3 py-2 text-sm focus:border-green-400 focus:outline-none"
              />
            </div>
          </div>
          <div className="md:w-48">
            <label className="block text-xs font-medium text-ink-500 mb-1">行业</label>
            <select
              value={filterIndustry}
              onChange={(e) => setFilterIndustry(e.target.value)}
              data-testid="industry-select"
              className="w-full rounded-lg border border-paper-200 px-3 py-2 text-sm focus:border-green-400 focus:outline-none"
            >
              <option value="">全部</option>
              {industries.map((ind) => (
                <option key={ind} value={ind}>{ind}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* 公司列表 */}
      <div>
        <h3 className="text-lg font-bold text-ink-800 mb-3 flex items-center gap-2">
          <Briefcase className="h-5 w-5 text-green-500" />
          公司列表（{filteredCompanies.length} 家）
        </h3>
        {filteredCompanies.length === 0 ? (
          <div className="text-center py-10 text-ink-400">
            <Briefcase className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p>没有找到匹配的公司</p>
          </div>
        ) : (
          <div
            ref={companyParentRef}
            style={{ height: "600px", overflow: "auto" }}
            className="rounded-lg"
          >
            <div
              style={{
                height: `${companyRowVirtualizer.getTotalSize()}px`,
                position: "relative",
              }}
            >
              {companyRowVirtualizer.getVirtualItems().map((virtualRow) => {
                const rowItems = companyRows[virtualRow.index];
                return (
                  <div
                    key={`company-row-${virtualRow.index}`}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                  >
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 px-0.5">
                      {rowItems.map((c) => (
                        <CompanyCardMemo key={c.id} company={c} />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* 薪资基准 */}
      <div>
        <h3 className="text-lg font-bold text-ink-800 mb-3 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-green-500" />
          薪资基准（{filteredSalaries.length} 条）
        </h3>
        {filteredSalaries.length === 0 ? (
          <div className="text-center py-10 text-ink-400">
            <TrendingUp className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p>没有找到匹配的薪资数据</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-paper-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-paper-50 border-b border-paper-200 sticky top-0">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-ink-600">公司</th>
                  <th className="text-left px-4 py-3 font-medium text-ink-600">岗位</th>
                  <th className="text-left px-4 py-3 font-medium text-ink-600">城市</th>
                  <th className="text-left px-4 py-3 font-medium text-ink-600">经验</th>
                  <th className="text-right px-4 py-3 font-medium text-ink-600">薪资中位数</th>
                  <th className="text-right px-4 py-3 font-medium text-ink-600">范围</th>
                </tr>
              </thead>
            </table>
            <div ref={salaryParentRef} style={{ height: "500px", overflow: "auto" }}>
              <div
                style={{
                  height: `${salaryRowVirtualizer.getTotalSize()}px`,
                  position: "relative",
                }}
              >
                <table className="w-full text-sm">
                  <tbody>
                    {salaryRowVirtualizer.getVirtualItems().map((virtualRow) => {
                      const s = filteredSalaries[virtualRow.index];
                      return (
                        <tr
                          key={s.id}
                          className="hover:bg-paper-50"
                          style={{
                            position: "absolute",
                            top: 0,
                            left: 0,
                            width: "100%",
                            transform: `translateY(${virtualRow.start}px)`,
                            display: "table-row",
                          }}
                        >
                          <td className="px-4 py-3 text-ink-800 font-medium">{s.company}</td>
                          <td className="px-4 py-3 text-ink-600">{s.position}</td>
                          <td className="px-4 py-3 text-ink-500">{s.city || "—"}</td>
                          <td className="px-4 py-3 text-ink-500">{s.experience_level}</td>
                          <td className="px-4 py-3 text-right font-semibold text-green-700">
                            {s.salary_median}k
                          </td>
                          <td className="px-4 py-3 text-right text-ink-500 text-xs">
                            {s.salary_min}-{s.salary_max}k
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function CompanyCard({ company: c }: { company: Company }) {
  return (
    <div className="bg-white rounded-lg p-4 border border-paper-200 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-semibold text-ink-800">{c.name}</h4>
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700">
          {c.industry}
        </span>
      </div>
      <div className="text-xs text-ink-500 space-y-1">
        <div className="flex justify-between">
          <span>规模</span>
          <span className="text-ink-700">{c.size || "—"}</span>
        </div>
        {c.headquarters && (
          <div className="flex justify-between">
            <span>总部</span>
            <span className="text-ink-700">{c.headquarters}</span>
          </div>
        )}
        {c.stage && (
          <div className="flex justify-between">
            <span>阶段</span>
            <span className="text-ink-700">{c.stage}</span>
          </div>
        )}
      </div>
      {c.description && (
        <p className="mt-2 text-xs text-ink-400 line-clamp-2">{c.description}</p>
      )}
    </div>
  );
}
const CompanyCardMemo = memo(CompanyCard);

// ======================================================================
// 面经库
// ======================================================================

function InterviewSection() {
  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl p-6 border border-amber-200">
        <h2 className="text-2xl font-bold text-amber-900 mb-2">面经库</h2>
        <p className="text-amber-700 mb-4">
          匿名分享面试经验，了解企业面试的真实侧重点
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <div className="bg-white/70 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-amber-700">200+</p>
            <p className="text-xs text-amber-600">面试样本</p>
          </div>
          <div className="bg-white/70 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-amber-700">50+</p>
            <p className="text-xs text-amber-600">覆盖公司</p>
          </div>
          <div className="bg-white/70 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-amber-700">100+</p>
            <p className="text-xs text-amber-600">覆盖岗位</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl p-6 border border-paper-200">
        <div className="text-center py-8">
          <Briefcase className="h-16 w-16 mx-auto mb-4 text-amber-400 opacity-50" />
          <h3 className="text-xl font-bold text-ink-800 mb-2">查看完整面经库</h3>
          <p className="text-ink-500 mb-6">
            提交面试经验，查看公司面试维度分析，获取面试准备建议
          </p>
          <Link
            href="/interview"
            className="inline-flex items-center gap-2 px-6 py-3 bg-amber-500 text-white rounded-lg font-medium hover:bg-amber-600 transition-colors"
          >
            前往面经库
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}

// ======================================================================
// 暗知识卡片
// ======================================================================

function DarkKnowledgeCard({ dk }: { dk: DarkKnowledgeResponse; color: string }) {
  const [expanded, setExpanded] = useState(false);

  const importanceColor: Record<string, string> = {
    critical: "bg-red-100 text-red-700",
    high: "bg-amber-100 text-amber-700",
    medium: "bg-blue-100 text-blue-700",
  };

  return (
    <div className="bg-white rounded-lg p-4 border border-paper-200">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-ink-400">{dk.category}</span>
            <span className={cn(
              "px-1.5 py-0.5 rounded text-[10px] font-medium",
              importanceColor[dk.importance] || "bg-paper-100 text-ink-500"
            )}>
              {dk.importance === "critical" ? "关键" : dk.importance === "high" ? "重要" : "中等"}
            </span>
          </div>
          <h4 className="font-semibold text-ink-800">{dk.title}</h4>
        </div>
      </div>

      <p className="text-sm text-ink-600 leading-relaxed">{dk.content}</p>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-paper-100 space-y-2 text-sm">
          {dk.common_misconception && (
            <div className="bg-red-50 rounded p-2">
              <p className="font-medium text-red-700 mb-1 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                常见误区
              </p>
              <p className="text-red-600">{dk.common_misconception}</p>
            </div>
          )}
          {dk.actionable_advice && (
            <div className="bg-green-50 rounded p-2">
              <p className="font-medium text-green-700 mb-1 flex items-center gap-1">
                <Lightbulb className="h-3 w-3" />
                行动建议
              </p>
              <p className="text-green-600">{dk.actionable_advice}</p>
            </div>
          )}
          {dk.verification_method && (
            <div className="bg-blue-50 rounded p-2">
              <p className="font-medium text-blue-700 mb-1">验证方法</p>
              <p className="text-blue-600">{dk.verification_method}</p>
            </div>
          )}
        </div>
      )}

      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-3 text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
      >
        {expanded ? "收起" : "查看详情"}
        <ChevronRight className={cn("h-3 w-3 transition-transform", expanded && "rotate-90")} />
      </button>
    </div>
  );
}
const DarkKnowledgeCardMemo = memo(DarkKnowledgeCard);

function CivilDarkKnowledgeCard({ dk }: { dk: CivilServiceDarkKnowledgeResponse }) {
  const [expanded, setExpanded] = useState(false);

  const importanceColor: Record<string, string> = {
    critical: "bg-red-100 text-red-700",
    high: "bg-amber-100 text-amber-700",
    medium: "bg-blue-100 text-blue-700",
    low: "bg-paper-100 text-ink-500",
  };

  return (
    <div className="bg-white rounded-lg p-4 border border-paper-200">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-ink-400">{dk.category}</span>
            <span className={cn(
              "px-1.5 py-0.5 rounded text-[10px] font-medium",
              importanceColor[dk.importance] || "bg-paper-100 text-ink-500"
            )}>
              {dk.importance === "critical" ? "关键" : dk.importance === "high" ? "重要" : dk.importance === "medium" ? "中等" : "低"}
            </span>
          </div>
          <h4 className="font-semibold text-ink-800">{dk.title}</h4>
        </div>
      </div>

      <p className="text-sm text-ink-600 leading-relaxed">{dk.content}</p>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-paper-100 space-y-2 text-sm">
          {dk.common_misconception && (
            <div className="bg-red-50 rounded p-2">
              <p className="font-medium text-red-700 mb-1 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                常见误区
              </p>
              <p className="text-red-600">{dk.common_misconception}</p>
            </div>
          )}
          {dk.actionable_advice && (
            <div className="bg-green-50 rounded p-2">
              <p className="font-medium text-green-700 mb-1 flex items-center gap-1">
                <Lightbulb className="h-3 w-3" />
                行动建议
              </p>
              <p className="text-green-600">{dk.actionable_advice}</p>
            </div>
          )}
          {dk.verification_method && (
            <div className="bg-blue-50 rounded p-2">
              <p className="font-medium text-blue-700 mb-1">验证方法</p>
              <p className="text-blue-600">{dk.verification_method}</p>
            </div>
          )}
        </div>
      )}

      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-3 text-xs text-red-600 hover:text-red-700 flex items-center gap-1"
      >
        {expanded ? "收起" : "查看详情"}
        <ChevronRight className={cn("h-3 w-3 transition-transform", expanded && "rotate-90")} />
      </button>
    </div>
  );
}
const CivilDarkKnowledgeCardMemo = memo(CivilDarkKnowledgeCard);
