"use client";

import { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Building2,
  MapPin,
  Target,
  BookOpen,
  Wrench,
  AlertTriangle,
  ChevronRight,
  TrendingUp,
  Star,
  Clock,
  Sparkles,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { civilServiceIntelApi } from "@/lib/api/ai";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  PostIntelResponse,
  CivilServicePositioningResponse,
  CivilServiceDarkKnowledgeResponse,
  CivilServiceDarkKnowledgeStage,
} from "@/types";

const tabs = [
  { id: "post-intel", label: "岗位情报", icon: Building2, color: "text-blue-500" },
  { id: "positioning", label: "考公定位", icon: Target, color: "text-purple-500" },
  { id: "dark-knowledge", label: "暗知识", icon: BookOpen, color: "text-amber-500" },
  { id: "tools", label: "备考工具", icon: Wrench, color: "text-green-500" },
];

const importanceMap: Record<string, { label: string; color: string }> = {
  critical: { label: "关键", color: "bg-red-100 text-red-700" },
  high: { label: "重要", color: "bg-orange-100 text-orange-700" },
  medium: { label: "一般", color: "bg-blue-100 text-blue-700" },
  low: { label: "了解", color: "bg-gray-100 text-gray-600" },
};

function PostIntelSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={`skel-${i}`} className="rounded-xl border border-paper-200 bg-white p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-5 rounded" />
            <Skeleton className="h-4 w-24" />
          </div>
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="h-3 w-1/2" />
          <div className="flex gap-2">
            <Skeleton className="h-6 w-16 rounded-full" />
            <Skeleton className="h-6 w-16 rounded-full" />
          </div>
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-4/5" />
        </div>
      ))}
    </div>
  );
}

function PostIntelCard({ post }: { post: PostIntelResponse }) {
  return (
    <div className="rounded-xl border border-paper-200 bg-white p-5 hover:shadow-md transition-shadow">
      <div className="flex items-center gap-2 mb-2">
        <Building2 className="h-4 w-4 text-blue-500" />
        <span className="text-xs font-medium text-ink-400">{post.department_tier || "部门"}</span>
      </div>
      <h3 className="font-display font-bold text-ink-800 mb-1">{post.post_name}</h3>
      <div className="flex items-center gap-3 text-sm text-ink-500 mb-3">
        <span className="flex items-center gap-1">
          <MapPin className="h-3.5 w-3.5" />
          {post.region}
        </span>
        <span>{post.department}</span>
      </div>
      <div className="flex flex-wrap gap-2 mb-3">
        <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
          {post.real_competition}
        </span>
        <span className="inline-flex items-center rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700">
          {post.treatment_level}
        </span>
        {post.salary_estimate && (
          <span className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700">
            {post.salary_estimate}
          </span>
        )}
      </div>
      {post.admission_ratio && (
        <p className="text-sm text-ink-500 mb-1">报录比：{post.admission_ratio}</p>
      )}
      {post.ai_summary && (
        <p className="text-sm text-ink-400 line-clamp-2">{post.ai_summary}</p>
      )}
    </div>
  );
}

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

