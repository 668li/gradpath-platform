"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bell,
  BellOff,
  CalendarClock,
  CheckCircle2,
  ExternalLink,
  FileText,
  HelpCircle,
  Link2,
  MinusCircle,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getToken } from "@/lib/api/client";
import { examTimelineApi } from "@/lib/api/exam-timeline";
import type {
  MyTimelineExam,
  NodeFeedbackStatus,
  TimelineExam,
  TimelineExamDetail,
  TimelineNode,
} from "@/types/exam-timeline";
import { EmptyState, LoadingState } from "@/components/ui/empty";

// ---------------------------------------------------------------- 纯函数（vitest 直测）

export const STATUS_BADGE: Record<
  TimelineNode["date_status"],
  { label: string; cls: string }
> = {
  OFFICIAL: { label: "官方", cls: "bg-green-100 text-green-700" },
  PREDICTED: { label: "预测", cls: "bg-amber-100 text-amber-700" },
  UNKNOWN: { label: "无来源", cls: "bg-ink-100 text-ink-500" },
};

/** 节点日期展示文案——诚实三态各有形态；UNKNOWN 绝不显示任何日期。 */
export function dateLabel(node: TimelineNode): string {
  if (node.date_status === "UNKNOWN" || !node.planned_date) {
    return node.verifiable ? "日期待定" : "暂无可核验来源";
  }
  const range = node.planned_end_date
    ? `${node.planned_date} ~ ${node.planned_end_date}`
    : node.planned_date;
  return node.date_status === "PREDICTED" ? `预计 ${range}` : range;
}

// ---------------------------------------------------------------- 组件

