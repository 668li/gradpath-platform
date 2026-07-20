"use client";

import { useEffect, useState, useCallback, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import {
  RefreshCw,
  Play,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  Clock,
  Database,
  Activity,
  Shield,
  TrendingUp,
  Zap,
} from "lucide-react";
import { crawlerApi, gradIntelApi, gradVisualizationApi } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import { Button, Badge } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Modal } from "@/components/ui/modal";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";
import type {
  CrawlerInfo,
  CrawlerRun,
  CrawlerCategory,
  CrawlerLastStatus,
} from "@/types";

// ===== 状态/分类标签与颜色映射 =====

const STATUS_LABEL: Record<NonNullable<CrawlerLastStatus>, string> = {
  success: "成功",
  failed: "失败",
  running: "运行中",
};

const STATUS_BADGE_COLOR: Record<NonNullable<CrawlerLastStatus>, "green" | "red" | "amber"> = {
  success: "green",
  failed: "red",
  running: "amber",
};

const CATEGORY_LABEL: Record<CrawlerCategory, string> = {
  grad: "考研",
  civil: "考公",
  career: "求职",
  reports: "报告",
};

// 橙色用 amber 近似
const CATEGORY_BADGE_COLOR: Record<CrawlerCategory, "blue" | "amber" | "green" | "purple"> = {
  grad: "blue",
  civil: "amber",
  career: "green",
  reports: "purple",
};

const PAGE_SIZE = 20;

