"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Plus, Pencil, Trash2, Network, List, ChevronRight, Map, Compass, ArrowRight, Flame, TrendingUp, TrendingDown, Minus, Check, Lightbulb } from "lucide-react";
import { skillsApi } from "@/lib/api";
import { formatDate, levelStars, cn } from "@/lib/utils";
import { Modal } from "@/components/ui/modal";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Badge, Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { SkillRadar } from "@/components/charts";
import { SkillForm } from "@/components/skill-form";
import { SkillMapView } from "@/components/skills/skill-map-view";
import { TargetConditionCard } from "@/components/skills/target-condition-card";
import type { SkillResponse, SkillStats } from "@/types";

// 优化：D3.js 树状图依赖 DOM，仅在客户端渲染，按需加载减少首屏 JS 体积
const SkillTreeGraph = dynamic(
  () => import("@/components/skill-tree-graph").then((m) => m.SkillTreeGraph),
  {
    ssr: false,
    loading: () => <LoadingState />,
  },
);

const LEVEL_COLOR: Record<number, "slate" | "blue" | "purple"> = {
  1: "slate",
  2: "blue",
  3: "blue",
  4: "purple",
  5: "purple",
};

// ===== Hot Technologies 技能热度榜（增强2：灵感来源 O*NET）=====
// 按用户身份分赛道展示：不同身份的人需要的能力完全不同，
// 原版只有互联网技术栈，无法覆盖考研/考公/泛就业人群。
type TechTrend = "up" | "down" | "stable";

interface HotTech {
  name: string;
  heat: number; // 1-100 热度指数
  trend: TechTrend;
  roles: string; // 常见用途/岗位
}

interface IdentityTrack {
  key: string;
  label: string;
  basis: string; // 热度数据口径说明
  skills: HotTech[];
}

