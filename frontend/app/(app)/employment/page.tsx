"use client";

import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import InterviewExperience from "@/app/(app)/interview/page";
import { failureCaseApi } from "@/lib/api/failure-case";
import type { FailureCaseResponse } from "@/types/failure-case";
import { AlertTriangle, MessageSquare, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { careerIntelApi } from "@/lib/api/ai";
import { employmentApi, type MarketOverview, type SchoolReportItem, type EmploymentSearchData, type EmploymentAnnounceItem } from "@/lib/api/employment";
import { useToast } from "@/components/ui/toast";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { ListSkeleton } from "@/components/ui/skeleton";
import type {
} from "@/types";

// ===== Tab 配置（面试经验与失败案例已合并为面经库单一入口） =====
const tabs = [
  { id: "interview", label: "面经库", icon: MessageSquare, color: "text-cyan-700", desc: "面试经验与失败案例，一站式查阅与提交" },
  { id: "market", label: "就业市场", icon: BarChart3, color: "text-emerald-700", desc: "库内真实公司库与城市岗位薪资聚合，覆盖度如实标注" },
];

const importanceColors: Record<string, string> = {
  critical: "border-red-200 bg-red-50/40",
  high: "border-orange-200 bg-orange-50/40",
  medium: "border-blue-200 bg-blue-50/40",
  low: "border-paper-200",
};

const importanceBadges: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-blue-100 text-blue-700",
  low: "bg-paper-100 text-ink-500",
};

const importanceLabels: Record<string, string> = {
  critical: "关键",
  high: "重要",
  medium: "一般",
  low: "参考",
};

