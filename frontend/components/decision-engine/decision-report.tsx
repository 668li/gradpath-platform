"use client";

// frontend/components/decision-engine/decision-report.tsx
// 「我的报考决策报告」— 报告式布局（截图/打印友好）。
// 把决策引擎的输出聚合为一份可读、可分享、可回传的报告：
// 三路横评 → 分数三档 → 岗位/院校分析 → 同分人群去向 → 行动时间线 → 综合建议。
// shared=true 时用于公开分享页（去掉一切需登录/回传元素）。

import { useMemo } from "react";
import {
  CalendarClock,
  FileText,
  Lightbulb,
  ShieldAlert,
  Target,
  Users,
} from "lucide-react";
import { Badge } from "@/components/ui/form-controls";
import { PathResultCard } from "./path-result-card";
import { PositionAnalysisCard } from "./position-analysis-card";
import { SchoolAnalysisCard } from "./school-analysis-card";
import { cn } from "@/lib/utils";
import type {
  DecisionEngineResponse,
  PeerDestinations,
} from "@/types/path-comparison";

/** 档案摘要 chip 的 key → 中文标签（含考研模考估分） */
const INPUT_LABELS: Record<string, string> = {
  major: "专业",
  region: "地区",
  school_tier: "层次",
  graduation_year: "届别",
  fresh_status: "应届状态",
  party_status: "政治面貌",
  education: "学历",
  has_grassroots: "基层经历",
  gender: "性别",
  estimated_score: "预估分",
  kaoyan_estimated_score: "考研估分",
};

/** 考公竞争力分级说明 */
const LEVEL_DESC: Record<string, string> = {
  稳健: "可报岗位进面线明显低于你的预估分，上岸概率相对更高",
  均衡: "可报岗位进面线与你的预估分大致相当，需要认真发挥",
  冲刺: "可报岗位进面线高于你的预估分，需要超常发挥或调整目标",
};

const LEVEL_COLOR: Record<string, "green" | "blue" | "amber" | "slate"> = {
  稳健: "green",
  均衡: "blue",
  冲刺: "amber",
};

/** 考研档位徽章颜色（冲/稳/保） */
const KAOYAN_BAND_COLOR: Record<string, "green" | "blue" | "amber"> = {
  稳: "green",
  均衡: "blue",
  冲: "amber",
};

/** 考研档位说明（由现有数据派生，不替用户拍板） */
const KAOYAN_BAND_DESC: Record<string, string> = {
  稳: "复试线明显低于你的估分，上岸把握较大",
  均衡: "复试线与你的估分大致相当，需要认真准备复试",
  冲: "复试线高于你的估分，属于需要超常发挥的冲刺档",
};

/** 由估分与复试线派生考研冲/稳/保档位（±15 分阈值） */
function deriveKaoyanBand(score: number, line: number): "稳" | "均衡" | "冲" {
  const diff = score - line;
  if (diff >= 15) return "稳";
  if (diff >= -15) return "均衡";
  return "冲";
}

/** 行动时间线里程碑（按历年惯例，具体以官方公告为准） */
interface TimelineItem {
  when: string;
  title: string;
  desc: string;
}

function buildTimeline(graduationYear?: number): TimelineItem[] {
  const gy = graduationYear ?? 2026;
  const py = gy - 1;
  return [
    { when: `${py} 年 9-11 月`, title: "秋招投递", desc: "直接就业线的主窗口，提前批往往更早启动" },
    { when: `${py} 年 10 月`, title: "考研报名 · 国考报名", desc: "研招网报名 + 国考职位发布（往年 10 月中）" },
    { when: `${py} 年 11-12 月`, title: "国考笔试", desc: "行政职业能力测验 + 申论" },
    { when: `${py} 年 12 月`, title: "考研初试", desc: "政治 / 外语 / 业务课（12 月下旬）" },
    { when: `${gy} 年 2-3 月`, title: "省考报名与笔试", desc: "多省联考往年 3 月笔试、2 月报名" },
    { when: `${gy} 年 3-4 月`, title: "考研复试 / 调剂", desc: "过线者准备复试，未过线抓紧调剂窗口" },
    { when: `${gy} 年 3-4 月`, title: "春招", desc: "就业线的第二窗口" },
    { when: `${gy} 年 6 月`, title: "毕业", desc: "应届身份结束，考公应届岗位窗口关闭" },
  ];
}

