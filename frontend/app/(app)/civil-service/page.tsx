"use client";

import { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Target,
  Wrench,
  AlertTriangle,
  ChevronRight,
  Star,
  Clock,
  Sparkles,
  CalendarRange,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { civilServiceIntelApi } from "@/lib/api/ai";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { ExamTimelineTab } from "@/components/civil-service/exam-timeline";
import type {
  CivilServicePositioningResponse,
} from "@/types";

const tabs = [
  { id: "positioning", label: "考公定位", icon: Target, color: "text-purple-500" },
  { id: "tools", label: "备考工具", icon: Wrench, color: "text-green-500" },
  { id: "timeline", label: "考试流程", icon: CalendarRange, color: "text-blue-500" },
];



function PositioningContent({ data }: { data: CivilServicePositioningResponse | null }) {
  if (!data) {
    return (
      <EmptyState
        title="暂无考公定位数据"
        description="完成考公定位评估后，系统将为你生成竞争力评分和岗位推荐"
        action={
          <a
            href="/civil-service/positioning"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-purple-600 text-white font-medium hover:opacity-90 transition-opacity"
          >
            开始考公定位评估
            <ChevronRight className="h-4 w-4" />
          </a>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* 竞争力评分 */}
      {data.competitiveness_score != null && (
        <div className="rounded-xl border border-paper-200 bg-white p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-50">
              <Star className="h-6 w-6 text-purple-500" />
            </div>
            <div>
              <h3 className="font-display font-bold text-ink-800">竞争力评分</h3>
              <p className="text-sm text-ink-400">基于你的综合条件评估</p>
            </div>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-4xl font-bold text-purple-600">{data.competitiveness_score}</span>
            <span className="text-lg text-ink-400">/100</span>
          </div>
          {data.ai_assessment && (
            <p className="mt-3 text-sm text-ink-500 leading-relaxed">{data.ai_assessment}</p>
          )}
        </div>
      )}

      {/* 岗位推荐 */}
      {([
        { label: "冲刺岗位", posts: data.reach_posts, color: "border-red-200 bg-red-50/50" },
        { label: "目标岗位", posts: data.target_posts, color: "border-blue-200 bg-blue-50/50" },
        { label: "保底岗位", posts: data.safety_posts, color: "border-green-200 bg-green-50/50" },
      ] as const).map((group) =>
        group.posts.length > 0 && (
          <div key={group.label} className={cn("rounded-xl border p-5", group.color)}>
            <h4 className="font-display font-bold text-ink-800 mb-3">{group.label}</h4>
            <div className="space-y-2">
              {group.posts.map((post, i) => (
                <div
                  key={`${post.region}-${post.department}-${i}`}
                  className="flex items-center justify-between rounded-lg bg-white/80 px-4 py-3 border border-paper-100"
                >
                  <div>
                    <p className="font-medium text-ink-800">
                      {post.region} · {post.department} · {post.post}
                    </p>
                    <p className="text-sm text-ink-400 mt-0.5">{post.reason}</p>
                  </div>
                  <span className="text-sm font-medium text-ink-500">{Math.round(post.probability * 100)}%</span>
                </div>
              ))}
            </div>
          </div>
        )
      )}

      {/* 选调资格 */}
      {data.eligible_for_xuandiao && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 flex items-center gap-3">
          <Sparkles className="h-5 w-5 text-amber-500 shrink-0" />
          <p className="text-sm text-amber-800">你符合选调生报名条件</p>
        </div>
      )}
    </div>
  );
}

function ToolsContent({ positioning }: { positioning: CivilServicePositioningResponse | null }) {
  if (!positioning) {
    return (
      <EmptyState
        title="完成考公定位后自动生成"
        description="备考时间线和风险提示将根据你的定位评估自动生成"
        action={
          <a
            href="/civil-service/positioning"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-purple-600 text-white font-medium hover:opacity-90 transition-opacity"
          >
            前往考公定位
            <ChevronRight className="h-4 w-4" />
          </a>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* 备考时间线 */}
      {positioning.preparation_timeline && (
        <div className="rounded-xl border border-paper-200 bg-white p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-green-50">
              <Clock className="h-5 w-5 text-green-500" />
            </div>
            <h3 className="font-display font-bold text-ink-800">备考时间线</h3>
          </div>
          <div className="text-sm text-ink-600 leading-relaxed whitespace-pre-line">
            {positioning.preparation_timeline}
          </div>
        </div>
      )}

      {/* 风险提示 */}
      {positioning.risk_warnings.length > 0 && (
        <div className="rounded-xl border border-paper-200 bg-white p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-50">
              <AlertTriangle className="h-5 w-5 text-red-500" />
            </div>
            <h3 className="font-display font-bold text-ink-800">风险提示</h3>
          </div>
          <ul className="space-y-2">
            {positioning.risk_warnings.map((warn, i) => (
              <li key={`${warn}-${i}`} className="flex items-start gap-2 text-sm text-ink-600">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-red-400" />
                {warn}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 基本条件 */}
      <div className="rounded-xl border border-paper-200 bg-white p-6">
        <h3 className="font-display font-bold text-ink-800 mb-4">定位条件</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="text-sm"><span className="text-ink-400">学历：</span><span className="text-ink-700">{positioning.education_level}</span></div>
          <div className="text-sm"><span className="text-ink-400">院校：</span><span className="text-ink-700">{positioning.school_tier}</span></div>
          {positioning.major && <div className="text-sm"><span className="text-ink-400">专业：</span><span className="text-ink-700">{positioning.major}</span></div>}
          {positioning.target_region && <div className="text-sm"><span className="text-ink-400">目标地区：</span><span className="text-ink-700">{positioning.target_region}</span></div>}
          {positioning.target_type && <div className="text-sm"><span className="text-ink-400">目标类型：</span><span className="text-ink-700">{positioning.target_type}</span></div>}
          <div className="text-sm"><span className="text-ink-400">应届生：</span><span className="text-ink-700">{positioning.is_fresh_graduate ? "是" : "否"}</span></div>
          <div className="text-sm"><span className="text-ink-400">党员：</span><span className="text-ink-700">{positioning.is_party_member ? "是" : "否"}</span></div>
        </div>
      </div>
    </div>
  );
}

export default function CivilServicePage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <CivilServicePageContent />
    </Suspense>
  );
}

function CivilServicePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = searchParams.get("tab") || "positioning";

  // Tab2: 考公定位
  const [positioning, setPositioning] = useState<CivilServicePositioningResponse | null>(null);
  const [posLoading, setPosLoading] = useState(true);

  const handleTabChange = (id: string) => {
    router.push(`/civil-service?tab=${id}`);
  };


  // 加载 Tab2 数据（备考工具 tab 复用此数据，故一并加载）
  useEffect(() => {
    if (activeTab !== "positioning" && activeTab !== "tools") {
      setPosLoading(false);
      return;
    }
    setPosLoading(true);
    civilServiceIntelApi
      .getLatestPositioning()
      .then((data) => setPositioning(data))
      .catch(() => setPositioning(null))
      .finally(() => setPosLoading(false));
  }, [activeTab]);

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-ink-800 mb-2">考公中心</h1>
        <p className="text-ink-500">定位评估、备考工具与考试流程时间线 · 职位检索由公考雷达等专门工具承担</p>
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

      {/* Tab 内容 */}

      {activeTab === "positioning" && (
        <div>
          {posLoading ? (
            <LoadingState text="加载定位数据…" />
          ) : (
            <PositioningContent data={positioning} />
          )}
        </div>
      )}

      {activeTab === "tools" && (
        <div>
          {posLoading ? (
            <LoadingState text="加载备考数据…" />
          ) : (
            <ToolsContent positioning={positioning} />
          )}
        </div>
      )}

      {activeTab === "timeline" && <ExamTimelineTab />}
    </div>
  );
}