// ===== Tab: 面经库（面试经验 + 失败案例，合并为单一入口） =====
function InterviewTab() {
  const [cases, setCases] = useState<FailureCaseResponse[]>([]);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    failureCaseApi
      .list({ page: 1, size: 5 })
      .then((d) => {
        setCases(d.items);
        setTotal(d.total);
      })
      .catch(() => {});
  }, []);

  const pathLabel: Record<string, string> = {
    kaoyan: "考研",
    civil_service: "考公",
    employment: "就业",
    study_abroad: "留学",
  };

  return (
    <div className="space-y-8">
      <InterviewExperience />

      <section className="rounded-xl border border-paper-200 bg-white p-5">
        <div className="mb-3 flex items-center justify-between gap-2">
          <h3 className="flex items-center gap-2 font-bold text-ink-800">
            <AlertTriangle className="h-5 w-5 text-rose-500" /> 失败案例（{total}）
          </h3>
          <Link href="/failure-cases/new" className="text-sm text-brand-600 hover:underline">
            分享我的失败案例
          </Link>
        </div>
        {cases.length === 0 ? (
          <div className="rounded-lg bg-paper-50 p-4">
            <p className="text-sm text-ink-500">
              还没有已审核的失败案例——这里是全站空位。真实教训和成功经验一样值钱，你的踩坑复盘可能正是别人缺的那块拼图。
            </p>
            <p className="mt-1.5 text-xs text-ink-400">
              点右上角「分享我的失败案例」，匿名提交，审核通过后公开展示。
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-paper-100">
            {cases.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/failure-cases/${c.id}`}
                  className="-mx-2 block rounded-lg px-2 py-3 hover:bg-paper-50"
                >
                  <p className="text-sm font-medium text-ink-800">{c.title}</p>
                  <p className="mt-0.5 line-clamp-2 text-xs text-ink-500">
                    {c.lessons[0] ?? c.what_would_i_do}
                  </p>
                  <p className="mt-1 text-[11px] text-ink-400">
                    {c.author_role} · {pathLabel[c.path_type] ?? c.path_type} · 有帮助 {c.helpful_count}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

// ===== Tab: 就业市场（B4：companies/salary_benchmarks 真实聚合，覆盖度如实） =====
function MarketTab() {
  const [data, setData] = useState<MarketOverview | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    employmentApi
      .marketOverview()
      .then(setData)
      .catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <EmptyState
        title="就业市场数据加载失败"
        description="稍后重试；数据来自库内真实公司库与岗位薪资表。"
      />
    );
  }
  if (!data) return <ListSkeleton count={5} />;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="rounded-xl border border-paper-200 bg-white p-4">
          <p className="text-2xl font-bold text-ink-800">{data.company_total}</p>
          <p className="text-xs text-ink-500">公司库企业</p>
        </div>
        <div className="rounded-xl border border-paper-200 bg-white p-4">
          <p className="text-2xl font-bold text-ink-800">{data.salary_total}</p>
          <p className="text-xs text-ink-500">岗位薪资样本</p>
        </div>
        <div className="rounded-xl border border-paper-200 bg-white p-4">
          <p className="text-2xl font-bold text-ink-800">
            {data.school_employment_coverage}
            <span className="text-sm text-ink-400">/{data.school_total}</span>
          </p>
          <p className="text-xs text-ink-500">院校就业率有值覆盖</p>
        </div>
        <div className="rounded-xl border border-paper-200 bg-white p-4">
          <p className="text-2xl font-bold text-ink-800">{data.city_salary_bands.length}</p>
          <p className="text-xs text-ink-500">覆盖城市</p>
        </div>
      </div>

      <section className="rounded-xl border border-paper-200 bg-white p-5">
        <h3 className="mb-1 font-bold text-ink-800">行业公司分布（Top {data.top_industries.length}）</h3>
        <p className="mb-3 text-xs text-ink-400">
          公司库以财富 500 强及大型上市企业为主——行业分布反映头部企业结构，不代表全市场口径，如实标注。
        </p>
        {data.top_industries.length === 0 ? (
          <p className="text-sm text-ink-400">暂无行业分布数据。</p>
        ) : (
          <ul className="space-y-2">
            {data.top_industries.map((i) => (
              <li key={i.industry} className="flex items-center justify-between text-sm">
                <span className="text-ink-600">{i.industry}</span>
                <span className="tabular-nums text-ink-400">{i.count} 家</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-xl border border-paper-200 bg-white p-5">
        <h3 className="mb-1 font-bold text-ink-800">城市岗位年薪带宽</h3>
        <p className="mb-3 text-xs text-ink-400">
          样本来自各城市人社局《人力资源市场工资价位》（全职业年口径，区间 = P10 低位至 P90 高位），单位：万元/年；城市覆盖有限时如实留空。
        </p>
        {data.city_salary_bands.length === 0 ? (
          <p className="text-sm text-ink-400">暂无城市薪资样本。</p>
        ) : (
          <ul className="space-y-2">
            {data.city_salary_bands.map((c) => (
              <li key={c.city} className="flex items-center justify-between text-sm">
                <span className="text-ink-600">
                  {c.city}
                  <span className="ml-2 text-xs text-ink-400">{c.sample_count} 条样本</span>
                </span>
                <span className="tabular-nums text-ink-500">
                  {c.min_wan != null && c.max_wan != null ? `${c.min_wan} – ${c.max_wan} 万/年` : "—"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-xl border border-paper-200 bg-white p-5">
        <h3 className="mb-1 font-bold text-ink-800">院校就业率（有值院校如实列出）</h3>
        <p className="mb-3 text-xs text-ink-400">
          全库 {data.school_total} 所院校中仅 {data.school_employment_coverage} 所有就业率数据——覆盖度如实展示，不补数。
        </p>
        {data.school_employment_samples.length === 0 ? (
          <p className="text-sm text-ink-400">暂无院校就业率数据。</p>
        ) : (
          <ul className="divide-y divide-paper-100">
            {data.school_employment_samples.map((s) => (
              <li key={s.name} className="flex items-center justify-between py-2 text-sm">
                <span className="text-ink-600">{s.name}</span>
                <span className="tabular-nums text-ink-500">
                  就业率 {s.employment_rate != null ? `${s.employment_rate}%` : "—"}
                  {s.grad_school_rate != null ? ` · 考研率 ${s.grad_school_rate}%` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <AnnouncesSection />

      <SchoolReportsSection />
    </div>
  );
}

// ===== 院校就业报告浏览（EMP-1c，2026-09-30）：消费既有 schools/search 端点 =====
const degreeLabels: Record<string, string> = {
  bachelor: "本科",
  master: "硕士",
  phd: "博士",
  all: "全校",
};

function pct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${Number(v).toFixed(1)}%`;
}

function SchoolReportsSection() {
  const [schools, setSchools] = useState<SchoolReportItem[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [openSchool, setOpenSchool] = useState<string | null>(null);
  const [detail, setDetail] = useState<EmploymentSearchData | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    employmentApi
      .schoolsReports()
      .then(setSchools)
      .catch(() => setFailed(true));
  }, []);

  const toggle = (name: string) => {
    if (openSchool === name) {
      setOpenSchool(null);
      setDetail(null);
      return;
    }
    setOpenSchool(name);
    setDetail(null);
    setDetailLoading(true);
    employmentApi
      .schoolReportDetail(name)
      .then((d) => setDetail(d))
      .catch(() => setFailed(true))
      .finally(() => setDetailLoading(false));
  };

  if (failed) {
    return (
      <section className="rounded-xl border border-paper-200 bg-white p-5">
        <h3 className="mb-2 font-bold text-ink-800">院校就业报告</h3>
        <p className="text-sm text-ink-400">报告列表加载失败，稍后重试。</p>
      </section>
    );
  }
  if (!schools) return <ListSkeleton count={4} />;

  return (
    <section className="rounded-xl border border-paper-200 bg-white p-5">
      <h3 className="mb-1 font-bold text-ink-800">院校就业报告（{schools.length} 所）</h3>
      <p className="mb-3 text-xs text-ink-400">
        各校官方就业质量年度报告的解析数据——点击院校查看毕业去向、雇主排行与报告原文；覆盖 {schools.length} 所院校，未覆盖的院校如实不列。
      </p>
      <ul className="divide-y divide-paper-100">
        {schools.map((s) => {
          const open = openSchool === s.name;
          return (
            <li key={s.id}>
              <button
                onClick={() => toggle(s.name)}
                aria-expanded={open}
                className="-mx-2 flex w-full items-center justify-between rounded-lg px-2 py-3 text-left hover:bg-paper-50"
              >
                <span className="text-sm font-medium text-ink-800">{s.name}</span>
                <span className="text-xs text-ink-400">
                  {s.report_count} 份报告 · {s.major_count} 个专业口径 {open ? "▲" : "▼"}
                </span>
              </button>
              {open && (
                <div className="mb-3 ml-2 space-y-2 border-l-2 border-paper-200 pl-4">
                  {detailLoading && <ListSkeleton count={2} />}
                  {!detailLoading && detail && detail.records.length === 0 && (
                    <p className="text-xs text-ink-400">该院校暂无已解析的就业数据行（报告可能仅存原文）。</p>
                  )}
                  {!detailLoading &&
                    detail?.records.map((r, idx) => (
                      <div key={idx} className="rounded-lg bg-paper-50 p-3 text-xs">
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                          <span className="font-semibold text-ink-700">{r.year} 年</span>
                          <span className="text-ink-500">{degreeLabels[r.degree] ?? r.degree}</span>
                          {r.total_graduates != null && (
                            <span className="text-ink-500">毕业生 {r.total_graduates.toLocaleString()} 人</span>
                          )}
                          <span className="text-ink-500">就业率 {pct(r.rates?.employment)}</span>
                          <span className="text-ink-500">深造率 {pct(r.rates?.further_study)}</span>
                        </div>
                        {r.employer_ranking?.length > 0 && (
                          <p className="mt-1.5 text-ink-400">
                            主要雇主：{r.employer_ranking.slice(0, 3).map((e) => e.name).filter(Boolean).join("、")}
                          </p>
                        )}
                        {r.source_url && (
                          <a
                            href={r.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-1.5 inline-flex items-center gap-1 text-brand-600 hover:underline"
                          >
                            查看报告原文（校方官网） ↗
                          </a>
                        )}
                      </div>
                    ))}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

// ===== 官方就业公告（EMP-3，2026-09-30）：公开只读端点消费，只出已审核条目 =====
function AnnouncesSection() {
  const [items, setItems] = useState<EmploymentAnnounceItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    employmentApi
      .announces(1, 20)
      .then((d) => {
        setItems(d.items);
        setTotal(d.total);
      })
      .catch(() => setFailed(true));
  }, []);

  return (
    <section className="rounded-xl border border-paper-200 bg-white p-5">
      <h3 className="mb-1 font-bold text-ink-800">官方就业公告</h3>
      <p className="mb-3 text-xs text-ink-400">
        高校就业网官方通知直采（校招公告/宣讲会/双选会/选调通知），全部经人工审核后展示——
        每条都可溯源到校方官网原文。
      </p>
      {failed ? (
        <p className="text-sm text-ink-400">公告加载失败，稍后重试。</p>
      ) : !items ? (
        <ListSkeleton count={3} />
      ) : items.length === 0 ? (
        <div className="rounded-lg bg-paper-50 p-4">
          <p className="text-sm text-ink-500">
            官方公告线已接入（首批覆盖山东大学/中南大学/河北工业大学/华东理工大学就业网），
            首批条目正在审核中——审核通过后此处实时可见，不会用转载内容充数。
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-paper-100">
          {items.map((a) => (
            <li key={a.source_url}>
              <a
                href={a.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="-mx-2 block rounded-lg px-2 py-3 hover:bg-paper-50"
              >
                <p className="text-sm font-medium text-ink-800">{a.title}</p>
                <p className="mt-0.5 text-[11px] text-ink-400">
                  {a.source_name ?? "高校就业网"} · {a.published_at ?? "日期以原文为准"}
                </p>
              </a>
            </li>
          ))}
        </ul>
      )}
      {items != null && total > items.length && (
        <p className="mt-2 text-right text-xs text-ink-400">共 {total} 条，展示最新 {items.length} 条</p>
      )}
    </section>
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
  const activeTab = searchParams.get("tab") || "interview";
  const current = tabs.find((t) => t.id === activeTab) || tabs[0];

  const handleTabChange = (id: string) => {
    router.push(`/employment?tab=${id}`);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-ink-800 mb-2">就业中心</h1>
        <p className="text-ink-500">面经库 · 失败案例 · 就业市场 · 院校就业报告</p>
      </div>

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

      <div className="mb-6">
        <p className="text-sm text-ink-500">{current.desc}</p>
      </div>

      <div>
        {activeTab === "interview" && <InterviewTab />}
        {activeTab === "market" && <MarketTab />}
      </div>
    </div>
  );
}
