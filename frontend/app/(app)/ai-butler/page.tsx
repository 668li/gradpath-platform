"use client";

import { useCallback, useEffect, useState } from "react";
import { Bot, Sparkles, MessageSquare, RefreshCw, Send } from "lucide-react";
import { aiButlerApi } from "@/lib/api/ai";
import { Button, Textarea } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { ListSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty";
import { cn } from "@/lib/utils";

type Tab = "scan" | "chat";

const PRIORITY_LABEL: Record<string, { label: string; cls: string }> = {
  high: { label: "高优先级", cls: "bg-red-500/15 text-red-700" },
  medium: { label: "中优先级", cls: "bg-amber-500/15 text-amber-700" },
  low: { label: "低优先级", cls: "bg-emerald-500/15 text-emerald-700" },
};

export default function AIButlerPage() {
  const [tab, setTab] = useState<Tab>("scan");

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-500/15 text-brand-500">
          <Bot className="h-6 w-6" strokeWidth={2} />
        </div>
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-800">
            AI 管家
          </h1>
          <p className="text-sm text-ink-500">
            扫描你的全部数据，生成专属职业方案；也能基于你的背景个性化答疑。
          </p>
        </div>
      </header>

      <div className="flex gap-1 rounded-lg bg-paper-200 p-1 w-fit">
        {([
          { id: "scan", label: "我的方案", icon: Sparkles },
          { id: "chat", label: "对话答疑", icon: MessageSquare },
        ] as const).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all",
              tab === t.id
                ? "bg-white text-brand-600 shadow-sm"
                : "text-ink-500 hover:text-ink-700",
            )}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === "scan" ? <ScanPanel /> : <ChatPanel />}
    </div>
  );
}

function ScanPanel() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);

  const run = useCallback(() => {
    setLoading(true);
    aiButlerApi
      .scan()
      .then(setData)
      .catch(() => toast.push("扫描失败，请稍后再试", "error"))
      .finally(() => setLoading(false));
  }, [toast]);

  useEffect(() => {
    run();
  }, [run]);

  if (loading) return <ListSkeleton count={6} />;
  if (!data) return <EmptyState title="暂无数据" description="完成更多职业动作后，管家会给出更精准的方案。" />;

  const profile = data.profile || {};
  const inv = profile.inventory || {};
  const plan = data.plan || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-ink-500">
          {data.llm_enriched ? "已结合 AI 润色" : "基于你的数据智能生成"} ·{" "}
          {new Date(data.generated_at).toLocaleString("zh-CN")}
        </p>
        <Button variant="ghost" size="sm" onClick={run}>
          <RefreshCw className="h-4 w-4" /> 重新扫描
        </Button>
      </div>

      {profile.summary && (
        <div className="rounded-xl border border-brand-200 bg-brand-50/40 p-4 text-sm text-ink-700">
          {profile.summary}
        </div>
      )}

      {/* 数据资产概览 */}
      <section className="rounded-xl border border-paper-300 bg-white p-5">
        <h2 className="mb-3 font-semibold text-ink-800">你的数据资产</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {[
            ["去向决策", inv.decisions],
            ["职业事件", inv.events],
            ["技能", inv.skills],
            ["规划", inv.career_plans],
            ["复盘", inv.retrospectives],
            ["测评", inv.assessments],
            ["收藏", inv.bookmarks],
            ["洞察", inv.insights],
            ["经验帖", inv.experience_posts],
            ["问答", inv.qa_asked],
          ].map(([label, val]) => (
            <div key={label} className="rounded-lg bg-paper-100 px-3 py-2 text-center">
              <p className="text-xl font-semibold text-brand-600">{val ?? 0}</p>
              <p className="text-xs text-ink-500">{label}</p>
            </div>
          ))}
        </div>
        {profile.active_plans?.length > 0 && (
          <div className="mt-4 space-y-1 text-sm text-ink-600">
            <p className="font-medium text-ink-700">进行中的规划：</p>
            {profile.active_plans.map((p: any, i: number) => (
              <p key={`${p.goal}-${i}`}>· {p.goal}（进度 {p.progress} · {p.timeline_months} 个月）</p>
            ))}
          </div>
        )}
      </section>

      {/* 行动清单 */}
      <section className="rounded-xl border border-paper-300 bg-white p-5">
        <h2 className="mb-3 font-semibold text-ink-800">专属行动清单</h2>
        <div className="space-y-3">
          {plan.map((item: any, i: number) => {
            const pr = PRIORITY_LABEL[item.priority] || PRIORITY_LABEL.low;
            return (
              <div key={`${item.title}-${i}`} className="flex gap-3 rounded-lg border border-paper-200 p-3">
                <span className={cn("mt-0.5 rounded px-2 py-0.5 text-xs font-medium", pr.cls)}>
                  {pr.label}
                </span>
                <div className="flex-1">
                  <p className="font-medium text-ink-800">{item.title}</p>
                  <p className="text-sm text-ink-500">{item.why}</p>
                  <p className="mt-1 text-sm text-brand-700">→ {item.action}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function ChatPanel() {
  const toast = useToast();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);

  const send = useCallback(() => {
    const text = input.trim();
    if (!text || busy) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setBusy(true);
    aiButlerApi
      .chat(text)
      .then((r) => {
        setMessages((m) => [...m, { role: "assistant", content: r.answer }]);
      })
      .catch(() => toast.push("管家暂时无法回答", "error"))
      .finally(() => setBusy(false));
  }, [input, busy, toast]);

  return (
    <div className="space-y-4">
      <div className="min-h-[300px] space-y-3 rounded-xl border border-paper-300 bg-white p-4">
        {messages.length === 0 && (
          <EmptyState title="问问你的管家" description="例如：我该考研还是就业？结合我的背景给建议" />
        )}
        {messages.map((m, i) => (
          <div
            key={`${m.role}-${i}`}
            className={cn(
              "max-w-[85%] rounded-lg px-3 py-2 text-sm",
              m.role === "user"
                ? "ml-auto bg-brand-500 text-white"
                : "bg-paper-100 text-ink-700 whitespace-pre-wrap",
            )}
          >
            {m.content}
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder="输入你的问题..."
          className="min-h-[44px]"
        />
        <Button onClick={send} loading={busy}>
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
