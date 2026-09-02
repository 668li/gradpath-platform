"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import {
  Telescope,
  Search,
  TrendingUp,
  Briefcase,
  Building2,
  GraduationCap,
  Landmark,
  Info,
  ArrowRight,
} from "lucide-react";
import { majorProspectApi } from "@/lib/api";
import type {
  MajorListItem,
  MajorProspect,
  OutgoingTier,
} from "@/lib/api/major-prospects";
import { LoadingState, EmptyState } from "@/components/ui/empty";

// 常用专业快捷入口（覆盖考研/考公/就业/在校各身份人群的高频专业）
const POPULAR_MAJORS = [
  "计算机科学与技术",
  "软件工程",
  "电子信息",
  "机械工程",
  "电气工程",
  "土木工程",
  "临床医学",
  "法学",
  "会计学",
  "金融学",
  "汉语言文学",
  "英语语言文学",
  "教育学",
  "行政管理",
];

const SIZE_LABELS: Record<string, string> = {
  giant: "巨头",
  large: "大型",
  medium: "中型",
  small: "小型",
  startup: "初创",
};

const DISCRIMINATION_LABELS: Record<string, { text: string; cls: string }> = {
  none: { text: "不卡第一学历", cls: "bg-green-100 text-green-700" },
  light: { text: "轻度看背景", cls: "bg-blue-100 text-blue-700" },
  moderate: { text: "中度看背景", cls: "bg-amber-100 text-amber-700" },
  severe: { text: "严重卡学历", cls: "bg-red-100 text-red-700" },
  unknown: { text: "未知", cls: "bg-ink-100 text-ink-500" },
};

// 出身层次选项：专科手动选档（系统不建专科院校库，避免把层次强加给专科）
const OUTGOING_TIER_OPTIONS: OutgoingTier[] = [
  "985",
  "211",
  "双一流",
  "一本",
  "二本",
  "专科",
];

// 出身个性化标注的徽章颜色（仅当目标校出身敏感度带可核验来源时才会出现）
const OUTGOING_RISK_BADGES: Record<string, { text: string; cls: string }> = {
  friendly: { text: "出身友好", cls: "bg-green-100 text-green-700" },
  acceptable: { text: "可冲", cls: "bg-blue-100 text-blue-700" },
  careful: { text: "需谨慎", cls: "bg-amber-100 text-amber-700" },
  high: { text: "风险偏高", cls: "bg-red-100 text-red-700" },
};

const CIVIL_STYLES: Record<string, string> = {
  high: "bg-green-100 text-green-700 border-green-200",
  medium: "bg-amber-100 text-amber-700 border-amber-200",
  low: "bg-ink-100 text-ink-500 border-ink-200",
};

function fmtWan(v: number): string {
  return (v / 10000).toFixed(1);
}

