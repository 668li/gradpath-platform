"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Plus,
  Pencil,
  Trash2,
  ClipboardList,
  CheckCircle2,
  ArrowRight,
} from "lucide-react";
import { retrospectivesApi } from "@/lib/api";
import { formatDate, levelStars } from "@/lib/utils";
import { PERIOD_TYPE_LABEL } from "@/lib/constants";
import { Modal } from "@/components/ui/modal";
import { EmptyState } from "@/components/ui/empty";
import { Badge, Button } from "@/components/ui/form-controls";
import { Skeleton } from "@/components/ui/skeleton";
import { Pagination } from "@/components/ui/pagination";
import { useToast } from "@/components/ui/toast";
import { RetroForm } from "@/components/retro-form";
import { RetroAIPanel } from "@/components/retro-ai-panel";
import type { AIRetroDraft, RetrospectiveResponse } from "@/types";

/** 阶段复盘示例模板（空态引导，点「以此为例」预填表单） */
const RETRO_TEMPLATES: { title: string; period_type: string; achievements: string[]; challenges: string; next_steps: string[] }[] = [
  {
    title: "2025 春季学期复盘",
    period_type: "semester",
    achievements: [
      "考研数学一轮复习完成（高数+线代+概率，基础题正确率 80%+）",
      "英语真题刷完 2010-2020 共 11 年，阅读错到每篇 1-2 个",
      "拿到一段暑期大厂后端实习 offer（return 意向）",
      "维持了每周 3 次、每次 5 公里跑步",
    ],
    challenges: "专业课（408）起步晚，5 月才正式开始，前期进度焦虑明显；时间分配不够科学，常把整块时间留给数学而压缩英语背诵，导致政治完全没碰。",
    next_steps: [
      "暑期集中攻克 408 四门课，按数据结构→计组→操作系统→计网顺序过完一轮",
      "每天固定 2 小时数学错题复盘（建错题本，按知识点归类）",
      "7 月起每天 30 分钟政治基础课（徐涛强化班）+ 8 月启动英语作文模板",
    ],
  },
  {
    title: "秋招月度复盘",
    period_type: "month",
    achievements: [
      "投递 30 家（含 12 家大厂/独角兽），笔试通过 12 家进入面试",
      "算法题稳定到中等难度（LeetCode 每日 2 题，周赛稳定 2-3 题）",
      "简历迭代 3 版（从 2 页精简到 1 页，项目量化指标补全）",
      "拿到 2 个口头 offer（一家中厂、一家 startup）",
    ],
    challenges: "面试表达卡顿，项目亮点讲不深（被追问技术选型理由时答不上来）；八股记忆碎片化，OS 和计网知识点容易混淆，缺乏体系化串联。",
    next_steps: [
      "每周 2 场模拟面试（找同学互面 + 录音复盘表达节奏）",
      "深挖 1 个项目到能讲 20 分钟（覆盖背景/难点/选型/复盘四段）",
      "系统整理八股笔记（按『问题→原理→源码/例子→对比』模板重建成知识网）",
    ],
  },
];