const IDENTITY_TRACKS: IdentityTrack[] = [
  {
    key: "kaoyan",
    label: "考研升学",
    basis: "基于全国硕士研究生报考科目与招生需求",
    skills: [
      { name: "专业课", heat: 96, trend: "up", roles: "目标院校自命题" },
      { name: "考研英语", heat: 94, trend: "stable", roles: "英语(一)/(二) 统考" },
      { name: "考研政治", heat: 92, trend: "stable", roles: "全国统考公共课" },
      { name: "考研数学", heat: 90, trend: "stable", roles: "数学(一)/(二)/(三)" },
      { name: "复试面试表达", heat: 84, trend: "up", roles: "综合面试/英文问答" },
      { name: "择校与信息检索", heat: 78, trend: "up", roles: "报录比/招简分析" },
      { name: "学术文献阅读", heat: 72, trend: "up", roles: "复试/读研衔接" },
      { name: "学术写作", heat: 68, trend: "stable", roles: "研究计划/论文" },
      { name: "编程上机", heat: 58, trend: "up", roles: "工科/计算机专业课" },
      { name: "二外/小语种", heat: 45, trend: "down", roles: "外语类专业课" },
    ],
  },
  {
    key: "kaogong",
    label: "考公考编",
    basis: "基于国考/省考/事业编笔试面试考察模块",
    skills: [
      { name: "申论写作", heat: 96, trend: "stable", roles: "笔试主观题" },
      { name: "行测-资料分析", heat: 93, trend: "stable", roles: "笔试/性价比最高" },
      { name: "行测-言语理解", heat: 92, trend: "stable", roles: "笔试" },
      { name: "行测-判断推理", heat: 91, trend: "stable", roles: "笔试" },
      { name: "面试结构化表达", heat: 88, trend: "up", roles: "面试翻盘关键" },
      { name: "时政热点积累", heat: 86, trend: "up", roles: "常识+申论素材" },
      { name: "常识判断", heat: 85, trend: "stable", roles: "笔试" },
      { name: "公共基础知识", heat: 78, trend: "stable", roles: "事业编/三支一扶" },
      { name: "公文写作", heat: 74, trend: "up", roles: "申论贯彻/上岸后" },
      { name: "计算机操作", heat: 62, trend: "up", roles: "岗位技能要求" },
    ],
  },
  {
    key: "jiuye",
    label: "求职就业",
    basis: "基于 2024-2025 全行业招聘市场需求",
    skills: [
      { name: "沟通表达", heat: 92, trend: "stable", roles: "全行业通用" },
      { name: "Excel/数据分析", heat: 90, trend: "stable", roles: "职能/运营/市场" },
      { name: "AI 工具应用", heat: 89, trend: "up", roles: "全行业提效" },
      { name: "简历与面试", heat: 88, trend: "stable", roles: "求职基本功" },
      { name: "英语", heat: 82, trend: "down", roles: "外企/跨境/大厂" },
      { name: "Python", heat: 80, trend: "up", roles: "数据/自动化/财务" },
      { name: "新媒体运营", heat: 75, trend: "up", roles: "内容/市场岗" },
      { name: "项目管理", heat: 73, trend: "stable", roles: "互联网/制造业" },
      { name: "PPT/演示设计", heat: 70, trend: "stable", roles: "咨询/汇报场景" },
      { name: "SQL", heat: 68, trend: "up", roles: "运营/产品/数据岗" },
    ],
  },
  {
    key: "tech",
    label: "互联网技术",
    basis: "基于 2024-2025 互联网技术岗招聘趋势",
    skills: [
      { name: "Python", heat: 98, trend: "up", roles: "后端/数据/AI" },
      { name: "JavaScript", heat: 95, trend: "stable", roles: "前端/全栈" },
      { name: "React", heat: 90, trend: "up", roles: "前端" },
      { name: "TypeScript", heat: 88, trend: "up", roles: "前端/全栈" },
      { name: "Java", heat: 85, trend: "stable", roles: "后端/Android" },
      { name: "SQL", heat: 82, trend: "stable", roles: "数据/后端" },
      { name: "Docker", heat: 78, trend: "up", roles: "运维/后端" },
      { name: "AWS", heat: 75, trend: "up", roles: "运维/后端" },
      { name: "Vue", heat: 72, trend: "stable", roles: "前端" },
      { name: "Go", heat: 70, trend: "up", roles: "后端" },
      { name: "Node.js", heat: 68, trend: "stable", roles: "全栈" },
      { name: "Kubernetes", heat: 65, trend: "up", roles: "运维" },
      { name: "Machine Learning", heat: 62, trend: "up", roles: "AI/数据" },
      { name: "Flutter", heat: 55, trend: "stable", roles: "移动端" },
      { name: "Rust", heat: 50, trend: "up", roles: "系统编程" },
    ],
  },
  {
    key: "campus",
    label: "在校通用",
    basis: "基于在校生评奖保研与实习求职基础能力",
    skills: [
      { name: "英语四六级", heat: 90, trend: "stable", roles: "毕业/保研硬门槛" },
      { name: "专业成绩 GPA", heat: 88, trend: "stable", roles: "保研/奖学金" },
      { name: "实习经历积累", heat: 85, trend: "up", roles: "秋招/春招敲门砖" },
      { name: "AI 辅助学习", heat: 83, trend: "up", roles: "效率/信息处理" },
      { name: "Office 办公技能", heat: 80, trend: "stable", roles: "课业/实习通用" },
      { name: "时间管理", heat: 78, trend: "stable", roles: "多线任务平衡" },
      { name: "演讲/展示表达", heat: 76, trend: "up", roles: "课堂展示/答辩" },
      { name: "团队协作", heat: 74, trend: "stable", roles: "小组项目/社团" },
      { name: "论文/报告写作", heat: 72, trend: "stable", roles: "课程论文/毕设" },
      { name: "竞赛与证书", heat: 70, trend: "stable", roles: "保研加分/简历" },
    ],
  },
];

const HOT_TAB_STORAGE_KEY = "skills:hot-track";
const HOT_MARKS_STORAGE_KEY = "skills:hot-marks";

type TechMark = "want" | "mastered" | null;

function TrendIcon({ trend }: { trend: TechTrend }) {
  if (trend === "up") {
    return <TrendingUp className="h-3 w-3 text-brand-600" />;
  }
  if (trend === "down") {
    return <TrendingDown className="h-3 w-3 text-red-500" />;
  }
  return <Minus className="h-3 w-3 text-ink-400" />;
}