export default function AdminCrawlersPage() {
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const hydrated = useAuthStore((s) => s.hydrated);

  const [crawlers, setCrawlers] = useState<CrawlerInfo[]>([]);
  const [runs, setRuns] = useState<CrawlerRun[]>([]);
  const [runsTotal, setRunsTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loadingCrawlers, setLoadingCrawlers] = useState(true);
  const [loadingRuns, setLoadingRuns] = useState(true);
  // 本地标记为"已触发运行中"的爬虫名（用于按钮变灰，直到下一次列表刷新证实状态）
  const [runningSources, setRunningSources] = useState<Set<string>>(new Set());
  const [selectedRun, setSelectedRun] = useState<CrawlerRun | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [qualityMetrics, setQualityMetrics] = useState<{
    total_runs: number;
    success_runs: number;
    failed_runs: number;
    success_rate: number;
    total_fetched: number;
    total_stored: number;
    total_duplicates: number;
    dedup_rate: number;
    store_rate: number;
    total_errors: number;
  } | null>(null);
  const [seeding, setSeeding] = useState(false);

  // ===== 数据加载 =====

  const loadCrawlers = useCallback(async () => {
    try {
      const data = await crawlerApi.list();
      setCrawlers(data);
      // 清理本地 running 标记：列表已经返回最新状态
      setRunningSources(new Set());
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载爬虫列表失败", "error");
    } finally {
      setLoadingCrawlers(false);
    }
  }, [toast]);

  const loadRuns = useCallback(async () => {
    try {
      const data = await crawlerApi.runs(page, PAGE_SIZE);
      setRuns(data.items);
      setRunsTotal(data.total);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载运行历史失败", "error");
    } finally {
      setLoadingRuns(false);
    }
  }, [page, toast]);

  // 初次加载爬虫列表
  useEffect(() => {
    loadCrawlers();
  }, [loadCrawlers]);

  // 加载运行历史（page 变化时也重新加载）
  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  // 加载数据质量指标
  const loadQualityMetrics = useCallback(async () => {
    try {
      const data = await gradVisualizationApi.getCrawlerQuality();
      setQualityMetrics(data);
    } catch {
      // 静默失败，质量指标为非关键功能
    }
  }, []);

  useEffect(() => {
    loadQualityMetrics();
  }, [loadQualityMetrics]);

  // 自动轮询：有运行中的爬虫时，每 5 秒刷新列表与历史
  const hasRunning =
    crawlers.some((c) => c.last_status === "running") ||
    runs.some((r) => r.status === "running") ||
    runningSources.size > 0;

  useEffect(() => {
    if (!hasRunning) return;
    const interval = setInterval(() => {
      loadCrawlers();
      loadRuns();
    }, 5000);
    return () => clearInterval(interval);
  }, [hasRunning, loadCrawlers, loadRuns]);

  // 非管理员重定向
  useEffect(() => {
    if (hydrated && user && !user.is_admin) {
      router.replace("/dashboard");
    }
  }, [hydrated, user, router]);

  // 手动刷新
  const refreshAll = useCallback(async () => {
    await Promise.all([loadCrawlers(), loadRuns(), loadQualityMetrics()]);
  }, [loadCrawlers, loadRuns, loadQualityMetrics]);

  // 触发爬虫运行
  const handleRun = async (sourceName: string) => {
    setRunningSources((prev) => new Set(prev).add(sourceName));
    try {
      await crawlerApi.run(sourceName);
      toast.push(`已触发爬虫：${sourceName}`, "success");
      // 立即刷新列表以获取最新状态
      await refreshAll();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "触发运行失败", "error");
      setRunningSources((prev) => {
        const next = new Set(prev);
        next.delete(sourceName);
        return next;
      });
    }
  };

  // 一键预填充暗知识
  const handleSeedDarkKnowledge = async () => {
    setSeeding(true);
    try {
      const result = await gradIntelApi.seedDarkKnowledge();
      toast.push(`暗知识预填充完成：新增 ${result.seeded} 条`, "success");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "预填充失败", "error");
    } finally {
      setSeeding(false);
    }
  };

  // 打开运行详情 Modal（同时拉取最新详情以获取完整 log）
  const handleOpenRun = (run: CrawlerRun) => {
    setSelectedRun(run);
    setModalOpen(true);
    crawlerApi
      .runDetail(run.id)
      .then((detail) => setSelectedRun(detail))
      .catch(() => {
        // 静默失败，保留列表中的数据
      });
  };

  // ===== 权限校验 =====
  if (!hydrated || !user) {
    return <LoadingState text="加载中…" />;
  }
  if (!user.is_admin) {
    return <LoadingState text="无权访问，正在跳转…" />;
  }

  const totalPages = Math.ceil(runsTotal / PAGE_SIZE) || 1;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">爬虫管理后台</h1>
          <p className="text-sm text-ink-500 mt-1">
            查看已注册爬虫、触发抓取任务、查看历史运行记录与日志
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={handleSeedDarkKnowledge}
            loading={seeding}
          >
            <Zap className="h-4 w-4" />
            预填充暗知识
          </Button>
          <Button variant="secondary" onClick={refreshAll} loading={loadingCrawlers}>
            <RefreshCw className="h-4 w-4" />
            刷新
          </Button>
        </div>
      </div>

      {/* 数据质量指标 */}
      {qualityMetrics && (
        <section className="card">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="h-5 w-5 text-brand-600" />
            <h2 className="font-display font-semibold text-ink-800">数据质量概览</h2>
            <span className="text-xs text-ink-400">（最近 {qualityMetrics.total_runs} 次运行）</span>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <QualityMetricCard
              label="成功率"
              value={`${qualityMetrics.success_rate}%`}
              sub={`${qualityMetrics.success_runs}/${qualityMetrics.total_runs}`}
              icon={<TrendingUp className="h-4 w-4 text-green-600" />}
              color={qualityMetrics.success_rate >= 80 ? "green" : qualityMetrics.success_rate >= 50 ? "amber" : "red"}
            />
            <QualityMetricCard
              label="去重率"
              value={`${qualityMetrics.dedup_rate}%`}
              sub={`${qualityMetrics.total_duplicates}/${qualityMetrics.total_fetched}`}
              icon={<Activity className="h-4 w-4 text-blue-600" />}
              color="blue"
            />
            <QualityMetricCard
              label="入库率"
              value={`${qualityMetrics.store_rate}%`}
              sub={`${qualityMetrics.total_stored}/${qualityMetrics.total_fetched}`}
              icon={<Database className="h-4 w-4 text-brand-600" />}
              color="brand"
            />
            <QualityMetricCard
              label="错误数"
              value={String(qualityMetrics.total_errors)}
              sub={`${qualityMetrics.failed_runs} 次失败`}
              icon={<AlertCircle className="h-4 w-4 text-red-600" />}
              color={qualityMetrics.total_errors > 0 ? "red" : "green"}
            />
          </div>
        </section>
      )}

      {/* 爬虫列表 */}
      <section className="card">
        <div className="flex items-center gap-2 mb-4">
          <Database className="h-5 w-5 text-brand-600" />
          <h2 className="font-display font-semibold text-ink-800">爬虫列表</h2>
          <span className="text-xs text-ink-400">（共 {crawlers.length} 个）</span>
        </div>
        {loadingCrawlers && crawlers.length === 0 ? (
          <LoadingState text="加载爬虫列表中…" />
        ) : crawlers.length === 0 ? (
          <EmptyState title="暂无已注册爬虫" description="后端未注册任何爬虫任务" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-paper-200 text-left text-xs text-ink-500">
                  <th className="px-3 py-2 font-medium">名称</th>
                  <th className="px-3 py-2 font-medium">分类</th>
                  <th className="px-3 py-2 font-medium">描述</th>
                  <th className="px-3 py-2 font-medium">最近运行</th>
                  <th className="px-3 py-2 font-medium">状态</th>
                  <th className="px-3 py-2 font-medium">入库</th>
                  <th className="px-3 py-2 font-medium text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {crawlers.map((c) => {
                  const isRunning =
                    c.last_status === "running" || runningSources.has(c.name);
                  return (
                    <tr
                      key={c.name}
                      className="border-b border-paper-100 hover:bg-paper-50/50"
                    >
                      <td className="px-3 py-3 font-mono text-ink-800">{c.name}</td>
                      <td className="px-3 py-3">
                        <Badge color={CATEGORY_BADGE_COLOR[c.category]}>
                          {CATEGORY_LABEL[c.category]}
                        </Badge>
                      </td>
                      <td className="px-3 py-3 text-ink-600 max-w-xs">
                        <span className="line-clamp-2">{c.description}</span>
                      </td>
                      <td className="px-3 py-3 text-ink-500 whitespace-nowrap">
                        {formatDate(c.last_run_at)}
                      </td>
                      <td className="px-3 py-3">
                        {c.last_status ? (
                          <Badge color={STATUS_BADGE_COLOR[c.last_status]}>
                            {STATUS_LABEL[c.last_status]}
                          </Badge>
                        ) : (
                          <Badge color="slate">未运行</Badge>
                        )}
                      </td>
                      <td className="px-3 py-3 text-ink-600">
                        {c.last_items_stored ?? "—"}
                      </td>
                      <td className="px-3 py-3 text-right">
                        <Button
                          size="sm"
                          variant={isRunning ? "secondary" : "primary"}
                          disabled={isRunning}
                          onClick={() => handleRun(c.name)}
                          loading={runningSources.has(c.name)}
                        >
                          <Play className="h-3.5 w-3.5" />
                          {isRunning ? "运行中" : "运行"}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 运行历史 */}
      <section className="card">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="h-5 w-5 text-brand-600" />
          <h2 className="font-display font-semibold text-ink-800">运行历史</h2>
          <span className="text-xs text-ink-400">（共 {runsTotal} 条）</span>
        </div>
        {loadingRuns && runs.length === 0 ? (
          <LoadingState text="加载运行历史中…" />
        ) : runs.length === 0 ? (
          <EmptyState
            title="暂无运行记录"
            description="触发任意爬虫后即可在此查看历史"
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-paper-200 text-left text-xs text-ink-500">
                    <th className="px-3 py-2 font-medium">爬虫</th>
                    <th className="px-3 py-2 font-medium">状态</th>
                    <th className="px-3 py-2 font-medium">开始时间</th>
                    <th className="px-3 py-2 font-medium">耗时</th>
                    <th className="px-3 py-2 font-medium">入库</th>
                    <th className="px-3 py-2 font-medium">错误</th>
                    <th className="px-3 py-2 font-medium text-right">详情</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <tr
                      key={r.id}
                      className="border-b border-paper-100 hover:bg-paper-50/50 cursor-pointer"
                      onClick={() => handleOpenRun(r)}
                    >
                      <td className="px-3 py-3 font-mono text-ink-800">
                        {r.source_name}
                      </td>
                      <td className="px-3 py-3">
                        <Badge color={STATUS_BADGE_COLOR[r.status]}>
                          {STATUS_LABEL[r.status]}
                        </Badge>
                      </td>
                      <td className="px-3 py-3 text-ink-500 whitespace-nowrap">
                        {formatDateTime(r.started_at)}
                      </td>
                      <td className="px-3 py-3 text-ink-600 whitespace-nowrap">
                        {formatDuration(r.duration_seconds)}
                      </td>
                      <td className="px-3 py-3 text-ink-600">{r.items_stored}</td>
                      <td className="px-3 py-3">
                        {r.error_count > 0 ? (
                          <span className="text-red-600 font-medium">
                            {r.error_count}
                          </span>
                        ) : (
                          <span className="text-ink-400">0</span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenRun(r);
                          }}
                        >
                          查看
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* 翻页 */}
            <div className="flex items-center justify-center gap-3 mt-4">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="inline-flex items-center gap-1 rounded-md border border-paper-300 px-3 py-1.5 text-sm text-ink-600 hover:bg-paper-100 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-4 w-4" />
                上一页
              </button>
              <span className="text-sm text-ink-500">
                第 {page} / {totalPages} 页
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="inline-flex items-center gap-1 rounded-md border border-paper-300 px-3 py-1.5 text-sm text-ink-600 hover:bg-paper-100 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                下一页
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </>
        )}
      </section>

      {/* 运行详情 Modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="运行详情"
        className="max-w-3xl"
      >
        {selectedRun ? (
          <div className="space-y-4">
            {/* 元信息 */}
            <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
              <MetaItem label="爬虫" value={selectedRun.source_name} />
              <MetaItem label="分类" value={selectedRun.category} />
              <MetaItem
                label="状态"
                value={
                  <Badge color={STATUS_BADGE_COLOR[selectedRun.status]}>
                    {STATUS_LABEL[selectedRun.status]}
                  </Badge>
                }
              />
              <MetaItem
                label="开始时间"
                value={formatDateTime(selectedRun.started_at)}
              />
              <MetaItem
                label="耗时"
                value={formatDuration(selectedRun.duration_seconds)}
              />
              <MetaItem
                label="完成时间"
                value={
                  selectedRun.finished_at
                    ? formatDateTime(selectedRun.finished_at)
                    : "—"
                }
              />
              <MetaItem
                label="抓取数量"
                value={String(selectedRun.items_fetched)}
              />
              <MetaItem
                label="入库数量"
                value={String(selectedRun.items_stored)}
              />
              <MetaItem
                label="重复数量"
                value={String(selectedRun.items_duplicates)}
              />
              <MetaItem
                label="错误数量"
                value={
                  <span
                    className={cn(
                      selectedRun.error_count > 0 && "text-red-600 font-medium",
                    )}
                  >
                    {selectedRun.error_count}
                  </span>
                }
              />
            </div>

            {/* 错误信息 */}
            {selectedRun.error_message && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-red-700 mb-1">
                      错误信息
                    </p>
                    <pre className="text-xs text-red-700 whitespace-pre-wrap break-words font-mono">
                      {selectedRun.error_message}
                    </pre>
                  </div>
                </div>
              </div>
            )}

            {/* 完整日志 */}
            <div>
              <p className="text-xs font-semibold text-ink-600 mb-2 flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                运行日志
              </p>
              <pre className="max-h-80 overflow-auto rounded-lg border border-paper-200 bg-paper-50 p-3 text-xs font-mono text-ink-700 whitespace-pre-wrap break-words">
                {selectedRun.log || "（无日志）"}
              </pre>
            </div>
          </div>
        ) : (
          <LoadingState text="加载详情中…" />
        )}
      </Modal>
    </div>
  );
}

// ===== 辅助组件 =====

function QualityMetricCard({
  label,
  value,
  sub,
  icon,
  color,
}: {
  label: string;
  value: string;
  sub: string;
  icon: ReactNode;
  color: "green" | "amber" | "red" | "blue" | "brand";
}) {
  const colorMap = {
    green: "bg-green-50 border-green-200",
    amber: "bg-amber-50 border-amber-200",
    red: "bg-red-50 border-red-200",
    blue: "bg-blue-50 border-blue-200",
    brand: "bg-brand-50 border-brand-200",
  };
  return (
    <div className={cn("rounded-lg border p-3", colorMap[color])}>
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-ink-500">{label}</span>
      </div>
      <p className="text-lg font-bold text-ink-800">{value}</p>
      <p className="text-xs text-ink-400">{sub}</p>
    </div>
  );
}

function MetaItem({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-ink-400">{label}</span>
      <span className="text-sm font-medium text-ink-800 mt-0.5">{value}</span>
    </div>
  );
}

// ===== 辅助函数 =====

/** 格式化日期时间：YYYY-MM-DD HH:mm:ss */
function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

/** 格式化耗时（秒）为易读形式 */
function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m${s}s`;
}
