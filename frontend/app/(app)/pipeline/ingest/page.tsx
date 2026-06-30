"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Link2, Upload, Cloud } from "lucide-react";
import { pipelineApi, employmentApi } from "@/lib/api";
import { Button, Input, Select } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type { DataSourceResponse, SchoolInfo } from "@/types";

type Mode = "url" | "file" | "api";

export default function IngestPage() {
  const router = useRouter();
  const toast = useToast();
  const [mode, setMode] = useState<Mode>("url");
  const [schools, setSchools] = useState<SchoolInfo[]>([]);
  const [sources, setSources] = useState<DataSourceResponse[]>([]);
  const [loading, setLoading] = useState(false);

  // URL 模式
  const [url, setUrl] = useState("");
  const [schoolSlug, setSchoolSlug] = useState("");
  const [year, setYear] = useState(2024);

  // API 模式
  const [apiSourceId, setApiSourceId] = useState("");

  // 文件模式
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [s, srcs] = await Promise.all([
          employmentApi.schools(),
          pipelineApi.sources(),
        ]);
        setSchools(s);
        setSources(srcs);
      } catch {
        // 加载失败时不阻塞页面，用户仍可看到表单
      }
    })();
  }, []);

  const handleSubmit = async () => {
    if (!schoolSlug) {
      toast.push("请选择学校", "error");
      return;
    }
    setLoading(true);
    try {
      if (mode === "url") {
        if (!url.trim()) {
          toast.push("请输入 URL", "error");
          setLoading(false);
          return;
        }
        await pipelineApi.ingestUrl({ school_slug: schoolSlug, year, url: url.trim() });
      } else if (mode === "file") {
        if (!file) {
          toast.push("请选择文件", "error");
          setLoading(false);
          return;
        }
        await pipelineApi.ingestFile(file, schoolSlug, year);
      } else {
        if (!apiSourceId) {
          toast.push("请选择数据源", "error");
          setLoading(false);
          return;
        }
        await pipelineApi.ingestApi({
          school_slug: schoolSlug,
          year,
          api_source_id: apiSourceId,
        });
      }
      toast.push("接入成功", "success");
      router.push("/pipeline");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "接入失败", "error");
    } finally {
      setLoading(false);
    }
  };

  const tabs: { key: Mode; label: string; icon: typeof Link2 }[] = [
    { key: "url", label: "URL 抓取", icon: Link2 },
    { key: "file", label: "文件上传", icon: Upload },
    { key: "api", label: "API 对接", icon: Cloud },
  ];

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="page-title">接入新数据</h1>
        <p className="text-sm text-slate-500 mt-1">选择数据源类型，系统会自动识别格式并解析</p>
      </div>

      <div className="flex gap-2">
        {tabs.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.key}
              onClick={() => setMode(t.key)}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                mode === t.key
                  ? "bg-brand-600 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              <Icon className="h-4 w-4" /> {t.label}
            </button>
          );
        })}
      </div>

      <div className="card space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">学校</label>
            <Select value={schoolSlug} onChange={(e) => setSchoolSlug(e.target.value)}>
              <option value="">选择学校</option>
              {schools.map((s) => (
                <option key={s.id} value={s.slug}>
                  {s.name}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">年份</label>
            <Input
              type="number"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
            />
          </div>
        </div>

        {mode === "url" && (
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">报告 URL</label>
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://career.tsinghua.edu.cn/..."
            />
          </div>
        )}

        {mode === "file" && (
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">
              上传文件（PDF/Excel/CSV）
            </label>
            <input
              type="file"
              accept=".pdf,.xlsx,.xls,.csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100"
            />
            {file && (
              <p className="mt-1 text-xs text-slate-400">
                已选择: {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>
        )}

        {mode === "api" && (
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">数据源</label>
            <Select
              value={apiSourceId}
              onChange={(e) => setApiSourceId(e.target.value)}
            >
              <option value="">选择数据源</option>
              {sources.map((s) => (
                <option key={s.id} value={s.id} disabled={!s.is_active}>
                  {s.name} {s.is_active ? "" : "(未启用)"}
                </option>
              ))}
            </Select>
            {sources.length === 0 && (
              <p className="mt-1 text-xs text-slate-400">
                暂无数据源，请先在数据源配置页添加
              </p>
            )}
          </div>
        )}

        <Button onClick={handleSubmit} loading={loading} className="w-full">
          开始接入
        </Button>
      </div>
    </div>
  );
}
