"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  MessageCircle,
  Heart,
  Shield,
  Swords,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Lightbulb,
  Quote,
  BarChart3,
  Send,
  RotateCcw,
  ChevronRight,
} from "lucide-react";
import { familyDialogueApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button, Input, Textarea, Field } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type {
  ParentArchetype,
  FamilyDialogueResponse,
  Argument,
  PracticeMessage,
} from "@/types/family-dialogue";

// 父母类型映射
const ARCHETYPES: { value: ParentArchetype; label: string; desc: string; icon: string }[] = [
  { value: "stability_first", label: "稳定优先型", desc: "考公稳定，不用担心失业", icon: "🛡️" },
  { value: "prestige_first", label: "面子优先型", desc: "公务员有面子，说出去好听", icon: "✨" },
  { value: "practical_worry", label: "现实焦虑型", desc: "现在经济不好，先求稳", icon: "😰" },
  { value: "supportive", label: "开明支持型", desc: "你自己决定，但要考虑清楚", icon: "🤝" },
];

const ARCHETYPE_LABELS: Record<string, string> = {
  stability_first: "稳定优先型",
  prestige_first: "面子优先型",
  practical_worry: "现实焦虑型",
  supportive: "开明支持型",
};

type Step = "intro" | "understanding" | "arguments" | "practice";

