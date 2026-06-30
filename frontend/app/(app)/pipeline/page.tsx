"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RefreshCw, Trash2, Upload, Eye, CheckCircle } from "lucide-react";
import { pipelineApi } from "@/lib/api";
import { Button } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import {
  PARSE_STATUS_LABEL,
  PARSE_STATUS_COLOR,
  SOURCE_TYPE_LABEL,
  CONTENT_TYPE_LABEL,
} from "@/lib/constants";
import type { PipelineStats, ReportListItem } from "@/types";

const STATUS_TABS = ["", "pending", "parsed", "failed", "reviewed", "published"];

export default function PipelinePage() {
  const toast = useToast();
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeStatus, setActiveStatus] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const loadData = async () => {
    setLoading(true);
    try {
      const [st, list] = await Promise.all([
        pipelineApi.stats(),
        pipelineApi.reports({ status: activeStatus || undefined, page, page_size: 20 }),
      ]);
      setStats(st);
      setReports(list.items);
      setTotal(list.total);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeStatus, page]);

  const handlePublish = async (id: string) => {
    try {
      await pipelineApi.publish(id);
      toast.push("已发布", "success");
      loadData();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "发布失败", "error");
    }
  };

  const handleReparse = async (id: string) => {
    try {
      await pipelineApi.reparse(id);
      toast.push("已重新解析", "success");
      loadData();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "解析失败", "error");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await pipelineApi.deleteReport(id);
      toast.push("已删除", "success");
      loadData();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "删除失败", "error");
    }
  };

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">数据管道</h1>
          <p className="text-sm text-slate-500 mt-1">管理就业报告数据源与解析流程</p>
        </div>
        <Link href="/pipeline/ingest">
          <Button>
            <Upload className="h-4 w-4" /> 接入新数据
          </Button>
        </Link>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card text-center">
            <p className="text-2xl font-bold text-slate-700">{stats.total_reports}</p>
            <p className="text-xs text-slate-500">总报告</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-green-600">{stats.published_count}</p>
            <p className="text-xs text-slate-500">已发布</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-amber-600">{stats.pending_count}</p>
            <p className="text-xs text-slate-500">待处理</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-red-600">{stats.failed_count}</p>
            <p className="text-xs text-slate-500">失败</p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {STATUS_TABS.map((s) => (
          <button
            key={s || "all"}
            onClick={() => {
              setActiveStatus(s);
              setPage(1);
            }}
            className={`rounded-full px-3 py-1.5 text-sm transition-colors ${
              activeStatus === s
                ? "bg-brand-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {s ? PARSE_STATUS_LABEL[s] : "全部"}
          </button>
        ))}
      </div>

      <div className="card">
        {reports.length === 0 ? (
          <EmptyState title="暂无报告" description="接入新数据源后报告会显示在这里" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs text-slate-400">
                  <th className="px-3 py-2 text-left">学校</th>
                  <th className="px-3 py-2 text-left">年份</th>
                  <th className="px-3 py-2 text-left">来源</th>
                  <th className="px-3 py-2 text-left">类型</th>
                  <th className="px-3 py-2 text-left">状态</th>
                  <th className="px-3 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id} className="border-b border-slate-50">
                    <td className="px-3 py-3 font-medium text-slate-700">{r.school_name}</td>
                    <td className="px-3 py-3 text-slate-500">{r.year}</td>
                    <td className="px-3 py-3 text-slate-500">
                      {SOURCE_TYPE_LABEL[r.source_type] ?? r.source_type}
                    </td>
                    <td className="px-3 py-3 text-slate-500">
                      {r.content_type ? CONTENT_TYPE_LABEL[r.content_type] ?? r.content_type : "—"}
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className="rounded-full px-2 py-0.5 text-xs font-medium"
                        style={{
                          backgroundColor: `${PARSE_STATUS_COLOR[r.parse_status]}20`,
                          color: PARSE_STATUS_COLOR[r.parse_status],
                        }}
                      >
                        {PARSE_STATUS_LABEL[r.parse_status] ?? r.parse_status}
                      </span>
                      {r.parse_error && (
                        <p className="mt-0.5 text-xs text-red-400 truncate max-w-xs">
                          {r.parse_error}
                        </p>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-1">
                        <Link
                          href={`/pipeline/reports/${r.id}`}
                          className="p-1.5 rounded hover:bg-slate-100"
                          title="查看"
                        >
                          <Eye className="h-4 w-4 text-slate-400" />
                        </Link>
                        <button
                          onClick={() => handleReparse(r.id)}
                          className="p-1.5 rounded hover:bg-slate-100"
                          title="重新解析"
                        >
                          <RefreshCw className="h-4 w-4 text-blue-400" />
                        </button>
                        {r.parse_status !== "published" && (
                          <button
                            onClick={() => handlePublish(r.id)}
                            className="p-1.5 rounded hover:bg-slate-100"
                            title="发布"
                          >
                            <CheckCircle className="h-4 w-4 text-green-400" />
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(r.id)}
                          className="p-1.5 rounded hover:bg-red-50"
                          title="删除"
                        >
                          <Trash2 className="h-4 w-4 text-red-400" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {total > 20 && (
        <div className="flex items-center justify-center gap-2 text-sm text-slate-500">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-40"
          >
            上一页
          </button>
          <span>
            第 {page} 页
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page * 20 >= total}
            className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-40"
          >
            下一页
          </button>
        </div>
      )}
    </div>
  );
}
