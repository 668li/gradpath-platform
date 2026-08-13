"use client";

// frontend/components/career-simulator/test-drive-card.tsx
// 职业试驾组件 — TestDriveCard（单个一日体验卡片）+ TestDriveSection（完整试驾区域）

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Calendar, Play, Sparkles, CheckCircle2, AlertCircle, Clock,
  GraduationCap, Briefcase, Landmark, ArrowRight, History,
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import { careerTestDriveApi } from "@/lib/api";
import type { CareerTestDrive } from "@/types/career-test-drive";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";

// 路径元信息：名称 / 图标 / 渐变色
const PATH_META: Record<string, { name: string; icon: React.ReactNode; gradient: string; ring: string }> = {
  kaoyan: {
    name: "考研",
    icon: <GraduationCap className="w-5 h-5" />,
    gradient: "from-blue-500 to-indigo-600",
    ring: "ring-blue-200",
  },
  employment: {
    name: "就业",
    icon: <Briefcase className="w-5 h-5" />,
    gradient: "from-emerald-500 to-teal-600",
    ring: "ring-emerald-200",
  },
  civil_service: {
    name: "考公",
    icon: <Landmark className="w-5 h-5" />,
    gradient: "from-amber-500 to-orange-600",
    ring: "ring-amber-200",
  },
};

// 候选角色（每条路径下的代表角色，用户可改）
const ROLE_OPTIONS: { path_type: string; role: string }[] = [
  { path_type: "kaoyan", role: "考研计算机" },
  { path_type: "kaoyan", role: "考研文科" },
  { path_type: "employment", role: "互联网产品经理" },
  { path_type: "employment", role: "软件开发" },
  { path_type: "civil_service", role: "考公基层" },
  { path_type: "civil_service", role: "考公机关" },
];

// 情绪 → 0-10 分值（用于情绪曲线）
const EMOTION_SCORE: Record<string, number> = {
  兴奋: 9, 期待: 8, 满足: 8, 充实: 7, 踏实: 7, 投入: 7, 专注: 7,
  放松: 6, 平静: 6, 认真: 6, 耐心: 6,
  紧张: 5, 高压: 4,
  无奈: 4, 困倦: 4, 受挫: 3, 麻木: 3, 机械: 3,
  焦虑: 3, 焦躁: 2, 烦躁: 2, 疲惫: 2, 枯燥: 2,
};

// 情绪 → 颜色标签
function emotionColor(emotion: string): string {
  const s = EMOTION_SCORE[emotion] ?? 5;
  if (s >= 7) return "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (s >= 5) return "bg-amber-50 text-amber-700 border-amber-200";
  return "bg-rose-50 text-rose-700 border-rose-200";
}

interface TestDriveCardProps {
  drive: CareerTestDrive;
}