export default function RetrospectivesPage() {
  const toast = useToast();
  const [retros, setRetros] = useState<RetrospectiveResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<RetrospectiveResponse | null>(null);
  const [aiDraftData, setAiDraftData] = useState<{
    draft: AIRetroDraft;
    periodStart: string;
    periodEnd: string;
  } | null>(null);

  const PAGE_SIZE = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await retrospectivesApi.list({ page, page_size: PAGE_SIZE });
      setRetros(list.items);
      setTotal(list.total);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  /** 用示例模板预填复盘表单（不写库，仅作为创建起点） */
  const useTemplate = (tpl: typeof RETRO_TEMPLATES[number]) => {
    const today = new Date().toISOString().slice(0, 10);
    const start = new Date(Date.now() - 90 * 86400000).toISOString().slice(0, 10);
    setEditing({
      id: "",
      user_id: "",
      title: tpl.title,
      period_type: tpl.period_type as RetrospectiveResponse["period_type"],
      period_start: start,
      period_end: today,
      achievements: tpl.achievements,
      challenges: tpl.challenges,
      lessons_learned: "",
      next_steps: tpl.next_steps,
      satisfaction: 4,
      created_at: "",
      updated_at: "",
    } as unknown as RetrospectiveResponse);
    setAiDraftData(null);
    setModalOpen(true);
  };

  const openCreate = () => {
    setEditing(null);
    setAiDraftData(null);
    setModalOpen(true);
  };

  const openEdit = (r: RetrospectiveResponse) => {
    setEditing(r);
    setAiDraftData(null);
    setModalOpen(true);
  };

  const handleSaved = () => {
    setModalOpen(false);
    setEditing(null);
    setAiDraftData(null);
    load();
  };

  const handleUseDraft = (
    draft: AIRetroDraft,
    period: { start: string; end: string },
  ) => {
    setAiDraftData({
      draft,
      periodStart: period.start,
      periodEnd: period.end,
    });
    setEditing(null);
    setModalOpen(true);
  };

  const handleDelete = async (r: RetrospectiveResponse) => {
    if (!window.confirm(`确认删除复盘「${r.title}」？`)) return;
    try {
      await retrospectivesApi.remove(r.id);
      toast.push("删除成功", "success");
      load();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "删除失败", "error");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">阶段复盘</h1>
          <p className="text-sm text-slate-500 mt-1">
            定期回顾，沉淀经验，规划下一步
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" /> 新建复盘
        </Button>
      </div>

      <RetroAIPanel onUseDraft={handleUseDraft} />

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={`skel-${i}`} className="card space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 min-w-0">
                  <Skeleton className="h-10 w-10 rounded-lg shrink-0" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-2/3" />
                    <div className="flex items-center gap-2">
                      <Skeleton className="h-5 w-12 rounded" />
                      <Skeleton className="h-3 w-24" />
                    </div>
                  </div>
                </div>
                <div className="flex gap-1 shrink-0">
                  <Skeleton className="h-7 w-7 rounded-md" />
                  <Skeleton className="h-7 w-7 rounded-md" />
                </div>
              </div>
              <div className="space-y-2">
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-5/6" />
                <Skeleton className="h-3 w-3/4" />
              </div>
              <div className="pt-3 border-t border-slate-100 flex items-center gap-2">
                <Skeleton className="h-3 w-12" />
                <Skeleton className="h-3 w-20" />
              </div>
            </div>
          ))}
        </div>
      ) : retros.length === 0 ? (
        <>
          <EmptyState
            title="还没有复盘记录"
            description="创建你的第一次阶段性复盘，可基于事件自动生成草稿"
            action={
              <Button onClick={openCreate}>
                <Plus className="h-4 w-4" /> 创建复盘
              </Button>
            }
          />
          <section className="space-y-3">
            <p className="flex items-center gap-2 text-sm font-medium text-ink-600">
              <ClipboardList className="h-4 w-4 text-brand-500" />
              看看一份完整复盘长什么样（点「以此为例」快速套用）
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {RETRO_TEMPLATES.map((tpl, i) => (
                <div
                  key={i}
                  className="card flex flex-col gap-3 border-dashed border-brand-200 bg-brand-50/30"
                >
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-semibold text-ink-800">{tpl.title}</h3>
                    <Badge color="purple">
                      {PERIOD_TYPE_LABEL[tpl.period_type as keyof typeof PERIOD_TYPE_LABEL] ?? tpl.period_type}
                    </Badge>
                  </div>
                  <div className="space-y-2 text-xs text-ink-500">
                    <p>
                      <span className="text-ink-400">成就：</span>
                      {tpl.achievements.slice(0, 2).join("、")}
                      {tpl.achievements.length > 2 ? "…" : ""}
                    </p>
                    <p className="line-clamp-2">
                      <span className="text-ink-400">挑战：</span>
                      {tpl.challenges}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => useTemplate(tpl)}
                    className="mt-auto"
                  >
                    以此为例
                  </Button>
                </div>
              ))}
            </div>
          </section>
        </>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {retros.map((r) => (
            <div key={r.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 min-w-0">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-50 text-purple-600 shrink-0">
                    <ClipboardList className="h-5 w-5" />
                  </span>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-slate-800 truncate">
                      {r.title}
                    </h3>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Badge color="purple">
                        {PERIOD_TYPE_LABEL[r.period_type]}
                      </Badge>
                      <span className="text-xs text-slate-400">
                        {formatDate(r.period_start)} ~ {formatDate(r.period_end)}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => openEdit(r)}
                    className="p-1.5 rounded-md text-slate-400 hover:bg-slate-100 hover:text-brand-600"
                    aria-label="编辑"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(r)}
                    className="p-1.5 rounded-md text-slate-400 hover:bg-red-50 hover:text-red-600"
                    aria-label="删除"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="mt-3 space-y-3 text-sm">
                {r.achievements.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-slate-500 mb-1">
                      成就 ({r.achievements.length})
                    </p>
                    <ul className="space-y-1">
                      {r.achievements.slice(0, 3).map((a, i) => (
                        <li
                          key={`${a}-${i}`}
                          className="flex items-start gap-1.5 text-slate-600"
                        >
                          <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0 mt-0.5" />
                          <span className="line-clamp-1">{a}</span>
                        </li>
                      ))}
                      {r.achievements.length > 3 && (
                        <li className="text-xs text-slate-400 pl-5">
                          …还有 {r.achievements.length - 3} 项
                        </li>
                      )}
                    </ul>
                  </div>
                )}

                {r.challenges && (
                  <div>
                    <p className="text-xs font-medium text-slate-500 mb-1">挑战</p>
                    <p className="text-slate-600 line-clamp-2">{r.challenges}</p>
                  </div>
                )}

                {r.lessons_learned && (
                  <div>
                    <p className="text-xs font-medium text-slate-500 mb-1">
                      教训提炼
                    </p>
                    <p className="text-slate-600 line-clamp-2">
                      {r.lessons_learned}
                    </p>
                  </div>
                )}

                {r.next_steps.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-slate-500 mb-1">
                      下一步 ({r.next_steps.length})
                    </p>
                    <ul className="space-y-1">
                      {r.next_steps.slice(0, 2).map((s, i) => (
                        <li
                          key={`${s}-${i}`}
                          className="flex items-start gap-1.5 text-slate-600"
                        >
                          <ArrowRight className="h-3.5 w-3.5 text-brand-500 shrink-0 mt-0.5" />
                          <span className="line-clamp-1">{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-2 text-sm text-slate-500">
                <span>满意度</span>
                <span className="text-amber-500 tracking-wide">
                  {levelStars(r.satisfaction)}
                </span>
                <span className="text-xs text-slate-400">{r.satisfaction}/5</span>
              </div>
            </div>
          ))}
        </div>
      )}
      {!loading && (
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          onPageChange={setPage}
        />
      )}

      <Modal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditing(null);
          setAiDraftData(null);
        }}
        title={editing ? "编辑复盘" : "新建复盘"}
        className="max-w-2xl"
      >
        <RetroForm
          initial={editing}
          aiDraft={aiDraftData}
          onSaved={handleSaved}
          onCancel={() => {
            setModalOpen(false);
            setEditing(null);
            setAiDraftData(null);
          }}
        />
      </Modal>
    </div>
  );
}