function SectionCard({
  icon: Icon,
  title,
  desc,
  children,
}: {
  icon: typeof TrendingUp;
  title: string;
  desc?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="mb-4 flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-600">
          <Icon className="h-5 w-5" strokeWidth={1.8} />
        </div>
        <div>
          <h2 className="font-semibold text-ink-800">{title}</h2>
          {desc && <p className="mt-0.5 text-xs text-ink-400">{desc}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

function ProspectResult({ data }: { data: MajorProspect }) {
  const maxSalary = Math.max(
    ...data.industries.map((i) => i.salary_non_private),
    1,
  );
  const hasAny =
    data.industries.length > 0 ||
    data.positions.length > 0 ||
    data.companies.length > 0 ||
    data.grad_paths.length > 0;

  return (
    <div className="space-y-5">
      {/* 专业头部 */}
      <div className="rounded-xl border border-brand-200 bg-brand-50 p-5 sm:p-6">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-display text-xl font-bold text-ink-800">
            {data.major}
          </h2>
          <span className="rounded-full bg-brand-100 px-2.5 py-0.5 text-xs font-medium text-brand-700">
            {data.category}
          </span>
          {!data.exact_match && (
            <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs text-amber-700">
              按「{data.matched_major}」相近口径分析
            </span>
          )}
        </div>
        {data.related_majors.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs text-ink-400">
            <span>相近专业：</span>
            {data.related_majors.map((m) => (
              <button
                key={m}
                onClick={() => window.dispatchEvent(new CustomEvent("major-prospect-select", { detail: m }))}
                className="rounded-full bg-white px-2 py-0.5 text-brand-600 hover:bg-brand-100 transition-colors"
              >
                {m}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 出身层次制度性事实（一般性公开常识，非某校特定造数，不与"真实数据"混标） */}
      {data.grad_personalized && data.tier_fact && (
        <div className="flex items-start gap-2 rounded-xl border border-blue-200 bg-blue-50 p-3.5 text-sm text-blue-800">
          <Info className="mt-0.5 h-4 w-4 shrink-0" />
          <p className="leading-relaxed">{data.tier_fact}</p>
        </div>
      )}

      {!hasAny && (
        <EmptyState
          title="该专业暂无聚合数据"
          description="这个专业还未收录对口数据，试试其他专业或联系我们补充。"
        />
      )}

      {/* 行业去向与薪资 */}
      {data.industries.length > 0 && (
        <SectionCard
          icon={TrendingUp}
          title="对口行业与薪资水平"
          desc={`国家统计局 ${data.industries[0]?.year} 年 · 城镇单位年平均工资（行业整体口径）`}
        >
          <div className="space-y-3">
            {data.industries.map((ind) => (
              <div key={ind.industry}>
                <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
                  <span className="truncate text-ink-700">{ind.industry}</span>
                  <span className="shrink-0 font-semibold text-ink-800">
                    {fmtWan(ind.salary_non_private)} 万/年
                    <span className="ml-1.5 text-xs font-normal text-ink-400">
                      {ind.salary_private
                        ? `（私营 ${fmtWan(ind.salary_private)} 万）`
                        : ""}
                    </span>
                  </span>
                </div>
                <div className="h-2.5 w-full overflow-hidden rounded-full bg-paper-200">
                  <div
                    className="h-full rounded-full bg-brand-500"
                    style={{
                      width: `${Math.max(6, (ind.salary_non_private / maxSalary) * 100)}%`,
                    }}
                  />
                </div>
                <p className="mt-0.5 text-xs text-ink-400">
                  {ind.vs_national >= 1
                    ? `是全国平均工资的 ${ind.vs_national} 倍`
                    : `为全国平均工资的 ${Math.round(ind.vs_national * 100)}%`}
                </p>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* 岗位薪资 */}
      {data.positions.length > 0 && (
        <SectionCard
          icon={Briefcase}
          title="相关岗位的真实薪资"
          desc="各市人社局工资价位 · 年薪中位数（多为 3~5 年经验口径，应届起薪通常低于此数）"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-paper-200 text-left text-xs text-ink-400">
                  <th className="pb-2 pr-3 font-medium">岗位</th>
                  <th className="pb-2 pr-3 font-medium">中位数</th>
                  <th className="pb-2 pr-3 font-medium">区间</th>
                  <th className="pb-2 font-medium">城市</th>
                </tr>
              </thead>
              <tbody>
                {data.positions.map((p) => (
                  <tr
                    key={p.position}
                    className="border-b border-paper-100 last:border-0"
                  >
                    <td className="py-2.5 pr-3 text-ink-700">{p.position}</td>
                    <td className="py-2.5 pr-3 font-semibold text-ink-800">
                      {fmtWan(p.salary_median)} 万
                    </td>
                    <td className="py-2.5 pr-3 text-xs text-ink-400">
                      {fmtWan(p.salary_min)} ~ {fmtWan(p.salary_max)} 万
                    </td>
                    <td className="py-2.5 text-xs text-ink-400">
                      {p.cities.slice(0, 3).join("、")}
                      {p.cities.length > 3 ? " 等" : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      )}

      {/* 去向公司 */}
      {data.companies.length > 0 && (
        <SectionCard
          icon={Building2}
          title="典型去向公司"
          desc="按行业匹配的对口雇主"
        >
          <div className="flex flex-wrap gap-2">
            {data.companies.map((c) => (
              <div
                key={c.name}
                className="rounded-lg border border-paper-200 bg-paper-50 px-3 py-2"
              >
                <p className="text-sm font-medium text-ink-700">{c.name}</p>
                <p className="mt-0.5 text-xs text-ink-400">
                  {c.industry}
                  {c.headquarters ? ` · ${c.headquarters}` : ""}
                  {SIZE_LABELS[c.size] ? ` · ${SIZE_LABELS[c.size]}` : ""}
                </p>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* 升学路径 */}
      {data.grad_paths.length > 0 && (
        <SectionCard
          icon={GraduationCap}
          title="升学路径 · 考研情报"
          desc={data.grad_personalized ? "该专业考研竞争格局（标注来自带可核验来源的院校信息）" : "该专业考研竞争格局，按公开分数线排序（多数院校出身敏感度暂缺可核验来源，未标注）"}
        >
          <div className="space-y-2.5">
            {data.grad_paths.map((g) => {
              const dis = DISCRIMINATION_LABELS[g.background_discrimination] ?? DISCRIMINATION_LABELS.unknown;
              const riskBadge = g.outgoing_risk ? OUTGOING_RISK_BADGES[g.outgoing_risk] : null;
              return (
                <div
                  key={`${g.school_name}-${g.major_name}`}
                  className="rounded-lg border border-paper-200 bg-paper-50 px-3 py-2.5 text-sm"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-ink-800">
                      {g.school_name}
                    </span>
                    {g.school_tier && (
                      <span className="rounded bg-brand-100 px-1.5 py-0.5 text-xs text-brand-700">
                        {g.school_tier}
                      </span>
                    )}
                    <span className="text-ink-400">·</span>
                    <span className="text-ink-600">{g.major_name}</span>
                    <span className="ml-auto flex flex-wrap items-center gap-1.5 text-xs">
                      <span className="rounded bg-white px-1.5 py-0.5 text-ink-500">
                        报录比 {g.admission_ratio}
                      </span>
                      <span className="rounded bg-white px-1.5 py-0.5 text-ink-500">
                        分数线 {g.score_line}
                      </span>
                      <span className={`rounded px-1.5 py-0.5 ${dis.cls}`}>
                        {dis.text}
                      </span>
                      {riskBadge && (
                        <span className={`rounded px-1.5 py-0.5 ${riskBadge.cls}`}>
                          {riskBadge.text}
                        </span>
                      )}
                    </span>
                  </div>
                  {g.outgoing_note && data.grad_personalized && (
                    <p className="mt-1.5 text-xs leading-relaxed text-ink-500">
                      {g.outgoing_note}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
          <Link
            href="/kaoyan"
            className="mt-3 inline-flex items-center gap-1 text-sm text-brand-600 hover:text-brand-700"
          >
            查看完整考研情报 <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </SectionCard>
      )}

      {/* 考公友好度 */}
      <SectionCard icon={Landmark} title="考公适配度" desc="基于历年国考省考招录专业的经验规则">
        <div
          className={`inline-flex rounded-lg border px-3 py-1 text-sm font-medium ${CIVIL_STYLES[data.civil_service.level]}`}
        >
          {data.civil_service.label}
        </div>
        <p className="mt-2.5 text-sm leading-relaxed text-ink-600">
          {data.civil_service.note}
        </p>
        <Link
          href="/civil-service"
          className="mt-3 inline-flex items-center gap-1 text-sm text-brand-600 hover:text-brand-700"
        >
          查看考公情报 <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </SectionCard>

      {/* 数据说明 */}
      <div className="rounded-xl bg-paper-100 p-4">
        <div className="flex items-start gap-2 text-xs text-ink-400">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <div>
            <p className="mb-1 font-medium text-ink-500">数据说明</p>
            <ul className="list-disc space-y-0.5 pl-4">
              {data.data_notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MajorProspectsPage() {
  const [input, setInput] = useState("");
  const [major, setMajor] = useState("");
  const [outgoingTier, setOutgoingTier] = useState<OutgoingTier | null>(null);

  const { data: majors } = useSWR<MajorListItem[]>(
    "major-prospect-majors",
    () => majorProspectApi.majors(),
    { revalidateOnFocus: false },
  );

  const { data, isLoading, error } = useSWR<MajorProspect>(
    major ? `major-prospect-${major}-${outgoingTier ?? "all"}` : null,
    () => majorProspectApi.detail(major, outgoingTier),
    { revalidateOnFocus: false },
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) setMajor(input.trim());
  };

  // 相近专业一键切换
  useEffect(() => {
    const handler = (e: Event) => {
      const name = (e as CustomEvent<string>).detail;
      if (name) {
        setInput(name);
        setMajor(name);
      }
    };
    window.addEventListener("major-prospect-select", handler);
    return () => window.removeEventListener("major-prospect-select", handler);
  }, []);

  const majorNames = useMemo(() => (majors ?? []).map((m) => m.name), [majors]);

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        {/* 头部 */}
        <div className="mb-8">
          <div className="mb-3 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
              <Telescope className="h-6 w-6" strokeWidth={1.8} />
            </div>
            <div>
              <h1 className="font-display text-2xl font-bold tracking-tight text-ink-800">
                专业前景
              </h1>
              <p className="mt-0.5 text-sm text-ink-400">
                你的专业，未来能去哪——用真实数据提前看到
              </p>
            </div>
          </div>
          <p className="text-sm leading-relaxed text-ink-500">
            不确定要不要考研、考公还是就业？先看看你这个专业的学长学姐们真实去了哪些行业、
            拿多少薪资、考研竞争有多激烈——全部基于公开权威数据，不是营销号的话术。
          </p>
        </div>

        {/* 搜索 */}
        <form onSubmit={handleSubmit} className="mb-5 flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入专业名，如：计算机、会计、法学…"
              className="w-full rounded-lg border border-paper-300 bg-white py-2.5 pl-9 pr-3 text-sm text-ink-800 placeholder:text-ink-300 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
              aria-label="输入专业名称"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-600"
          >
            查前景
          </button>
        </form>

        {/* 出身层次选档（升学路径个性化） */}
        <div className="mb-6 rounded-xl border border-paper-200 bg-white p-3.5">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-ink-500">
            <GraduationCap className="h-3.5 w-3.5" />
            <span>你的本科出身层次（可选）</span>
            <span className="font-normal text-ink-300">
              · 用于升学路径个性化，不改变薪资/行业数据
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setOutgoingTier(null)}
              className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                outgoingTier === null
                  ? "border-brand-400 bg-brand-100 text-brand-700"
                  : "border-paper-300 bg-white text-ink-500 hover:border-brand-300 hover:text-brand-600"
              }`}
            >
              不指定
            </button>
            {OUTGOING_TIER_OPTIONS.map((t) => (
              <button
                key={t}
                onClick={() => setOutgoingTier(t)}
                className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                  outgoingTier === t
                    ? "border-brand-400 bg-brand-100 text-brand-700"
                    : "border-paper-300 bg-white text-ink-500 hover:border-brand-300 hover:text-brand-600"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          {outgoingTier && major &&
            (data?.grad_personalized ? (
              <p className="mt-2 text-xs text-ink-400">
                已按「{outgoingTier}」出身个性化升学路径（依据带可核验来源的院校出身敏感度）。
              </p>
            ) : (
              <p className="mt-2 rounded-md bg-amber-50 px-2.5 py-1.5 text-xs text-amber-700">
                已选「{outgoingTier}」出身，但这些院校暂缺带可核验来源的出身敏感度数据，升学路径暂按公开分数线排序，未做出身降权。
              </p>
            ))}
        </div>

        {/* 热门专业 chips */}
        <div className="mb-8 flex flex-wrap gap-1.5">
          {POPULAR_MAJORS.filter((m) => majorNames.length === 0 || majorNames.includes(m)).map(
            (m) => (
              <button
                key={m}
                onClick={() => {
                  setInput(m);
                  setMajor(m);
                }}
                className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                  major === m
                    ? "border-brand-400 bg-brand-100 text-brand-700"
                    : "border-paper-300 bg-white text-ink-500 hover:border-brand-300 hover:text-brand-600"
                }`}
              >
                {m}
              </button>
            ),
          )}
        </div>

        {/* 结果 */}
        {isLoading && <LoadingState text="正在聚合专业数据…" />}
        {error && (
          <EmptyState
            title="查询失败"
            description="请稍后重试，或换个专业名试试。"
          />
        )}
        {data && !isLoading && <ProspectResult data={data} />}

        {/* 未选择专业时的引导 */}
        {!major && !isLoading && (
          <div className="rounded-xl border border-dashed border-paper-300 bg-white/60 p-8 text-center">
            <Telescope className="mx-auto mb-3 h-8 w-8 text-ink-300" />
            <p className="text-sm text-ink-400">
              输入你的专业，看看它通往哪些行业、岗位和院校
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