/** 同分人群去向栏：has_data 时显示分布，否则诚实占位（绝不编造） */
function PeerDestinationsSection({ peer }: { peer?: PeerDestinations | null }) {
  const has = !!peer?.has_data && (peer.distribution?.length ?? 0) > 0;
  return (
    <section className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-sky-500 to-cyan-600 text-white">
          <Users className="h-4 w-4" />
        </span>
        <div>
          <h3 className="text-base font-semibold text-ink-900">同分人群去向</h3>
          <p className="text-xs text-ink-500">
            {has && peer!.score_ref != null
              ? `与你考研估分 ${peer!.score_ref} 分 ±30 分内的真实回传样本`
              : "与你和同分人群的真实选择去向"}
          </p>
        </div>
      </div>

      {has ? (
        <div className="mt-4">
          <p className="text-xs text-ink-500">
            共 {peer!.peer_count} 条真实回传样本（由用户自愿交回，匿名聚合）
          </p>
          <ul className="mt-2 space-y-2">
            {peer!.distribution.map((d, i) => (
              <li key={i}>
                <div className="flex items-center justify-between text-xs text-ink-600">
                  <span>{d.label}</span>
                  <span className="text-ink-400">
                    {d.count} 人 · {Math.round(d.rate * 100)}%
                  </span>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-ink-100">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-sky-400 to-cyan-500"
                    style={{ width: `${Math.max(4, Math.round(d.rate * 100))}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="mt-3 rounded-lg border border-dashed border-paper-300 bg-paper-50/60 p-4">
          <p className="text-sm font-medium text-ink-700">
            你是最早的一批用户——同分样本还在积累
          </p>
          <p className="mt-1 text-xs leading-relaxed text-ink-500">
            当有足够多与你分数相近的人交回真实结果后，这里会显示「同样估分的人最后去了哪」。
            你现在就可以在下方回传自己的选择，成为这套分布的第一块基石。
          </p>
        </div>
      )}
    </section>
  );
}

interface DecisionReportProps {
  result: DecisionEngineResponse;
  /** 公开分享页模式：去掉需登录/回传元素 */
  shared?: boolean;
}

export function DecisionReport({ result, shared }: DecisionReportProps) {
  const input = result.input ?? {};
  const position = result.position_analysis;
  const school = result.school_analysis;

  // 考研冲/稳/保：由模考估分 vs 各院校复试线派生（标注「由现有数据派生」）
  const kaoyanScore =
    typeof input.kaoyan_estimated_score === "number"
      ? (input.kaoyan_estimated_score as number)
      : undefined;
  const kaoyanBands = useMemo(() => {
    if (kaoyanScore == null || !school?.items?.length) return [];
    return school.items
      .filter((s) => s.score_line != null && s.score_line > 0)
      .slice(0, 6)
      .map((s) => ({
        name: s.university_name,
        major: s.major_name,
        line: s.score_line as number,
        band: deriveKaoyanBand(kaoyanScore, s.score_line as number),
      }));
  }, [kaoyanScore, school]);

  const timeline = useMemo(() => buildTimeline(input.graduation_year as number | undefined), [input.graduation_year]);

  const today = new Date().toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  // 硬伤提醒计数（岗位劝退 + 院校劝退）
  const hardHitCount =
    (position?.avoid_positions?.length ?? 0) + (school?.avoid_schools?.length ?? 0);

  return (
    <div className={cn("mx-auto max-w-3xl space-y-5", shared && "w-full")}>
      {/* ===== 报告头 ===== */}
      <div className="overflow-hidden rounded-2xl border border-paper-200 bg-white shadow-sm">
        <div className="bg-gradient-to-br from-brand-600 via-indigo-600 to-fuchsia-600 px-6 py-5 text-white">
          <div className="flex items-center gap-2 text-xs font-medium text-white/80">
            <FileText className="h-3.5 w-3.5" />
            我的报考决策报告
            {shared && <span className="rounded-full bg-white/20 px-2 py-0.5 text-[10px]">公开分享</span>}
          </div>
          <h2 className="mt-1.5 text-xl font-bold">
            {String(input.major ?? "我的专业")} · {String(input.graduation_year ?? 2026)} 届报考决策
          </h2>
          <p className="mt-1 text-xs text-white/75">生成于 {today}</p>
        </div>
        {/* 档案摘要 chips */}
        <div className="flex flex-wrap items-center gap-2 border-t border-paper-100 px-6 py-3 text-xs text-ink-500">
          <span className="font-medium text-ink-700">当前档案：</span>
          {Object.entries(input).map(([k, v]) => (
            <span
              key={k}
              className="rounded-full border border-paper-200 bg-paper-50 px-2 py-0.5"
            >
              {INPUT_LABELS[k] ?? k}：{String(v)}
            </span>
          ))}
        </div>
      </div>

      {/* ===== 三路横评 ===== */}
      <div>
        <h3 className="mb-2 text-sm font-semibold text-ink-700">三路横评</h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {result.metrics.map((m) => (
            <PathResultCard key={m.path_type} metric={m} />
          ))}
        </div>
      </div>

      {/* ===== 分数三档 ===== */}
      <section className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 text-white">
            <Target className="h-4 w-4" />
          </span>
          <div>
            <h3 className="text-base font-semibold text-ink-900">分数三档</h3>
            <p className="text-xs text-ink-500">按你的预估分给目标分级，条件式结论、不替你做决定</p>
          </div>
        </div>

        {/* 考公档位 */}
        {position?.personalized_level && (
          <div className="mt-4 flex items-center gap-3 rounded-lg border border-paper-100 bg-paper-50/60 p-3">
            <div className="flex-1">
              <div className="text-xs font-medium text-ink-600">考公 · 个人竞争力</div>
              <div className="mt-0.5 text-sm text-ink-700">{LEVEL_DESC[position.personalized_level]}</div>
            </div>
            <Badge color={LEVEL_COLOR[position.personalized_level] ?? "slate"}>
              当前档位：{position.personalized_level}
            </Badge>
          </div>
        )}

        {/* 考研冲稳保 */}
        {kaoyanBands.length > 0 && (
          <div className="mt-3">
            <div className="flex items-center justify-between">
              <div className="text-xs font-medium text-ink-600">
                考研 · 按模考估分分档
                {kaoyanScore != null && <span className="text-ink-400">（估分 {kaoyanScore} 分）</span>}
              </div>
              <span className="text-[10px] text-ink-400">由现有数据派生</span>
            </div>
            <ul className="mt-2 space-y-1.5">
              {kaoyanBands.map((b) => (
                <li
                  key={`${b.name}-${b.major}`}
                  className="flex items-center gap-2 rounded-lg border border-paper-100 bg-paper-50/60 px-3 py-2 text-xs"
                >
                  <Badge color={KAOYAN_BAND_COLOR[b.band]}>
                    {b.band}
                  </Badge>
                  <span className="font-medium text-ink-800">{b.name}</span>
                  <span className="text-ink-500">{b.major}</span>
                  <span className="ml-auto text-ink-400">复试线 {b.line} 分</span>
                </li>
              ))}
            </ul>
            <p className="mt-1.5 text-[11px] text-ink-400">
              冲/稳/保由「模考估分 − 复试线」派生：±15 分内为均衡，高于为稳，低于为冲。
            </p>
          </div>
        )}
      </section>

      {/* ===== 硬伤提醒 ===== */}
      {hardHitCount > 0 && (
        <section className="rounded-xl border border-red-200 bg-red-50/50 p-5">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-red-600 text-white">
              <ShieldAlert className="h-4 w-4" />
            </span>
            <div>
              <h3 className="text-base font-semibold text-ink-900">硬伤提醒</h3>
              <p className="text-xs text-ink-500">
                共 {hardHitCount} 处「预估分明显低于目标线」的诚实劝退
              </p>
            </div>
          </div>
          {position?.avoid_positions?.map((card, i) => (
            <div key={`pos-${i}`} className="mt-3 rounded-lg border border-red-200 bg-white p-3">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className="text-sm font-semibold text-red-800">{card.verdict}</span>
                <span className="text-sm font-medium text-ink-800">{card.dept_name}</span>
                <span className="text-xs text-ink-500">{card.position_name}</span>
              </div>
              <p className="mt-1 text-xs leading-relaxed text-ink-600">{card.basis}</p>
              {card.alternatives.length > 0 && (
                <div className="mt-1.5 text-xs text-ink-600">
                  <span className="font-medium text-emerald-700">更有把握的替代：</span>
                  {card.alternatives.join("；")}
                </div>
              )}
            </div>
          ))}
          {school?.avoid_schools?.map((card, i) => (
            <div key={`sch-${i}`} className="mt-3 rounded-lg border border-red-200 bg-white p-3">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className="text-sm font-semibold text-red-800">{card.verdict}</span>
                <span className="text-sm font-medium text-ink-800">{card.university_name}</span>
                {card.major_name && <span className="text-xs text-ink-500">{card.major_name}</span>}
              </div>
              <p className="mt-1 text-xs leading-relaxed text-ink-600">{card.basis}</p>
              {card.alternatives.length > 0 && (
                <div className="mt-1.5 text-xs text-ink-600">
                  <span className="font-medium text-emerald-700">更有把握的替代：</span>
                  {card.alternatives.join("；")}
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {/* ===== 岗位级 + 院校级分析 ===== */}
      {position && <PositionAnalysisCard analysis={position} />}
      {school && <SchoolAnalysisCard analysis={school} />}

      {/* ===== 同分人群去向 ===== */}
      <PeerDestinationsSection peer={result.peer_destinations} />

      {/* ===== 行动时间线 ===== */}
      <section className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-teal-500 to-emerald-600 text-white">
            <CalendarClock className="h-4 w-4" />
          </span>
          <div>
            <h3 className="text-base font-semibold text-ink-900">行动时间线</h3>
            <p className="text-xs text-ink-500">
              按历年惯例的节点提醒，具体日期以官方公告为准
            </p>
          </div>
        </div>
        <ol className="mt-4 space-y-0">
          {timeline.map((t, i) => (
            <li key={i} className="relative flex gap-3 pb-4 last:pb-0">
              {i < timeline.length - 1 && (
                <span className="absolute left-[5px] top-4 h-full w-px bg-paper-200" />
              )}
              <span className="relative mt-1 h-[11px] w-[11px] shrink-0 rounded-full border-2 border-teal-500 bg-white" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <span className="text-xs font-semibold text-teal-700">{t.when}</span>
                  <span className="text-sm font-medium text-ink-800">{t.title}</span>
                </div>
                <p className="text-[11px] leading-snug text-ink-500">{t.desc}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* ===== 综合建议 ===== */}
      <div className="rounded-xl border border-purple-200 bg-gradient-to-br from-purple-50 via-fuchsia-50 to-indigo-50 p-5">
        <div className="flex items-start gap-3">
          <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-fuchsia-600 text-white">
            <Lightbulb className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1">
            <h3 className="mb-2 text-base font-semibold text-ink-900">综合建议</h3>
            <div className="whitespace-pre-line text-sm leading-relaxed text-ink-700">
              {result.recommendation}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
