"use client";

// frontend/app/(app)/self-discovery/interview/page.tsx
// 人生设计访谈 — 斯坦福人生设计方法论的独立交互页（认识自己 V1）。
// 一问一答聚焦式 UI（非聊天泡泡流）：顶部阶段进度轨 + 大字号当前问题 + 折叠实录。
// 后端复用 chat 会话 + life_design skill（阶段标记协议 ⟨S1⟩~⟨S4⟩/⟨DONE⟩），
// ⟨DONE⟩ 轮产出《个人人生设计蓝图》→ 入库 life_design_blueprints。

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Compass,
  Send,
  ArrowLeft,
  RotateCcw,
  Save,
  MapPin,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { chatApi, lifeDesignApi, pathDecisionApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";
import { Button, Input } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";
import type { DecisionEngineResponse } from "@/types/path-comparison";

// ===== 阶段标记协议（与后端 app/skills/life_design.py 同一协议）=====
const STAGE_RE = /^\s*[⟨<](S[1-4]|DONE)[⟩>]\s*\n?/i;

function parseStage(raw: string): { stage: string | null; content: string } {
  const m = raw.match(STAGE_RE);
  if (!m) return { stage: null, content: raw };
  return { stage: m[1].toUpperCase(), content: raw.slice(m[0].length) };
}

const STAGES = [
  { key: "S1", label: "你在这里", desc: "看清现状" },
  { key: "S2", label: "指南针", desc: "工作观与人生观" },
  { key: "S3", label: "寻路", desc: "心流与能量" },
  { key: "S4", label: "奥德赛计划", desc: "三个五年版本" },
  { key: "DONE", label: "蓝图", desc: "人生设计蓝图" },
] as const;

const CONV_KEY = "gradpath_self_discovery_conv";
const SAVED_KEY = "gradpath_self_discovery_saved";

interface Turn {
  role: "user" | "assistant";
  content: string;
  stage: string | null;
}

export default function InterviewPage() {
  const toast = useToast();
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

  const [booting, setBooting] = useState(true);
  const [phase, setPhase] = useState<"intro" | "interview" | "done">("intro");
  const [convId, setConvId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [starting, setStarting] = useState(false);
  const [blueprint, setBlueprint] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [showTranscript, setShowTranscript] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const currentStage = useMemoStage(turns);
  const stageIdx = STAGES.findIndex((s) => s.key === currentStage);

  // 恢复未完成/已完成的访谈
  useEffect(() => {
    const saved = window.localStorage.getItem(CONV_KEY);
    if (!saved) {
      setBooting(false);
      return;
    }
    chatApi
      .getMessages(saved)
      .then((msgs) => {
        if (!msgs.length) {
          window.localStorage.removeItem(CONV_KEY);
          setBooting(false);
          return;
        }
        const rebuilt: Turn[] = msgs.map((m) => {
          const p = parseStage(m.content);
          return { role: m.role, content: p.content, stage: p.stage };
        });
        setConvId(saved);
        setTurns(rebuilt);
        const lastAssistant = [...rebuilt].reverse().find((t) => t.role === "assistant");
        if (lastAssistant?.stage === "DONE") {
          setBlueprint(lastAssistant.content);
          setPhase("done");
          setSavedId(window.localStorage.getItem(SAVED_KEY) === saved ? saved : null);
        } else {
          setPhase("interview");
        }
      })
      .catch(() => {
        // 会话已被删除等：清掉本地指针，重新开始
        window.localStorage.removeItem(CONV_KEY);
        setBooting(false);
      })
      .finally(() => setBooting(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, phase]);

  const appendTurn = (t: Turn) => setTurns((prev) => [...prev, t]);

  const start = useCallback(async () => {
    setStarting(true);
    try {
      const conv = await chatApi.createConversation("人生设计访谈");
      window.localStorage.setItem(CONV_KEY, conv.id);
      setConvId(conv.id);
      setTurns([]);
      setPhase("interview");
      // 首条消息触发 skill 开场（skill_hint 强制路由到 life_design）
      setSending(true);
      const res = await chatApi.sendMessage(conv.id, {
        content: "我想开始一次人生设计访谈。",
        skill_hint: "life_design",
      });
      if (res.skill_used !== "life_design") {
        toast.push("访谈路由异常，请重试", "error");
        throw new Error("skill mismatch");
      }
      const p = parseStage(res.content);
      appendTurn({ role: "assistant", content: p.content, stage: p.stage });
    } catch {
      toast.push("访谈启动失败，请重试", "error");
      setPhase("intro");
    } finally {
      setStarting(false);
      setSending(false);
    }
  }, [toast]);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || !convId || sending) return;
    setInput("");
    appendTurn({ role: "user", content: text, stage: null });
    setSending(true);
    try {
      const res = await chatApi.sendMessage(convId, {
        content: text,
        skill_hint: "life_design",
      });
      const p = parseStage(res.content);
      appendTurn({ role: "assistant", content: p.content, stage: p.stage });
      if (p.stage === "DONE") {
        setBlueprint(p.content);
        setPhase("done");
      }
    } catch {
      toast.push("发送失败，请重试", "error");
    } finally {
      setSending(false);
    }
  }, [input, convId, sending, toast]);

  const saveBlueprint = useCallback(async () => {
    if (!blueprint || saving) return;
    setSaving(true);
    try {
      const record = await lifeDesignApi.createBlueprint({
        content: blueprint,
        conversation_id: convId,
        transcript: turns.map((t) => ({
          role: t.role,
          content: t.content,
          stage: t.stage,
        })),
      });
      if (convId) window.localStorage.setItem(SAVED_KEY, convId);
      setSavedId(record.id);
      toast.push("蓝图已保存到「我的人生蓝图」", "success");
    } catch {
      toast.push("蓝图保存失败，请重试", "error");
    } finally {
      setSaving(false);
    }
  }, [blueprint, saving, convId, turns, toast]);

  const restart = () => {
    window.localStorage.removeItem(CONV_KEY);
    setConvId(null);
    setTurns([]);
    setBlueprint("");
    setSavedId(null);
    setPhase("intro");
  };

  if (booting) return <LoadingState text="正在恢复你的访谈…" />;

  // ===== 介绍页 =====
  if (phase === "intro") {
    return (
      <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
        <div className="text-center">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
            <Compass className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
          </div>
          <h1 className="page-title">人生设计访谈</h1>
          <p className="text-sm text-ink-400 mt-2 leading-relaxed">
            来自斯坦福最受欢迎的人生设计课
            <br />
            一次一问的深度访谈，终点是一份属于你的《个人人生设计蓝图》
          </p>
        </div>

        <div className="card space-y-4">
          <div className="space-y-3">
            {STAGES.slice(0, 4).map((s, i) => (
              <div key={s.key} className="flex items-center gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-700">
                  {i + 1}
                </span>
                <div>
                  <p className="text-sm font-medium text-ink-800">{s.label}</p>
                  <p className="text-xs text-ink-400">{s.desc}</p>
                </div>
              </div>
            ))}
            <div className="flex items-center gap-3 rounded-lg border border-brand-200 bg-brand-50 p-3">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white">
                ✓
              </span>
              <div>
                <p className="text-sm font-medium text-ink-800">《个人人生设计蓝图》</p>
                <p className="text-xs text-ink-400">
                  8000-12000 字：真问题、指南针、能量地图、三个五年版本、原型行动
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-lg bg-paper-50 p-4 space-y-2">
            <p className="text-xs text-ink-500 leading-relaxed">
              <ShieldCheck className="inline h-3.5 w-3.5 -mt-0.5 mr-1" />
              访谈不替你做决定，也不做心理诊断；你会被一次只问一个问题，
              约需 30-60 分钟，可随时中断、下次继续。你的测评结果和身份档案会自动作为访谈背景。
            </p>
          </div>

          <Button onClick={start} loading={starting} className="w-full" size="md">
            <Compass className="h-4 w-4" />
            开始我的访谈
          </Button>
        </div>
      </div>
    );
  }

  // ===== 蓝图完成页 =====
  if (phase === "done") {
    return (
      <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
        <div className="text-center">
          <h1 className="page-title">你的《个人人生设计蓝图》已生成</h1>
          <p className="text-sm text-ink-400 mt-2">
            这不是终点——三个版本都是可以低成本试错的原型
          </p>
        </div>

        <div className="card">
          <div className="max-h-[55vh] overflow-y-auto whitespace-pre-line text-sm leading-relaxed text-ink-700 p-2">
            {blueprint}
          </div>
        </div>

        <div className="card space-y-3">
          {savedId ? (
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button
                className="flex-1"
                onClick={() => router.push("/self-discovery/blueprint")}
              >
                查看我的人生蓝图
              </Button>
              <Button variant="secondary" className="flex-1" onClick={restart}>
                <RotateCcw className="h-4 w-4" />
                再做一次访谈
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-ink-500">保存后可在「我的人生蓝图」随时回看。</p>
              <Button onClick={saveBlueprint} loading={saving} className="w-full" size="md">
                <Save className="h-4 w-4" />
                保存这份蓝图
              </Button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ===== 访谈进行中 =====
  const lastQuestion = [...turns].reverse().find((t) => t.role === "assistant");
  const answeredCount = turns.filter((t) => t.role === "user").length;

  return (
    <div className="max-w-2xl mx-auto space-y-5 animate-fade-in">
      {/* 阶段进度轨 */}
      <div className="card py-4 px-5">
        <div className="flex items-center justify-between">
          <button
            onClick={() => router.push("/self-discovery")}
            className="inline-flex items-center gap-1 text-sm text-ink-400 hover:text-ink-600 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            认识自己
          </button>
          <span className="text-xs text-ink-400">已回答 {answeredCount} 个问题</span>
        </div>
        <div className="mt-3 flex items-center gap-1">
          {STAGES.map((s, i) => {
            const active = i === stageIdx;
            const passed = stageIdx > i;
            return (
              <div key={s.key} className="flex-1">
                <div
                  className={cn(
                    "h-1.5 rounded-full transition-all",
                    passed ? "bg-brand-400" : active ? "bg-brand-600" : "bg-paper-200",
                  )}
                />
                <p
                  className={cn(
                    "mt-1.5 text-[11px] leading-tight",
                    active ? "font-semibold text-brand-700" : "text-ink-400",
                  )}
                >
                  {s.label}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* 当前问题 */}
      <div key={turns.length} className="card py-8 px-6 space-y-4 animate-fade-in">
        {sending && !lastQuestion ? (
          <p className="text-sm text-ink-400 text-center py-8">访谈准备中…</p>
        ) : (
          <>
            <p className="text-xs font-medium text-brand-600">
              {STAGES[stageIdx]?.label ?? "访谈"}
              {currentStage === "S4" ? " · 讲出你的版本后，下方可用真实数据体检" : ""}
            </p>
            <h2 className="font-display text-lg font-semibold text-ink-800 leading-relaxed whitespace-pre-line">
              {lastQuestion?.content ?? "正在等待第一个问题…"}
            </h2>
          </>
        )}
        {sending && (
          <p className="text-xs text-ink-400 animate-pulse">设计师正在听你说话…</p>
        )}
      </div>

      {/* 数据体检卡（护城河：奥德赛阶段用真实数据检验五年版本） */}
      {currentStage === "S4" && <DataCheckCard prefillMajor={user?.major ?? ""} />}

      {/* 回答输入 */}
      <div className="card space-y-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              send();
            }
          }}
          placeholder="诚实地写下你的回答…（Ctrl/⌘ + Enter 发送）"
          disabled={sending}
          rows={4}
          className="w-full resize-y rounded-lg border border-paper-300 bg-white px-3 py-2.5 text-sm text-ink-800 placeholder:text-ink-300 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100 disabled:bg-paper-50"
        />
        <div className="flex items-center justify-between">
          <button
            onClick={() => setShowTranscript((v) => !v)}
            className="inline-flex items-center gap-1 text-xs text-ink-400 hover:text-ink-600 transition-colors"
          >
            {showTranscript ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            访谈实录（{turns.length} 条）
          </button>
          <Button onClick={send} disabled={!input.trim() || sending} size="sm">
            <Send className="h-3.5 w-3.5" />
            发送回答
          </Button>
        </div>
      </div>

      {/* 折叠实录 */}
      {showTranscript && (
        <div className="card space-y-3 max-h-[40vh] overflow-y-auto">
          {turns.length === 0 && <p className="text-sm text-ink-400">还没有内容</p>}
          {turns.map((t, i) => (
            <div key={i} className={cn("text-sm leading-relaxed", t.role === "user" ? "text-right" : "")}>
              <p className={cn("text-[11px] mb-0.5", t.role === "user" ? "text-ink-400" : "text-brand-500")}>
                {t.role === "user" ? "你" : `人生设计师${t.stage ? ` · ${STAGES.find((s) => s.key === t.stage)?.label ?? ""}` : ""}`}
              </p>
              <p
                className={cn(
                  "inline-block max-w-[92%] whitespace-pre-line rounded-lg px-3 py-2 text-left",
                  t.role === "user" ? "bg-brand-50 text-ink-700" : "bg-paper-50 text-ink-600",
                )}
              >
                {t.content.length > 500 ? t.content.slice(0, 500) + "…" : t.content}
              </p>
            </div>
          ))}
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}

// ===== 数据体检卡（护城河：真实数据检验五年版本）=====
function DataCheckCard({ prefillMajor }: { prefillMajor: string }) {
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const [open, setOpen] = useState(false);
  const [major, setMajor] = useState("");
  const [tier, setTier] = useState("");
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<DecisionEngineResponse | null>(null);

  useEffect(() => {
    setMajor(prefillMajor);
  }, [prefillMajor]);

  const run = async () => {
    if (!major.trim()) {
      toast.push("请先填写专业（如：计算机 / 汉语言文学）", "error");
      return;
    }
    setChecking(true);
    try {
      const res = await pathDecisionApi.analyze({
        major: major.trim(),
        school_tier: tier || undefined,
        fresh_status: user?.fresh_status ?? undefined,
        education: user?.education ?? undefined,
      });
      setResult(res);
    } catch {
      toast.push("数据体检失败，请稍后重试", "error");
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="rounded-xl border border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50 p-4 space-y-3">
      <button onClick={() => setOpen((v) => !v)} className="w-full text-left">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
            <MapPin className="h-4 w-4" />
          </span>
          <div className="flex-1 min-w-0">
            <h3 className="font-display text-sm font-semibold text-ink-800">
              数据体检：你的五年版本，够不够得着？
            </h3>
            <p className="text-xs text-ink-500 leading-relaxed">
              用平台真实数据（可报边界 / 进面线 / 薪资前景）检验你刚讲出的版本——这是任何通用 AI 给不了的检验
            </p>
          </div>
          {open ? <ChevronUp className="h-4 w-4 text-ink-400 mt-1" /> : <ChevronDown className="h-4 w-4 text-ink-400 mt-1" />}
        </div>
      </button>

      {open && (
        <div className="space-y-3 pt-1">
          <div className="grid grid-cols-2 gap-3">
            <Input value={major} onChange={(e) => setMajor(e.target.value)} placeholder="专业，如 计算机" className="text-sm" />
            <select
              value={tier}
              onChange={(e) => setTier(e.target.value)}
              className="w-full rounded-lg border border-paper-300 bg-white px-3 py-2 text-sm text-ink-800 focus:border-brand-400 focus:outline-none"
            >
              <option value="">学校层次（可选）</option>
              <option value="985">985</option>
              <option value="211">211</option>
              <option value="双一流">双一流</option>
              <option value="普通">普通本科</option>
            </select>
          </div>
          <Button size="sm" onClick={run} loading={checking} className="w-full">
            <ShieldCheck className="h-3.5 w-3.5" />
            用真实数据体检
          </Button>

          {result && (
            <div className="space-y-2">
              {result.metrics.map((m) => (
                <div key={m.path_type} className="rounded-lg border border-paper-200 bg-white p-3">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-ink-800">
                      {m.path_type === "kaoyan" ? "考研" : m.path_type === "civil_service" ? "考公" : "就业"}
                      ：{m.target_role}
                    </p>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[11px] font-medium",
                        m.risk_level === "low"
                          ? "bg-emerald-50 text-emerald-600"
                          : m.risk_level === "medium"
                            ? "bg-amber-50 text-amber-600"
                            : "bg-red-50 text-red-500",
                      )}
                    >
                      {m.risk_level === "low" ? "低风险" : m.risk_level === "medium" ? "中风险" : "高风险"} · 匹配 {m.match_score}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-ink-500">
                    首年收入 {m.income_1y} · 准备约 {m.time_cost_months} 个月
                  </p>
                </div>
              ))}
              <p className="text-[11px] text-ink-400 text-center">
                每个数字都有溯源依据。
                <a href="/decision-engine" className="text-brand-600 hover:underline">
                  查看完整决策报告 →
                </a>
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// 最后一个 assistant 阶段标记即当前阶段
function useMemoStage(turns: Turn[]): string | null {
  for (let i = turns.length - 1; i >= 0; i--) {
    if (turns[i].role === "assistant" && turns[i].stage) return turns[i].stage;
  }
  return null;
}