export function ExamTimelineTab() {
  const router = useRouter();
  const [exams, setExams] = useState<TimelineExam[]>([]);
  const [code, setCode] = useState<string | null>(null);
  const [detail, setDetail] = useState<TimelineExamDetail | null>(null);
  const [my, setMy] = useState<MyTimelineExam[]>([]);
  const [loading, setLoading] = useState(true);
  const [authed, setAuthed] = useState(false);
  const [busy, setBusy] = useState(false);
  // 本次会话内的回传选择（服务端为唯一真源；本地只做即时高亮反馈）
  const [fbLocal, setFbLocal] = useState<Record<string, NodeFeedbackStatus>>({});

  const auth = getToken() != null;

  useEffect(() => setAuthed(auth), [auth]);

  const refreshMy = useCallback(() => {
    if (!getToken()) return;
    examTimelineApi
      .mine()
      .then(setMy)
      .catch(() => setMy([]));
  }, []);

  useEffect(() => {
    examTimelineApi
      .listExams()
      .then((list) => {
        setExams(list);
        // 默认选中最近的待考场次（upcoming），否则第一项
        const up = list.find((e) => e.status === "upcoming") ?? list[0];
        if (up) setCode(up.code);
      })
      .catch(() => setExams([]))
      .finally(() => setLoading(false));
    refreshMy();
  }, [refreshMy]);

  useEffect(() => {
    if (!code) return;
    setDetail(null);
    examTimelineApi
      .getExam(code)
      .then(setDetail)
      .catch(() => setDetail(null));
  }, [code]);

  const myItem = my.find((m) => m.exam.code === code) ?? null;
  const subscribed = !!myItem?.subscribed;

  const toggleSubscribe = async () => {
    if (!authed) {
      router.push("/login");
      return;
    }
    if (!code) return;
    setBusy(true);
    try {
      if (subscribed) await examTimelineApi.unsubscribe(code);
      else await examTimelineApi.subscribe(code);
      refreshMy();
    } finally {
      setBusy(false);
    }
  };

  const sendFeedback = async (nodeId: string, status: NodeFeedbackStatus) => {
    if (!authed) {
      router.push("/login");
      return;
    }
    await examTimelineApi
      .feedback(nodeId, status)
      .then((updated) => {
        setFbLocal((m) => ({ ...m, [updated.id]: status }));
      })
      .catch(() => undefined);
    refreshMy();
  };

  if (loading) return <LoadingState text="加载考试流程…" />;
  if (exams.length === 0 || !detail)
    return (
      <EmptyState
        title="时间线尚未就绪"
        description="官方公告数据入库后，这里会亮起一条带来源的考公流程时间线"
      />
    );

  const nextStage = detail.next_node?.stage_key ?? null;

  return (
    <div>
      {/* 头部：场次选择 + 订阅 */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        {exams.map((e) => (
          <button
            key={e.code}
            onClick={() => setCode(e.code)}
            className={cn(
              "rounded-full px-4 py-1.5 text-sm font-medium border transition-colors",
              e.code === code
                ? "bg-purple-600 text-white border-purple-600"
                : "bg-white text-ink-600 border-paper-200 hover:border-purple-300",
            )}
          >
            {e.name}
          </button>
        ))}
        <div className="ml-auto">
          <button
            onClick={toggleSubscribe}
            disabled={busy}
            className={cn(
              "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
              subscribed
                ? "bg-green-50 text-green-700 border border-green-200"
                : "bg-purple-600 text-white hover:bg-purple-700",
            )}
          >
            {subscribed ? <BellOff className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
            {subscribed ? "已订阅，节点到点提醒你" : "订阅提醒"}
          </button>
        </div>
      </div>

      {myItem && myItem.progress.reached > 0 && (
        <div className="mb-6 rounded-lg bg-paper-50 border border-paper-200 px-4 py-3 text-sm text-ink-600">
          进度：已到窗口 {myItem.progress.reached} 个节点，完成 {myItem.progress.done}
          {myItem.completion_rate != null && `（条件完成率 ${(myItem.completion_rate * 100).toFixed(0)}%）`}
        </div>
      )}

      {/* 垂直时间轴 */}
      <ol className="relative ml-3 border-l-2 border-paper-200">
        {detail.nodes.map((n) => {
          const badge = STATUS_BADGE[n.date_status];
          const isNext = nextStage === n.stage_key;
          const fb = fbLocal[n.id];
          return (
            <li key={n.id} className="mb-6 ml-6">
              <span
                className={cn(
                  "absolute -left-[9px] mt-1.5 h-4 w-4 rounded-full border-2 bg-white",
                  isNext
                    ? "border-purple-600 ring-4 ring-purple-100"
                    : n.date_status === "OFFICIAL"
                      ? "border-green-500"
                      : n.date_status === "PREDICTED"
                        ? "border-amber-400"
                        : "border-paper-300",
                )}
              />
              <div
                className={cn(
                  "rounded-lg border bg-white p-4",
                  isNext ? "border-purple-300 shadow-sm" : "border-paper-200",
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-medium text-ink-400">
                    {String(n.seq).padStart(2, "0")}
                  </span>
                  <h3 className="font-semibold text-ink-800">{n.title}</h3>
                  <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", badge.cls)}>
                    {badge.label}
                  </span>
                  {isNext && (
                    <span className="flex items-center gap-1 rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">
                      <CalendarClock className="h-3 w-3" /> 下一节点
                    </span>
                  )}
                  <span className="ml-auto flex items-center gap-1 text-sm text-ink-600">
                    {n.date_status === "PREDICTED" && <span title={n.predict_basis ?? ""}>
                      {dateLabel(n)}
                      <HelpCircle className="ml-1 inline h-3.5 w-3.5 text-amber-500" />
                    </span>}
                    {n.date_status !== "PREDICTED" && dateLabel(n)}
                  </span>
                </div>

                <p className="mt-2 text-sm text-ink-600">{n.action_guide}</p>

                {n.date_status === "OFFICIAL" && n.source_url && (
                  <p className="mt-2 flex items-center gap-1 text-xs text-green-700">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    已核验来源：
                    <a href={n.source_url} target="_blank" rel="noopener noreferrer" className="underline inline-flex items-center gap-0.5">
                      {new URL(n.source_url).hostname} <ExternalLink className="h-3 w-3" />
                    </a>
                  </p>
                )}

                <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
                  {n.official_entry_url && (
                    <a
                      href={n.official_entry_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-purple-600 hover:underline"
                    >
                      <Link2 className="h-4 w-4" /> 官方入口
                    </a>
                  )}
                  {n.materials.length > 0 && (
                    <details className="text-ink-600">
                      <summary className="cursor-pointer inline-flex items-center gap-1">
                        <FileText className="h-4 w-4" /> 材料清单
                      </summary>
                      <ul className="mt-1 list-disc pl-5 text-xs space-y-0.5">
                        {n.materials.map((m, i) => (
                          <li key={i}>{typeof m === "string" ? m : JSON.stringify(m)}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                  {n.dark_knowledge.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {n.dark_knowledge.map((dk) => (
                        <span key={dk.id} className="rounded bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                          暗知识·{dk.title}
                        </span>
                      ))}
                    </div>
                  )}
                  {subscribed && authed && (
                    <div className="ml-auto flex items-center gap-2">
                      <button
                        onClick={() => sendFeedback(n.id, "done")}
                        className={cn(
                          "inline-flex items-center gap-1 text-xs",
                          fb === "done" ? "font-bold text-green-700" : "text-green-600 hover:underline",
                        )}
                      >
                        <CheckCircle2 className="h-4 w-4" /> {fb === "done" ? "已完成 ✓" : "已完成"}
                      </button>
                      <button
                        onClick={() => sendFeedback(n.id, "uncertain")}
                        className={cn(
                          "inline-flex items-center gap-1 text-xs",
                          fb === "uncertain" ? "font-bold text-amber-700" : "text-amber-600 hover:underline",
                        )}
                      >
                        <HelpCircle className="h-4 w-4" /> 不确定
                      </button>
                      <button
                        onClick={() => sendFeedback(n.id, "skipped")}
                        className={cn(
                          "inline-flex items-center gap-1 text-xs",
                          fb === "skipped" ? "font-bold text-ink-700" : "text-ink-400 hover:underline",
                        )}
                      >
                        <MinusCircle className="h-4 w-4" /> 跳过
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ol>

      <p className="text-xs text-ink-400 mb-2">
        时间线只承载“什么时候该做什么＋官方入口”——报名等动作一律在官方网页面完成，本站不代办。
      </p>
    </div>
  );
}