/** 单个一日体验卡片：情绪曲线 + 时间轴 + 优点/挑战 */
export function TestDriveCard({ drive }: TestDriveCardProps) {
  const meta = PATH_META[drive.path_type] ?? PATH_META.employment;

  // 情绪曲线数据
  const emotionData = useMemo(
    () => drive.experience_content.map((b) => ({
      time: b.time,
      mood: EMOTION_SCORE[b.emotion] ?? 5,
      label: b.emotion,
    })),
    [drive.experience_content],
  );

  return (
    <div className={`rounded-2xl bg-white shadow-lg overflow-hidden ring-1 ${meta.ring}`}>
      {/* 顶部：路径 + 角色 + 情绪曲线 */}
      <div className={`bg-gradient-to-r ${meta.gradient} p-5 text-white`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-white/20 backdrop-blur-sm">
              {meta.icon}
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-white/80">
                {meta.name} · 一日试驾
              </div>
              <h3 className="text-xl font-bold">{drive.target_role}</h3>
            </div>
          </div>
          <Calendar className="w-5 h-5 text-white/70" />
        </div>
        {/* 情绪曲线 */}
        <div className="mt-3 h-20">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={emotionData} margin={{ top: 5, right: 5, bottom: 0, left: -28 }}>
              <XAxis dataKey="time" tick={{ fill: "rgba(255,255,255,0.7)", fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 10]} hide />
              <Tooltip
                contentStyle={{ background: "rgba(0,0,0,0.8)", border: "none", borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: "#fff" }}
                formatter={(v: number) => [`${v}/10`, "情绪"]}
                labelFormatter={(l) => `${l}`}
              />
              <Line
                type="monotone"
                dataKey="mood"
                stroke="rgba(255,255,255,0.95)"
                strokeWidth={2}
                dot={{ r: 3, fill: "rgba(255,255,255,0.9)" }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 中间：时间轴 */}
      <div className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-4 h-4 text-ink-400" />
          <span className="text-sm font-medium text-ink-700">一日时间轴</span>
        </div>
        <div className="relative">
          {/* 时间轴竖线 */}
          <div className="absolute left-[60px] top-2 bottom-2 w-0.5 bg-gradient-to-b from-ink-200 via-ink-200 to-transparent" />
          <div className="space-y-3">
            {drive.experience_content.map((block, i) => (
              <div key={`${block.time}-${i}`} className="flex items-start gap-4">
                <div className="w-12 text-right text-xs font-mono text-ink-500 pt-1.5 shrink-0">
                  {block.time}
                </div>
                {/* 节点圆点 */}
                <div className="relative shrink-0 mt-2">
                  <div className="w-3 h-3 rounded-full bg-white border-2 border-ink-300 z-10 relative" />
                </div>
                <div className="flex-1 min-w-0 pb-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-ink-900 text-sm">{block.activity}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${emotionColor(block.emotion)}`}>
                      {block.emotion}
                    </span>
                  </div>
                  <p className="text-xs text-ink-600 mt-0.5 leading-relaxed">{block.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 一日总结 */}
        <div className="mt-4 rounded-xl bg-ink-50 border border-ink-100 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span className="text-sm font-medium text-ink-700">一日总结</span>
          </div>
          <p className="text-sm text-ink-600 leading-relaxed">{drive.summary}</p>
        </div>
      </div>

      {/* 底部：优点 / 挑战 双栏 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 border-t border-ink-100">
        <div className="p-5 border-r border-ink-100">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span className="text-sm font-semibold text-emerald-700">这条路的优势</span>
          </div>
          <ul className="space-y-2">
            {drive.pros.map((p, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-ink-700">
                <span className="text-emerald-500 mt-0.5">+</span>
                <span className="leading-relaxed">{p}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertCircle className="w-4 h-4 text-rose-600" />
            <span className="text-sm font-semibold text-rose-700">需面对的挑战</span>
          </div>
          <ul className="space-y-2">
            {drive.cons.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-ink-700">
                <span className="text-rose-500 mt-0.5">−</span>
                <span className="leading-relaxed">{c}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

/** 完整试驾区域：路径选择 + 生成 + 卡片展示 + 引导到 decision-lab */
export function TestDriveSection() {
  const router = useRouter();
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [drive, setDrive] = useState<CareerTestDrive | null>(null);
  const [selected, setSelected] = useState<{ path_type: string; role: string }>(ROLE_OPTIONS[0]);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const data = await careerTestDriveApi.generate({
        path_type: selected.path_type,
        target_role: selected.role,
      });
      setDrive(data);
      toast.success("一日体验已生成，沉浸感受这条路径");
    } catch {
      toast.error("试驾生成失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  // 按路径分组角色选项
  const groupedRoles = useMemo(() => {
    const groups: Record<string, { path_type: string; role: string }[]> = {};
    for (const r of ROLE_OPTIONS) {
      (groups[r.path_type] ||= []).push(r);
    }
    return groups;
  }, []);

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 mt-6">
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-ink-900 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-amber-500" />
          职业试驾 — 沉浸式体验这一天
        </h2>
        <p className="mt-1 text-sm text-ink-500">
          选定路径前，先"试驾"一天：第一人称感受从清晨到深夜的真实节奏、情绪起伏与得失。
        </p>
      </div>

      {/* 路径 + 角色选择器 */}
      <div className="flex flex-wrap items-end gap-3 mb-5">
        <div>
          <label className="block text-xs font-medium text-ink-500 mb-1">路径</label>
          <select
            value={selected.path_type}
            onChange={(e) => {
              const pt = e.target.value;
              const first = ROLE_OPTIONS.find((r) => r.path_type === pt);
              setSelected({ path_type: pt, role: first?.role ?? "" });
            }}
            className="border rounded-lg px-3 py-2 text-sm bg-white"
          >
            {Object.entries(groupedRoles).map(([pt]) => (
              <option key={pt} value={pt}>{PATH_META[pt]?.name ?? pt}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-ink-500 mb-1">角色</label>
          <select
            value={selected.role}
            onChange={(e) => setSelected({ path_type: selected.path_type, role: e.target.value })}
            className="border rounded-lg px-3 py-2 text-sm bg-white"
          >
            {(groupedRoles[selected.path_type] || []).map((r) => (
              <option key={r.role} value={r.role}>{r.role}</option>
            ))}
          </select>
        </div>
        <button
          onClick={handleGenerate}
          disabled={loading || !selected.role}
          className="inline-flex items-center gap-1.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-5 py-2 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {loading ? (
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          {loading ? "生成中…" : "试驾这一天"}
        </button>
        <button
          onClick={() => router.push("/career-simulator")}
          className="inline-flex items-center gap-1.5 text-ink-500 hover:text-ink-700 px-3 py-2 text-sm border rounded-lg transition-colors"
          title="查看历史试驾"
        >
          <History className="w-4 h-4" />
        </button>
      </div>

      {/* 加载 / 结果 / 空状态 */}
      {loading && <LoadingState text="正在生成你的沉浸式一日体验…" />}

      {!loading && drive && (
        <div className="space-y-5">
          <TestDriveCard drive={drive} />
          {/* 引导到深度决策 */}
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              onClick={() => router.push("/decision-lab")}
              className="inline-flex items-center gap-1.5 text-brand-600 hover:text-brand-700 text-sm font-medium px-4 py-2 rounded-lg bg-brand-50 hover:bg-brand-100 transition-colors"
            >
              对比其他路径 <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => router.push("/decision-lab")}
              className="inline-flex items-center gap-1.5 text-purple-600 hover:text-purple-700 text-sm font-medium px-4 py-2 rounded-lg bg-purple-50 hover:bg-purple-100 transition-colors"
            >
              深度分析这条路径 <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {!loading && !drive && (
        <EmptyState
          title="还没试驾过"
          description="选择一条路径与角色，点击「试驾这一天」，AI 会生成一段第一人称的沉浸式一日体验。"
        />
      )}
    </div>
  );
}