function HotTechnologiesCard() {
  const [trackKey, setTrackKey] = useState<string>(IDENTITY_TRACKS[0].key);
  // 用户标记：身份 → (技能名 → 标记状态)，按身份分开存储并持久化
  const [marksByTrack, setMarksByTrack] = useState<Record<string, Record<string, TechMark>>>({});

  useEffect(() => {
    try {
      const savedTab = localStorage.getItem(HOT_TAB_STORAGE_KEY);
      if (savedTab && IDENTITY_TRACKS.some((t) => t.key === savedTab)) {
        setTrackKey(savedTab);
      }
      const savedMarks = localStorage.getItem(HOT_MARKS_STORAGE_KEY);
      if (savedMarks) setMarksByTrack(JSON.parse(savedMarks));
    } catch {
      // 本地缓存损坏时静默降级为初始状态
    }
  }, []);

  const track = IDENTITY_TRACKS.find((t) => t.key === trackKey) ?? IDENTITY_TRACKS[0];
  const marks = marksByTrack[track.key] ?? {};

  const persist = (next: Record<string, Record<string, TechMark>>) => {
    setMarksByTrack(next);
    try {
      localStorage.setItem(HOT_MARKS_STORAGE_KEY, JSON.stringify(next));
    } catch {
      // 忽略存储失败（隐私模式等）
    }
  };

  const cycleMark = (name: string) => {
    const current = marks[name] ?? null;
    const next: TechMark = current === null ? "want" : current === "want" ? "mastered" : null;
    const updated = { ...marks };
    if (next === null) {
      delete updated[name];
    } else {
      updated[name] = next;
    }
    persist({ ...marksByTrack, [track.key]: updated });
  };

  const switchTrack = (key: string) => {
    setTrackKey(key);
    try {
      localStorage.setItem(HOT_TAB_STORAGE_KEY, key);
    } catch {
      // 忽略存储失败
    }
  };

  const markValues = Object.values(marks);
  const wantCount = markValues.filter((m) => m === "want").length;
  const masteredCount = markValues.filter((m) => m === "mastered").length;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Flame className="h-4 w-4 text-orange-500 shrink-0" />
          <h2 className="font-semibold text-ink-800 text-sm">
            技能热度榜
          </h2>
          <span className="text-xs text-ink-400">· {track.basis}</span>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1 text-brand-600">
            <Lightbulb className="h-3 w-3" />
            想学 {wantCount}
          </span>
          <span className="flex items-center gap-1 text-ink-500">
            <Check className="h-3 w-3" />
            已掌握 {masteredCount}
          </span>
        </div>
      </div>
      {/* 身份切换：不同身份需要的能力不同，各赛道榜单与标记互相独立 */}
      <div className="flex items-center gap-1.5 mb-2 flex-wrap">
        {IDENTITY_TRACKS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => switchTrack(t.key)}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-colors",
              t.key === track.key
                ? "bg-brand-600 text-white"
                : "bg-ink-50 text-ink-600 hover:bg-ink-100",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      <p className="text-xs text-ink-400 mb-3">
        点击技能标记为「想学 → 已掌握 → 取消」，热度指数反映该身份下的能力需求强度
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        {track.skills.map((tech) => {
          const mark = marks[tech.name] ?? null;
          return (
            <button
              key={tech.name}
              type="button"
              onClick={() => cycleMark(tech.name)}
              className={cn(
                "rounded-lg border p-2.5 text-left transition-all hover:shadow-card-hover",
                mark === "mastered"
                  ? "border-brand-400 bg-brand-50"
                  : mark === "want"
                    ? "border-amber-300 bg-amber-50"
                    : "border-paper-300 bg-white hover:border-paper-400",
              )}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-ink-800 truncate">
                  {tech.name}
                </span>
                <TrendIcon trend={tech.trend} />
              </div>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-lg font-bold text-ink-800 leading-none">
                  {tech.heat}
                </span>
                <span className="text-[10px] text-ink-400">热度</span>
              </div>
              {/* 热度条 */}
              <div className="h-1 rounded-full bg-paper-200 overflow-hidden mb-1.5">
                <div
                  className={cn(
                    "h-full rounded-full",
                    tech.heat >= 85
                      ? "bg-orange-500"
                      : tech.heat >= 70
                        ? "bg-amber-500"
                        : "bg-brand-500",
                  )}
                  style={{ width: `${tech.heat}%` }}
                />
              </div>
              <p className="text-[10px] text-ink-400 truncate">{tech.roles}</p>
              {/* 标记状态 */}
              {mark && (
                <div className="mt-1.5 flex items-center gap-1">
                  {mark === "want" && (
                    <span className="inline-flex items-center gap-0.5 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
                      <Lightbulb className="h-2.5 w-2.5" /> 想学
                    </span>
                  )}
                  {mark === "mastered" && (
                    <span className="inline-flex items-center gap-0.5 rounded-full bg-brand-100 px-1.5 py-0.5 text-[10px] font-medium text-brand-700">
                      <Check className="h-2.5 w-2.5" /> 已掌握
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function SkillNodeItem({
  node,
  depth,
  onEdit,
  onDelete,
}: {
  node: SkillResponse;
  depth: number;
  onEdit: (s: SkillResponse) => void;
  onDelete: (s: SkillResponse) => void;
}) {
  return (
    <div>
      <div
        className="flex items-center gap-2 rounded-lg px-2 py-2 hover:bg-ink-50 group"
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
      >
        {node.children?.length > 0 ? (
          <ChevronRight className="h-4 w-4 text-ink-300 shrink-0" />
        ) : (
          <span className="w-4 shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-ink-800">{node.name}</span>
            <Badge color={LEVEL_COLOR[node.level] ?? "slate"}>
              Lv.{node.level}
            </Badge>
            {node.acquired_date && (
              <span className="text-xs text-ink-400">
                {formatDate(node.acquired_date)}
              </span>
            )}
          </div>
          {node.notes && (
            <p className="text-xs text-ink-400 mt-0.5 truncate">{node.notes}</p>
          )}
          <span className="text-amber-500 tracking-wide text-xs">
            {levelStars(node.level)}
          </span>
        </div>
        <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => onEdit(node)}
            className="p-1.5 rounded-md text-ink-400 hover:bg-ink-100 hover:text-brand-600"
            aria-label="编辑"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => onDelete(node)}
            className="p-1.5 rounded-md text-ink-400 hover:bg-red-50 hover:text-red-600"
            aria-label="删除"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
      {node.children?.map((child) => (
        <SkillNodeItem
          key={child.id}
          node={child}
          depth={depth + 1}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}

export default function SkillsPage() {
  const toast = useToast();
  const [tree, setTree] = useState<SkillResponse[]>([]);
  const [stats, setStats] = useState<SkillStats>({});
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<SkillResponse | null>(null);
  const [viewMode, setViewMode] = useState<"tree" | "list">("tree");
  // 顶层视图：能力地图 | 技能树
  const [topView, setTopView] = useState<"map" | "tree">("tree");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [treeResult, statsResult] = await Promise.allSettled([skillsApi.tree(), skillsApi.stats()]);
      if (treeResult.status === "fulfilled") {
        setTree(treeResult.value);
      }
      if (statsResult.status === "fulfilled") {
        setStats(statsResult.value);
      }
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    setModalOpen(true);
  };

  const openEdit = (s: SkillResponse) => {
    setEditing(s);
    setModalOpen(true);
  };

  const handleSaved = () => {
    setModalOpen(false);
    setEditing(null);
    load();
  };

  const handleDelete = async (s: SkillResponse) => {
    if (
      !window.confirm(
        `确认删除技能「${s.name}」？${s.children?.length ? "其子技能也将被删除。" : ""}`,
      )
    )
      return;
    try {
      await skillsApi.remove(s.id);
      toast.push("删除成功", "success");
      load();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "删除失败", "error");
    }
  };

  // 按顶层节点的 category 分组
  const grouped = tree.reduce<Record<string, SkillResponse[]>>((acc, node) => {
    const cat = node.category || "未分类";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(node);
    return acc;
  }, {});

  const radarData = Object.entries(stats).map(([category, count]) => ({
    category,
    count,
  }));

  const totalCount = tree.reduce(
    (sum, n) => sum + 1 + countDescendants(n),
    0,
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">技能树</h1>
          <p className="text-sm text-ink-500 mt-1">
            构建你的个人技能图谱，共 {totalCount} 个技能节点
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* 顶层视图切换：能力地图 | 技能树 */}
          <div className="inline-flex rounded-lg border border-paper-300 bg-white p-0.5">
            <button
              type="button"
              onClick={() => setTopView("map")}
              className={cn(
                "inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                topView === "map"
                  ? "bg-brand-600 text-white"
                  : "text-ink-600 hover:bg-paper-100",
              )}
            >
              <Map className="h-3.5 w-3.5" /> 能力地图
            </button>
            <button
              type="button"
              onClick={() => setTopView("tree")}
              className={cn(
                "inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                topView === "tree"
                  ? "bg-brand-600 text-white"
                  : "text-ink-600 hover:bg-paper-100",
              )}
            >
              <Network className="h-3.5 w-3.5" /> 技能树
            </button>
          </div>
          {/* 技能树视图下的二级切换：树形图 / 列表 */}
          {topView === "tree" && (
            <div className="inline-flex rounded-lg border border-paper-300 bg-white p-0.5">
              <button
                type="button"
                onClick={() => setViewMode("tree")}
                className={cn(
                  "inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                  viewMode === "tree"
                    ? "bg-brand-600 text-white"
                    : "text-ink-600 hover:bg-paper-100",
                )}
              >
                <Network className="h-3.5 w-3.5" /> 树形图
              </button>
              <button
                type="button"
                onClick={() => setViewMode("list")}
                className={cn(
                  "inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                  viewMode === "list"
                    ? "bg-brand-600 text-white"
                    : "text-ink-600 hover:bg-paper-100",
                )}
              >
                <List className="h-3.5 w-3.5" /> 列表
              </button>
            </div>
          )}
          {topView === "tree" && (
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" /> 新建技能
            </Button>
          )}
        </div>
      </div>

      {/* 能力地图视图 */}
      {topView === "map" && (
        <>
          <SkillMapView />
          {/* 能力地图底部引导：基于技能画像模拟职业路径 */}
          <Link
            href="/career-simulator?from=skills"
            className="card flex items-center gap-4 border-brand-200 bg-gradient-to-r from-brand-50/60 to-paper-50 p-4 transition-all hover:shadow-md group"
          >
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm">
              <Compass className="h-5 w-5" strokeWidth={1.8} />
            </span>
            <div className="flex-1 min-w-0">
              <p className="font-display font-semibold text-ink-800">
                基于你的技能画像，模拟职业路径
              </p>
              <p className="text-xs text-ink-500 mt-0.5 line-clamp-1">
                把能力地图代入考研 / 就业 / 考公的真实发展轨迹，看 10 年薪资与满意度对比。
              </p>
            </div>
            <span className="shrink-0 inline-flex items-center gap-1 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white transition-colors group-hover:bg-brand-700">
              去模拟
              <ArrowRight className="h-3.5 w-3.5" />
            </span>
          </Link>
        </>
      )}

      {/* 技能树视图 */}
      {topView === "tree" && (
        <>
        {/* 转型核心：目标条件对照 — 完成率即北极星「条件完成率」的职位级视图 */}
        <TargetConditionCard />

        {/* 增强2：Hot Technologies 技能热度榜 */}
        <HotTechnologiesCard />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 技能分组列表 */}
          <div className="lg:col-span-2 space-y-4">
            {loading ? (
              <div className="space-y-4 animate-pulse">
                {[1,2,3].map(i => (
                  <div key={`skel-${i}`} className="card p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="h-4 w-4 rounded bg-ink-200" />
                      <div className="h-4 w-20 bg-ink-200 rounded" />
                      <div className="h-5 w-10 bg-ink-200 rounded-full" />
                    </div>
                    {[1,2].map(j => (
                      <div key={j} className="flex items-center gap-2 py-2">
                        <div className="h-3 w-3 bg-ink-100 rounded" />
                        <div className="h-3 bg-ink-200 rounded flex-1" />
                        <div className="h-3 w-16 bg-ink-100 rounded" />
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            ) : tree.length === 0 ? (
              <EmptyState
                title="还没有技能"
                description="添加你的第一项技能，构建个人技能树"
                action={
                  <Button onClick={openCreate}>
                    <Plus className="h-4 w-4" /> 创建技能
                  </Button>
                }
              />
            ) : viewMode === "tree" ? (
              <div className="card p-4">
                <SkillTreeGraph skills={tree} onNodeClick={openEdit} />
              </div>
            ) : (
              Object.entries(grouped).map(([cat, nodes]) => (
                <div key={cat} className="card">
                  <div className="flex items-center gap-2 mb-2">
                    <Network className="h-4 w-4 text-brand-500" />
                    <h2 className="font-semibold text-ink-800">{cat}</h2>
                    <Badge color="blue">{countCategoryNodes(nodes)}</Badge>
                  </div>
                  <div className="divide-y divide-ink-50">
                    {nodes.map((node) => (
                      <SkillNodeItem
                        key={node.id}
                        node={node}
                        depth={0}
                        onEdit={openEdit}
                        onDelete={handleDelete}
                      />
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* 雷达图 */}
          <div className="card h-fit lg:sticky lg:top-6">
            <h2 className="font-semibold text-ink-800 mb-2">技能分类雷达</h2>
            {radarData.length === 0 ? (
              <EmptyState title="暂无数据" description="添加技能后将显示雷达图" />
            ) : (
              <SkillRadar data={radarData} />
            )}
          </div>
        </div>
        </>
      )}

      <Modal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditing(null);
        }}
        title={editing ? "编辑技能" : "新建技能"}
        className="max-w-xl"
      >
        <SkillForm
          initial={editing}
          tree={tree}
          onSaved={handleSaved}
          onCancel={() => {
            setModalOpen(false);
            setEditing(null);
          }}
        />
      </Modal>
    </div>
  );
}

function countDescendants(node: SkillResponse): number {
  return (node.children ?? []).reduce(
    (sum, c) => sum + 1 + countDescendants(c),
    0,
  );
}

function countCategoryNodes(nodes: SkillResponse[]): number {
  return nodes.reduce((sum, n) => sum + 1 + countDescendants(n), 0);
}
