"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, School as SchoolIcon } from "lucide-react";
import { employmentApi } from "@/lib/api";
import { Button } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import type { SchoolInfo, EmploymentStats } from "@/types";

export default function ExplorePage() {
  const router = useRouter();
  const toast = useToast();
  const [schools, setSchools] = useState<SchoolInfo[]>([]);
  const [stats, setStats] = useState<EmploymentStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [schoolQuery, setSchoolQuery] = useState("");
  const [majorQuery, setMajorQuery] = useState("");
  const [majorOptions, setMajorOptions] = useState<string[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const [s, st] = await Promise.all([
          employmentApi.schools(),
          employmentApi.stats(),
        ]);
        setSchools(s);
        setStats(st);
      } catch (err) {
        toast.push(
          err instanceof Error ? err.message : "加载学校与统计数据失败",
          "error",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, [toast]);

  // 学校输入失焦时拉取对应专业列表，用于专业输入框自动补全
  const handleSchoolBlur = async () => {
    const school = schoolQuery.trim();
    if (!school) {
      setMajorOptions([]);
      return;
    }
    try {
      const list = await employmentApi.majors(school);
      setMajorOptions(list);
    } catch (err) {
      // 静默失败：补全不可用不应阻断搜索流程
      setMajorOptions([]);
      toast.push(
        err instanceof Error ? err.message : "获取专业列表失败",
        "error",
      );
    }
  };

  if (loading) return <LoadingState />;

  const handleSearch = () => {
    const school = schoolQuery.trim();
    const major = majorQuery.trim();
    if (!school || !major) return;
    const params = new URLSearchParams({
      school,
      major,
    });
    router.push(`/explore/result?${params.toString()}`);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">去向探索</h1>
        <p className="text-sm text-slate-500 mt-1">
          搜索高校专业的毕业去向分布、重点单位排名和趋势
        </p>
      </div>

      {/* 搜索栏 */}
      <div className="card">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-500 mb-1">学校</label>
            <input
              type="text"
              value={schoolQuery}
              onChange={(e) => setSchoolQuery(e.target.value)}
              onBlur={handleSchoolBlur}
              placeholder="如：清华大学"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-400 focus:outline-none"
              list="school-list"
            />
            <datalist id="school-list">
              {schools.map((s) => <option key={s.id} value={s.name} />)}
            </datalist>
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-500 mb-1">专业</label>
            <input
              type="text"
              value={majorQuery}
              onChange={(e) => setMajorQuery(e.target.value)}
              placeholder="如：机械工程"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-400 focus:outline-none"
              list="major-list"
            />
            <datalist id="major-list">
              {majorOptions.map((m) => <option key={m} value={m} />)}
            </datalist>
          </div>
          <div className="flex items-end">
            <Button
              disabled={!schoolQuery || !majorQuery}
              onClick={handleSearch}
            >
              <Search className="h-4 w-4" /> 搜索
            </Button>
          </div>
        </div>
      </div>

      {/* 全局统计 */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="card text-center">
            <p className="text-2xl font-bold text-brand-600">{stats.school_count}</p>
            <p className="text-xs text-slate-500">已收录高校</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-green-600">{stats.report_count}</p>
            <p className="text-xs text-slate-500">就业报告</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-amber-600">{stats.major_count}</p>
            <p className="text-xs text-slate-500">专业数据</p>
          </div>
        </div>
      )}

      {/* 已收录学校列表 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4">已收录高校</h2>
        {schools.length === 0 ? (
          <EmptyState title="暂无数据" description="尚未收录任何高校就业报告" />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {schools.map((s) => (
              <div
                key={s.id}
                className="rounded-lg border border-slate-100 p-4 hover:border-brand-200 transition-colors"
              >
                <div className="flex items-center gap-2 mb-2">
                  <SchoolIcon className="h-4 w-4 text-brand-500" />
                  <span className="font-medium text-slate-800">{s.name}</span>
                </div>
                <p className="text-xs text-slate-400">
                  {s.report_count} 份报告 · {s.major_count} 个专业
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