function DarkKnowledgeContent({
  stages,
  activeStage,
  onSelectStage,
  items,
  loading,
}: {
  stages: CivilServiceDarkKnowledgeStage[];
  activeStage: string;
  onSelectStage: (stage: string) => void;
  items: CivilServiceDarkKnowledgeResponse[];
  loading: boolean;
}) {
  return (
    <div className="space-y-6">
      {/* 阶段筛选 */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {stages.map((s) => (
          <button
            key={s.stage}
            onClick={() => onSelectStage(s.stage)}
            className={cn(
              "flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all",
              activeStage === s.stage
                ? "bg-amber-500 text-white shadow-sm"
                : "bg-paper-100 text-ink-500 hover:bg-paper-200"
            )}
          >
            {s.stage_name}
            <span className="text-xs opacity-70">({s.count})</span>
          </button>
        ))}
      </div>

      {/* 暗知识卡片 */}
      {loading ? (
        <LoadingState text="加载暗知识…" />
      ) : items.length === 0 ? (
        <EmptyState title="该阶段暂无暗知识" description="请尝试选择其他阶段" />
      ) : (
        <div className="space-y-4">
          {items.map((item) => {
            const imp = importanceMap[item.importance] || importanceMap.medium;
            return (
              <div key={item.id} className="rounded-xl border border-paper-200 bg-white p-5">
                <div className="flex items-center gap-2 mb-2">
                  <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", imp.color)}>
                    {imp.label}
                  </span>
                  {item.tags.slice(0, 2).map((tag) => (
                    <span key={tag} className="text-xs text-ink-400">#{tag}</span>
                  ))}
                </div>
                <h4 className="font-display font-bold text-ink-800 mb-2">{item.title}</h4>
                <p className="text-sm text-ink-600 leading-relaxed mb-3">{item.content}</p>
                {item.common_misconception && (
                  <div className="rounded-lg bg-red-50 border border-red-100 p-3 mb-3">
                    <p className="text-xs font-medium text-red-600 mb-1">常见误区</p>
                    <p className="text-sm text-red-700">{item.common_misconception}</p>
                  </div>
                )}
                {item.actionable_advice && (
                  <div className="rounded-lg bg-green-50 border border-green-100 p-3">
                    <p className="text-xs font-medium text-green-600 mb-1">行动建议</p>
                    <p className="text-sm text-green-700">{item.actionable_advice}</p>
                  </div>
                )}
              </div>
            );
          })}
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
  const activeTab = searchParams.get("tab") || "post-intel";

  // Tab1: 岗位情报
  const [posts, setPosts] = useState<PostIntelResponse[]>([]);
  const [postsLoading, setPostsLoading] = useState(true);

  // Tab2: 考公定位
  const [positioning, setPositioning] = useState<CivilServicePositioningResponse | null>(null);
  const [posLoading, setPosLoading] = useState(true);

  // Tab3: 暗知识
  const [dkStages, setDkStages] = useState<CivilServiceDarkKnowledgeStage[]>([]);
  const [activeDkStage, setActiveDkStage] = useState("");
  const [dkItems, setDkItems] = useState<CivilServiceDarkKnowledgeResponse[]>([]);
  const [dkLoading, setDkLoading] = useState(false);
  const [stagesLoading, setStagesLoading] = useState(true);

  const handleTabChange = (id: string) => {
    router.push(`/civil-service?tab=${id}`);
  };

  // 加载 Tab1 数据
  useEffect(() => {
    if (activeTab !== "post-intel") return;
    setPostsLoading(true);
    civilServiceIntelApi
      .listPublicPostIntel({ limit: 50 })
      .then((data) => setPosts(data))
      .catch(() => setPosts([]))
      .finally(() => setPostsLoading(false));
  }, [activeTab]);

  // 加载 Tab2 数据
  useEffect(() => {
    if (activeTab !== "positioning") return;
    setPosLoading(true);
    civilServiceIntelApi
      .getLatestPositioning()
      .then((data) => setPositioning(data))
      .catch(() => setPositioning(null))
      .finally(() => setPosLoading(false));
  }, [activeTab]);

  // 加载 Tab3 阶段列表
  useEffect(() => {
    if (activeTab !== "dark-knowledge") return;
    setStagesLoading(true);
    civilServiceIntelApi
      .getDarkKnowledgeStages()
      .then((data) => {
        setDkStages(data);
        if (data.length > 0 && !activeDkStage) {
          setActiveDkStage(data[0].stage);
        }
      })
      .catch(() => setDkStages([]))
      .finally(() => setStagesLoading(false));
  }, [activeTab]);

  // 加载 Tab3 暗知识内容
  useEffect(() => {
    if (activeTab !== "dark-knowledge" || !activeDkStage) return;
    setDkLoading(true);
    civilServiceIntelApi
      .getDarkKnowledge(activeDkStage)
      .then((data) => setDkItems(data))
      .catch(() => setDkItems([]))
      .finally(() => setDkLoading(false));
  }, [activeTab, activeDkStage]);

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-ink-800 mb-2">考公中心</h1>
        <p className="text-ink-500">岗位情报、竞争力评估、暗知识与备考工具</p>
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
      {activeTab === "post-intel" && (
        <div>
          {postsLoading ? (
            <PostIntelSkeleton />
          ) : posts.length === 0 ? (
            <EmptyState
              title="暂无岗位情报"
              description="还没有公开的岗位情报数据"
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {posts.map((post) => (
                <PostIntelCard key={post.id} post={post} />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "positioning" && (
        <div>
          {posLoading ? (
            <LoadingState text="加载定位数据…" />
          ) : (
            <PositioningContent data={positioning} />
          )}
        </div>
      )}

      {activeTab === "dark-knowledge" && (
        <div>
          {stagesLoading ? (
            <LoadingState text="加载阶段列表…" />
          ) : dkStages.length === 0 ? (
            <EmptyState title="暂无暗知识" description="后端暂无考公暗知识数据" />
          ) : (
            <DarkKnowledgeContent
              stages={dkStages}
              activeStage={activeDkStage}
              onSelectStage={setActiveDkStage}
              items={dkItems}
              loading={dkLoading}
            />
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
    </div>
  );
}
