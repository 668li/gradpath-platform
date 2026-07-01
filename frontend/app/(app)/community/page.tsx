"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Send, Trash2, BarChart3, Users, School as SchoolIcon } from "lucide-react";
import { employmentApi, communityApi } from "@/lib/api";
import { Button, Input, Select } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Pagination } from "@/components/ui/pagination";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";
import {
  COMMUNITY_DESTINATION_TYPES,
  DEGREE_OPTIONS,
  DEGREE_LABEL,
  SALARY_RANGE_OPTIONS,
  SALARY_RANGE_LABEL,
  RATE_LABEL,
} from "@/lib/constants";
import type {
  SchoolInfo,
  CommunityReport,
  CommunityStats,
  CommunitySubmit,
} from "@/types";

const YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025];

/** 将中文编码为 Base64 并 URL 编码，用于 URL 参数传递 */
function encodeParam(value: string): string {
  return encodeURIComponent(btoa(unescape(encodeURIComponent(value))));
}

export default function CommunityPage() {
  const router = useRouter();
  const toast = useToast();

  const [schools, setSchools] = useState<SchoolInfo[]>([]);
  const [stats, setStats] = useState<CommunityStats | null>(null);
  const [myReports, setMyReports] = useState<CommunityReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const PAGE_SIZE = 20;

  // 分页加载“我的提交记录”
  const loadMyReports = useCallback(
    async (targetPage: number) => {
      try {
        let target = targetPage;
        let data = await communityApi.myReports({
          page: target,
          page_size: PAGE_SIZE,
        });
        // 若目标页为空且非首页，回退到首页
        if (data.items.length === 0 && target > 1) {
          target = 1;
          data = await communityApi.myReports({
            page: 1,
            page_size: PAGE_SIZE,
          });
        }
        setMyReports(data.items);
        setTotal(data.total);
        setPage(target);
      } catch (err) {
        toast.push(
          err instanceof Error ? err.message : "加载失败",
          "error",
        );
      }
    },
    [toast],
  );

  // 表单状态
  const [schoolName, setSchoolName] = useState("");
  const [major, setMajor] = useState("");
  const [graduationYear, setGraduationYear] = useState<number>(2024);
  const [degree, setDegree] = useState("bachelor");
  const [destinationType, setDestinationType] = useState("employment");
  const [employer, setEmployer] = useState("");
  const [city, setCity] = useState("");
  const [industry, setIndustry] = useState("");
  const [salaryRange, setSalaryRange] = useState("");
  const [majorOptions, setMajorOptions] = useState<string[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const [s, st, mine] = await Promise.all([
          employmentApi.schools(),
          communityApi.stats(),
          communityApi.myReports({ page: 1, page_size: PAGE_SIZE }),
        ]);
        setSchools(s);
        setStats(st);
        setMyReports(mine.items);
        setTotal(mine.total);
      } catch (err) {
        toast.push(
          err instanceof Error ? err.message : "加载数据失败",
          "error",
        );
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toast]);

  // 学校失焦时拉取对应专业列表，用于专业自动补全（静默失败）
  const handleSchoolBlur = async () => {
    const school = schoolName.trim();
    if (!school) {
      setMajorOptions([]);
      return;
    }
    try {
      const list = await employmentApi.majors(school);
      setMajorOptions(list);
    } catch {
      setMajorOptions([]);
    }
  };

  const resetDynamicFields = () => {
    setEmployer("");
    setCity("");
    setIndustry("");
    setSalaryRange("");
  };

  const refreshStats = async () => {
    try {
      const st = await communityApi.stats();
      setStats(st);
    } catch {
      // 静默失败：统计刷新不阻断主流程
    }
  };

  const handleSubmit = async () => {
    const sn = schoolName.trim();
    const m = major.trim();
    if (!sn || !m) {
      toast.push("请填写学校和专业", "error");
      return;
    }

    const body: CommunitySubmit = {
      school_name: sn,
      major: m,
      graduation_year: graduationYear,
      degree,
      destination_type: destinationType,
    };

    // 根据去向类型组装可选字段
    if (destinationType === "employment") {
      if (employer.trim()) body.employer = employer.trim();
      if (city.trim()) body.city = city.trim();
      if (industry.trim()) body.industry = industry.trim();
      if (salaryRange) body.salary_range = salaryRange;
    } else if (destinationType === "further_study") {
      // 升学学校填在 employer 字段
      if (employer.trim()) body.employer = employer.trim();
    } else {
      // 考公 / 出国 / 创业 / 间隔年：仅城市
      if (city.trim()) body.city = city.trim();
    }

    setSubmitting(true);
    try {
      await communityApi.submit(body);
      toast.push("提交成功，感谢你的分享！", "success");
      resetDynamicFields();
      loadMyReports(page);
      refreshStats();
    } catch (err) {
      toast.push(
        err instanceof Error ? err.message : "提交失败",
        "error",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await communityApi.remove(id);
      toast.push("已删除该记录", "success");
      loadMyReports(page);
      refreshStats();
    } catch (err) {
      toast.push(
        err instanceof Error ? err.message : "删除失败",
        "error",
      );
    }
  };

  // 跳转到同校同专业的社区聚合结果页
  const handleViewAggregate = () => {
    const sn = schoolName.trim();
    const m = major.trim();
    if (!sn || !m) {
      toast.push("请先填写学校和专业", "info");
      return;
    }
    const s = encodeParam(sn);
    const mm = encodeParam(m);
    router.push(`/community/result?s=${s}&m=${mm}`);
  };

  if (loading) return <LoadingState />;

  // 动态字段渲染配置
  const showEmployerField =
    destinationType === "employment" || destinationType === "further_study";
  const showCityField =
    destinationType === "employment" ||
    destinationType === "civil_service" ||
    destinationType === "abroad" ||
    destinationType === "startup" ||
    destinationType === "gap_year";
  const showIndustryField = destinationType === "employment";
  const showSalaryField = destinationType === "employment";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">社区数据</h1>
        <p className="text-sm text-slate-500 mt-1">
          匿名分享你的毕业去向，聚合后与官方数据互补，帮助学弟学妹做出更明智的决策
        </p>
      </div>

      {/* 社区统计 */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="card text-center">
            <p className="text-2xl font-bold text-brand-600">
              {stats.total_reports}
            </p>
            <p className="text-xs text-slate-500">社区样本</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-green-600">
              {stats.school_count}
            </p>
            <p className="text-xs text-slate-500">覆盖学校</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-amber-600">
              {stats.major_count}
            </p>
            <p className="text-xs text-slate-500">覆盖专业</p>
          </div>
        </div>
      )}

      {/* 提交表单 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <Users className="h-4 w-4 text-brand-500" />
          匿名提交去向报告
        </h2>

        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                学校 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={schoolName}
                onChange={(e) => setSchoolName(e.target.value)}
                onBlur={handleSchoolBlur}
                placeholder="如：清华大学"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                list="community-school-list"
              />
              <datalist id="community-school-list">
                {schools.map((s) => (
                  <option key={s.id} value={s.name} />
                ))}
              </datalist>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                专业 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={major}
                onChange={(e) => setMajor(e.target.value)}
                placeholder="如：机械工程"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                list="community-major-list"
              />
              <datalist id="community-major-list">
                {majorOptions.map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                毕业年份 <span className="text-red-500">*</span>
              </label>
              <Select
                value={graduationYear}
                onChange={(e) => setGraduationYear(Number(e.target.value))}
              >
                {YEARS.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                学历 <span className="text-red-500">*</span>
              </label>
              <Select
                value={degree}
                onChange={(e) => setDegree(e.target.value)}
              >
                {DEGREE_OPTIONS.map((d) => (
                  <option key={d.value} value={d.value}>
                    {d.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {/* 去向类型单选 */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-2">
              去向类型 <span className="text-red-500">*</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {COMMUNITY_DESTINATION_TYPES.map((t) => {
                const active = destinationType === t;
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => {
                      setDestinationType(t);
                      resetDynamicFields();
                    }}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-sm transition-colors",
                      active
                        ? "border-brand-500 bg-brand-50 text-brand-700"
                        : "border-slate-200 bg-white text-slate-600 hover:border-brand-300 hover:text-brand-600",
                    )}
                  >
                    {RATE_LABEL[t] ?? t}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 动态额外字段 */}
          {(showEmployerField ||
            showCityField ||
            showIndustryField ||
            showSalaryField) && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 rounded-lg bg-slate-50 p-4">
              {showEmployerField && (
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">
                    {destinationType === "further_study"
                      ? "升学学校"
                      : "雇主 / 单位"}
                  </label>
                  <Input
                    value={employer}
                    onChange={(e) => setEmployer(e.target.value)}
                    placeholder={
                      destinationType === "further_study"
                        ? "如：北京大学"
                        : "如：腾讯"
                    }
                  />
                </div>
              )}
              {showCityField && (
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">
                    城市
                  </label>
                  <Input
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    placeholder="如：深圳"
                  />
                </div>
              )}
              {showIndustryField && (
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">
                    行业
                  </label>
                  <Input
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    placeholder="如：互联网"
                  />
                </div>
              )}
              {showSalaryField && (
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">
                    薪资范围
                  </label>
                  <Select
                    value={salaryRange}
                    onChange={(e) => setSalaryRange(e.target.value)}
                  >
                    <option value="">选择薪资范围</option>
                    {SALARY_RANGE_OPTIONS.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </Select>
                </div>
              )}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Button onClick={handleSubmit} loading={submitting}>
              <Send className="h-4 w-4" /> 提交报告
            </Button>
            <Button variant="secondary" onClick={handleViewAggregate}>
              <BarChart3 className="h-4 w-4" /> 查看聚合结果
            </Button>
            <span className="text-xs text-slate-400">
              数据完全匿名，仅用于聚合统计
            </span>
          </div>
        </div>
      </div>

      {/* 我的提交记录 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4">我的提交记录</h2>
        {myReports.length === 0 ? (
          <EmptyState
            title="暂无提交记录"
            description="提交你的第一份去向报告，它会出现在这里"
          />
        ) : (
          <div className="space-y-3">
            {myReports.map((r) => (
              <div
                key={r.id}
                className="rounded-lg border border-slate-100 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="inline-flex items-center gap-1 font-medium text-slate-800">
                        <SchoolIcon className="h-3.5 w-3.5 text-brand-500" />
                        {r.school_name} · {r.major}
                      </span>
                      <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
                        {RATE_LABEL[r.destination_type] ?? r.destination_type}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      {r.graduation_year}届 · {DEGREE_LABEL[r.degree] ?? r.degree}
                      {r.employer ? ` · ${r.employer}` : ""}
                      {r.city ? ` · ${r.city}` : ""}
                      {r.industry ? ` · ${r.industry}` : ""}
                      {r.salary_range
                        ? ` · ${SALARY_RANGE_LABEL[r.salary_range] ?? r.salary_range}`
                        : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Link
                      href={`/community/result?s=${encodeParam(r.school_name)}&m=${encodeParam(r.major)}`}
                      className="text-xs text-brand-600 hover:underline"
                    >
                      查看聚合
                    </Link>
                    <button
                      onClick={() => handleDelete(r.id)}
                      className="flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                      aria-label="删除记录"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          onPageChange={(p) => loadMyReports(p)}
        />
      </div>
    </div>
  );
}