export default function FamilyDialoguePage() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState<Step>("intro");

  // 表单
  const [parentConcern, setParentConcern] = useState("");
  const [userChoice, setUserChoice] = useState("");
  const [archetype, setArchetype] = useState<ParentArchetype>("stability_first");
  const [starting, setStarting] = useState(false);

  // 会话
  const [session, setSession] = useState<FamilyDialogueResponse | null>(null);
  const [history, setHistory] = useState<FamilyDialogueResponse[]>([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const h = await familyDialogueApi.getHistory().catch(() => []);
      setHistory(h);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 启动会话
  const handleStart = useCallback(async () => {
    if (!parentConcern.trim() || !userChoice.trim()) {
      toast.push("请填写父母担忧和你的选择", "error");
      return;
    }
    setStarting(true);
    try {
      const res = await familyDialogueApi.start({
        parent_concern: parentConcern.trim(),
        user_choice: userChoice.trim(),
        parent_archetype: archetype,
      });
      setSession(res);
      setStep("understanding");
      toast.push("分析已生成", "success");
      loadData();
    } catch {
      toast.push("启动失败，请重试", "error");
    } finally {
      setStarting(false);
    }
  }, [parentConcern, userChoice, archetype, toast, loadData]);

  const handleReset = useCallback(() => {
    setSession(null);
    setParentConcern("");
    setUserChoice("");
    setArchetype("stability_first");
    setStep("intro");
  }, []);

  if (loading) return <LoadingState />;

  // ====== Step 0: 介绍 + 表单 ======
  if (step === "intro") {
    return (
      <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
        <div className="text-center">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
            <MessageCircle className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
          </div>
          <h1 className="page-title">家庭对话脚手架</h1>
          <p className="text-sm text-ink-400 mt-2 leading-relaxed">
            把父母的旧经验，翻译成新时代语境
            <br />
            理解父母 → 准备弹药 → 实战演练
          </p>
        </div>

        <div className="card space-y-5">
          <div className="grid grid-cols-3 gap-3">
            <StepCard num="1" title="理解父母" desc="父母为什么这么想？" icon={<Heart className="h-4 w-4" />} />
            <StepCard num="2" title="准备弹药" desc="话术模板 + 数据支撑" icon={<Shield className="h-4 w-4" />} />
            <StepCard num="3" title="实战演练" desc="模拟对话练习" icon={<Swords className="h-4 w-4" />} />
          </div>

          <Field label="父母主要担心什么" required hint="如「爸妈想让我考公务员」">
            <Input
              value={parentConcern}
              onChange={(e) => setParentConcern(e.target.value)}
              placeholder="用一句话描述父母的担忧"
              maxLength={200}
            />
          </Field>

          <Field label="你想选什么" required hint="如「我想去互联网大厂做开发」">
            <Input
              value={userChoice}
              onChange={(e) => setUserChoice(e.target.value)}
              placeholder="用一句话描述你的选择"
              maxLength={200}
            />
          </Field>

          <Field label="父母类型" required hint="选择最贴近你父母的类型">
            <div className="grid grid-cols-2 gap-2">
              {ARCHETYPES.map((a) => (
                <button
                  key={a.value}
                  type="button"
                  onClick={() => setArchetype(a.value)}
                  className={cn(
                    "flex items-start gap-2.5 rounded-lg border p-3 text-left transition-all",
                    archetype === a.value
                      ? "border-brand-500 bg-brand-50 ring-1 ring-brand-200"
                      : "border-paper-300 bg-white hover:border-brand-300",
                  )}
                >
                  <span className="text-xl leading-none">{a.icon}</span>
                  <div className="min-w-0">
                    <p className={cn("text-sm font-medium", archetype === a.value ? "text-brand-700" : "text-ink-800")}>
                      {a.label}
                    </p>
                    <p className="text-[11px] text-ink-400 mt-0.5 leading-snug">{a.desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </Field>

          <Button onClick={handleStart} loading={starting} className="w-full" size="md">
            <Heart className="h-4 w-4" />
            开始分析
          </Button>
        </div>

        {history.length > 0 && (
          <div className="card space-y-3">
            <h2 className="font-display font-semibold text-ink-800">历史会话</h2>
            {history.slice(0, 5).map((h) => (
              <button
                key={h.id}
                onClick={() => {
                  setSession(h);
                  setParentConcern(h.parent_concern);
                  setUserChoice(h.user_choice);
                  setArchetype((h.parent_archetype as ParentArchetype) || "stability_first");
                  setStep(h.practice_messages.length > 0 ? "practice" : "understanding");
                }}
                className="flex w-full items-center justify-between border-b border-paper-200 pb-2 text-left last:border-0 last:pb-0 hover:bg-paper-50 -mx-2 px-2 py-1 rounded transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink-700">{h.parent_concern}</p>
                  <p className="truncate text-xs text-ink-400">
                    {ARCHETYPE_LABELS[h.parent_archetype || ""] || h.parent_archetype} · {h.user_choice}
                  </p>
                </div>
                <span
                  className={cn(
                    "ml-2 inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium",
                    h.status === "completed"
                      ? "bg-green-50 text-green-600"
                      : h.status === "practiced"
                        ? "bg-brand-100 text-brand-700"
                        : "bg-paper-200 text-ink-500",
                  )}
                >
                  {h.status === "completed" ? "已完成" : h.status === "practiced" ? "已演练" : "准备中"}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  // 后续步骤需要 session
  if (!session) {
    return <LoadingState />;
  }

  // ====== Step 1: 理解父母 ======
  if (step === "understanding") {
    return (
      <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
        <StepHeader current={1} />

        <div className="text-center">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-50 mb-3">
            <Heart className="h-7 w-7 text-rose-500" strokeWidth={1.8} />
          </div>
          <h1 className="page-title">理解父母</h1>
          <p className="text-sm text-ink-400 mt-2">先理解他们的出发点，沟通才有效</p>
        </div>

        <div className="card space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-paper-50 p-3">
              <p className="text-[11px] font-medium text-ink-400">父母担心</p>
              <p className="text-sm text-ink-800 mt-1">{session.parent_concern}</p>
            </div>
            <div className="rounded-lg bg-paper-50 p-3">
              <p className="text-[11px] font-medium text-ink-400">你的选择</p>
              <p className="text-sm text-ink-800 mt-1">{session.user_choice}</p>
            </div>
          </div>

          <div className="rounded-lg border border-rose-100 bg-rose-50/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="h-4 w-4 text-rose-500" />
              <p className="text-sm font-medium text-ink-800">为什么父母会这么想</p>
            </div>
            <p className="text-sm text-ink-700 leading-relaxed whitespace-pre-line">
              {session.understanding}
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <button
            onClick={() => setStep("intro")}
            className="text-sm text-ink-400 hover:text-ink-600 transition-colors"
          >
            <ArrowLeft className="inline h-4 w-4" /> 返回修改
          </button>
          <Button onClick={() => setStep("arguments")}>
            准备弹药 <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  // ====== Step 2: 准备弹药 ======
  if (step === "arguments") {
    return (
      <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
        <StepHeader current={2} />

        <div className="text-center">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 mb-3">
            <Shield className="h-7 w-7 text-brand-600" strokeWidth={1.8} />
          </div>
          <h1 className="page-title">准备弹药</h1>
          <p className="text-sm text-ink-400 mt-2">数据化回应 + 共情提示，把冲突翻译成对话</p>
        </div>

        {/* 论据卡片 */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Swords className="h-4 w-4 text-brand-600" />
            <h2 className="font-display font-semibold text-ink-800">话术模板（{session.arguments.length} 条）</h2>
          </div>
          {session.arguments.map((arg, i) => (
            <ArgumentCard key={i} index={i} argument={arg} />
          ))}
        </div>

        {/* 沟通技巧 */}
        <div className="card space-y-3">
          <div className="flex items-center gap-2">
            <Lightbulb className="h-4 w-4 text-amber-500" />
            <h2 className="font-display font-semibold text-ink-800">沟通技巧</h2>
          </div>
          <ul className="space-y-2">
            {session.talking_tips.map((tip, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-ink-600">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-100 text-[10px] font-bold text-amber-600">
                  {i + 1}
                </span>
                <span className="leading-relaxed">{tip}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex items-center justify-between">
          <button
            onClick={() => setStep("understanding")}
            className="text-sm text-ink-400 hover:text-ink-600 transition-colors"
          >
            <ArrowLeft className="inline h-4 w-4" /> 上一步
          </button>
          <Button onClick={() => setStep("practice")}>
            开始演练 <Swords className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  // ====== Step 3: 实战演练 ======
  return (
    <PracticeView
      session={session}
      onUpdate={(s) => setSession(s)}
      onBack={() => setStep("arguments")}
      onReset={handleReset}
    />
  );
}

// ----------------------------------------------------------------------
// 步骤进度头
// ----------------------------------------------------------------------
function StepHeader({ current }: { current: 1 | 2 | 3 }) {
  const steps = [
    { n: 1, label: "理解父母" },
    { n: 2, label: "准备弹药" },
    { n: 3, label: "实战演练" },
  ];
  return (
    <div className="flex items-center justify-center gap-2">
      {steps.map((s, i) => (
        <div key={s.n} className="flex items-center gap-2">
          <div
            className={cn(
              "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
              current >= s.n ? "bg-brand-100 text-brand-700" : "bg-paper-200 text-ink-400",
            )}
          >
            <span
              className={cn(
                "flex h-4 w-4 items-center justify-center rounded-full text-[10px]",
                current >= s.n ? "bg-brand-600 text-white" : "bg-paper-400 text-white",
              )}
            >
              {current > s.n ? "✓" : s.n}
            </span>
            {s.label}
          </div>
          {i < steps.length - 1 && <ChevronRight className="h-3 w-3 text-ink-300" />}
        </div>
      ))}
    </div>
  );
}

function StepCard({ num, title, desc, icon }: { num: string; title: string; desc: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-paper-200 bg-white p-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-brand-600">{icon}</span>
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-brand-100 text-[10px] font-bold text-brand-700">
          {num}
        </span>
      </div>
      <p className="text-sm font-medium text-ink-800">{title}</p>
      <p className="text-[11px] text-ink-400 mt-0.5 leading-snug">{desc}</p>
    </div>
  );
}

// ----------------------------------------------------------------------
// 论据卡片
// ----------------------------------------------------------------------
function ArgumentCard({ index, argument }: { index: number; argument: Argument }) {
  return (
    <div className="card space-y-3">
      <div className="flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
          {index + 1}
        </span>
        <Quote className="h-4 w-4 text-ink-400" />
        <p className="text-sm font-medium text-ink-800">{argument.parent_saying}</p>
      </div>

      <div className="rounded-lg bg-brand-50/60 p-3">
        <p className="text-[11px] font-medium text-brand-600 mb-1">建议回应</p>
        <p className="text-sm text-ink-700 leading-relaxed">{argument.user_response}</p>
      </div>

      <div className="rounded-lg bg-paper-50 p-3">
        <div className="flex items-center gap-1.5 mb-1">
          <BarChart3 className="h-3.5 w-3.5 text-ink-500" />
          <p className="text-[11px] font-medium text-ink-500">数据支撑</p>
        </div>
        <p className="text-xs text-ink-600 leading-relaxed">{argument.data_backing}</p>
      </div>

      <div className="flex items-start gap-1.5 rounded-lg border border-rose-100 bg-rose-50/40 p-3">
        <Heart className="h-3.5 w-3.5 text-rose-400 shrink-0 mt-0.5" />
        <div>
          <p className="text-[11px] font-medium text-rose-500 mb-0.5">共情提示</p>
          <p className="text-xs text-ink-600 leading-relaxed">{argument.empathy_note}</p>
        </div>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// 实战演练视图
// ----------------------------------------------------------------------
function PracticeView({
  session,
  onUpdate,
  onBack,
  onReset,
}: {
  session: FamilyDialogueResponse;
  onUpdate: (s: FamilyDialogueResponse) => void;
  onBack: () => void;
  onReset: () => void;
}) {
  const toast = useToast();
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const messagesRef = useRef<HTMLDivElement>(null);

  const messages: PracticeMessage[] = session.practice_messages || [];

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages.length]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    setSending(true);
    try {
      const reply = await familyDialogueApi.practice(session.id, text);
      // 乐观更新：把用户消息 + 父母回复都加上
      onUpdate({
        ...session,
        practice_messages: [
          ...messages,
          { role: "user", content: text },
          { role: "parent", content: reply.content },
        ],
        status: "practiced",
      });
    } catch {
      toast.push("回复失败，请重试", "error");
      setInput(text);
    } finally {
      setSending(false);
    }
  }, [input, session, messages, onUpdate, toast]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-4 animate-fade-in">
      <StepHeader current={3} />

      <div className="text-center">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 mb-3">
          <Swords className="h-7 w-7 text-brand-600" strokeWidth={1.8} />
        </div>
        <h1 className="page-title">实战演练</h1>
        <p className="text-sm text-ink-400 mt-2">输入你要说的话，AI 扮演父母回复</p>
      </div>

      {/* 论据速查 */}
      <details className="card">
        <summary className="cursor-pointer text-sm font-medium text-ink-700 list-none flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-amber-500" />
          论据速查（点击展开）
        </summary>
        <div className="mt-3 space-y-2">
          {session.arguments.map((arg, i) => (
            <div key={i} className="rounded-md bg-paper-50 p-2.5 text-xs">
              <p className="font-medium text-ink-700">{arg.parent_saying}</p>
              <p className="text-ink-500 mt-1">{arg.user_response}</p>
            </div>
          ))}
        </div>
      </details>

      {/* 对话区 */}
      <div className="card flex flex-col" style={{ minHeight: 360 }}>
        <div
          ref={messagesRef}
          className="flex-1 space-y-3 overflow-y-auto pr-1"
          style={{ maxHeight: 420 }}
        >
          {messages.length === 0 ? (
            <div className="flex h-full min-h-[200px] items-center justify-center">
              <EmptyState
                title="开始你的第一句话"
                description="试试「爸妈，我想跟你们聊聊我的打算……」"
              />
            </div>
          ) : (
            messages.map((m, i) => <ChatBubble key={i} message={m} />)
          )}
          {sending && (
            <ChatBubble message={{ role: "parent", content: "……（父母正在思考）" }} pending />
          )}
        </div>

        {/* 输入区 */}
        <div className="mt-3 flex items-end gap-2 border-t border-paper-200 pt-3">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你要对父母说的话…（Enter 发送，Shift+Enter 换行）"
            className="resize-none min-h-[44px] max-h-32 text-sm"
            disabled={sending}
          />
          <Button onClick={handleSend} loading={sending} disabled={!input.trim()} size="md" className="shrink-0">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* 底部引导 */}
      {messages.length >= 4 && (
        <div className="card space-y-3 animate-fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <h2 className="font-display font-semibold text-ink-800">演练小结</h2>
          </div>
          <p className="text-sm text-ink-600 leading-relaxed">
            你已完成 {messages.length} 轮对话。真实沟通不是一次性的，可以把这里的论据和话术带到下次和父母的对话中。
            记住核心原则：先共情再表态、用数据落地、给折中方案。
          </p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button variant="secondary" onClick={onReset} className="flex-1">
              <RotateCcw className="h-4 w-4" /> 再练一次
            </Button>
            <Link
              href="/career-simulator"
              className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-brand-sm transition-all hover:bg-brand-700"
            >
              沟通成功后，来规划你的路径 <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="text-sm text-ink-400 hover:text-ink-600 transition-colors"
        >
          <ArrowLeft className="inline h-4 w-4" /> 返回弹药
        </button>
        <button
          onClick={onReset}
          className="text-sm text-ink-400 hover:text-ink-600 transition-colors"
        >
          <RotateCcw className="inline h-4 w-4" /> 重新开始
        </button>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// 对话气泡
// ----------------------------------------------------------------------
function ChatBubble({ message, pending }: { message: PracticeMessage; pending?: boolean }) {
  const isParent = message.role === "parent";
  return (
    <div className={cn("flex", isParent ? "justify-start" : "justify-end")}>
      <div
        className={cn(
          "flex max-w-[80%] items-start gap-2",
          isParent ? "flex-row" : "flex-row-reverse",
        )}
      >
        <div
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs",
            isParent ? "bg-rose-100 text-rose-500" : "bg-brand-100 text-brand-600",
          )}
        >
          {isParent ? "父" : "我"}
        </div>
        <div
          className={cn(
            "rounded-2xl px-3.5 py-2 text-sm leading-relaxed",
            isParent
              ? "rounded-tl-sm bg-white border border-paper-200 text-ink-700"
              : "rounded-tr-sm bg-brand-600 text-white",
            pending && "opacity-60",
          )}
        >
          {message.content}
        </div>
      </div>
    </div>
  );
}
