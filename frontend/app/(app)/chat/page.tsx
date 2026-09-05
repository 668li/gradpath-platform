"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import {
  Plus,
  Send,
  MessageSquare,
  Trash2,
  Bot,
  User as UserIcon,
  Sparkles,
  ChevronDown,
  Pencil,
  Check,
  X,
  Target,
  KeyRound,
} from "lucide-react";
import { chatApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Markdown } from "@/components/ui/markdown";
import { LoadingState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import type { Conversation, Message, ChatSkillInfo } from "@/types";

/** Agent 来源（对应后端 SourceItem：db=数据库检索 / web=联网检索） */
interface AgentSource {
  type: "db" | "web";
  title: string;
  content?: string;
  url?: string;
}

/** 扩展消息类型，支持 Agent 来源和置信度 */
interface MessageWithMeta extends Message {
  agent_sources?: AgentSource[];
  agent_confidence?: number;
}

/**
 * 情景化 quick-start 卡（Phase C3）。
 * 面向"没用过 AI"的新用户，按报考/职业真实场景分组，点击自动填 input 并 preselect 对应 skill。
 * scene: 情景标识（用于分组展示）；skill: 预留 skill code，留空则由后端按情景自动匹配。
 */
const QUICK_START_CARDS = [
  {
    scene: "考研",
    sceneIcon: "🎓",
    title: "考研规划",
    text: "我是二本计算机专业应届生，想考研，帮我看看怎么择校和备考？",
    skill: "grad_school_planning",
  },
  {
    scene: "考公",
    sceneIcon: "🏛️",
    title: "考公方向",
    text: "我想考公务员，专业是汉语言文学，帮我分析能不能报、怎么准备？",
    skill: "career_planning",
  },
  {
    scene: "就业",
    sceneIcon: "💼",
    title: "就业方向",
    text: "我快毕业了，不知道怎么选工作方向，帮我根据我的情况规划一下？",
    skill: "career_planning",
  },
  {
    scene: "选岗",
    sceneIcon: "📍",
    title: "我能报什么岗",
    text: "我本科毕业、专业是计算机，帮我看看国考有哪些岗位我能报、进面线多少？",
    skill: "position_advisor",
  },
  {
    scene: "查线",
    sceneIcon: "📈",
    title: "分数线稳不稳",
    text: "我想考这个学校，进面线大概多少分？我够不够得着？",
    skill: "grad_school_planning",
  },
  {
    scene: "志愿",
    sceneIcon: "🪧",
    title: "冲稳保怎么填",
    text: "我预估能考 380 分，帮我按冲、稳、保三档列一下能报的院校和专业？",
    skill: "grad_school_planning",
  },
];

export default function ChatPage() {
  const toast = useToast();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageWithMeta[]>([]);
  const [skills, setSkills] = useState<ChatSkillInfo[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingConvos, setLoadingConvos] = useState(true);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const [skillHint, setSkillHint] = useState<string>("");
  const [showSkillDropdown, setShowSkillDropdown] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [lastPlanId, setLastPlanId] = useState<string | null>(null);
  const [showByokHint, setShowByokHint] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 加载对话列表
  const loadConversations = useCallback(async () => {
    setLoadingConvos(true);
    try {
      const res = await chatApi.listConversations({ page: 1, page_size: 50 });
      setConversations(res.items);
    } catch {
      toast.push("加载对话列表失败", "error");
    } finally {
      setLoadingConvos(false);
    }
  }, [toast]);

  // 加载 Skills
  useEffect(() => {
    chatApi
      .listSkills()
      .then(setSkills)
      .catch(() => {});
  }, []);

  // 首次加载
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // 选中对话时加载消息
  useEffect(() => {
    if (!currentId) {
      setMessages([]);
      return;
    }
    setLoadingMsgs(true);
    chatApi
      .getMessages(currentId)
      .then((msgs) =>
        // 历史消息：从 context_snapshot 恢复站内数据来源标签
        setMessages(
          msgs.map((m) => ({
            ...m,
            agent_sources:
              (m.context_snapshot?.data_sources as MessageWithMeta["agent_sources"]) ??
              m.agent_sources,
          })),
        ),
      )
      .catch(() => toast.push("加载消息失败", "error"))
      .finally(() => setLoadingMsgs(false));
  }, [currentId, toast]);

  // 新消息时自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 自适应 textarea 高度
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [input]);

  const handleNewConversation = async () => {
    try {
      const conv = await chatApi.createConversation();
      setConversations((prev) => [conv, ...prev]);
      setCurrentId(conv.id);
      setMessages([]);
      setLastPlanId(null);
    } catch {
      toast.push("创建对话失败", "error");
    }
  };

  // Phase C3：情景卡点击 → 填入输入框 + preselect 对应 skill（后端有 skill 则直取，空则自动匹配）
  const applyQuickStart = async (card: (typeof QUICK_START_CARDS)[number], useNewConv: boolean) => {
    if (useNewConv) {
      await handleNewConversation();
    }
    setInput(card.text);
    setSkillHint(card.skill || "");
  };

  const handleSend = async () => {
    const content = input.trim();
    if (!content || sending) return;

    // 没有选中对话时自动创建
    let convId = currentId;
    if (!convId) {
      try {
        const conv = await chatApi.createConversation(content.slice(0, 30));
        setConversations((prev) => [conv, ...prev]);
        convId = conv.id;
        setCurrentId(conv.id);
      } catch {
        toast.push("创建对话失败", "error");
        return;
      }
    }

    // 乐观更新：立即显示用户消息
    const userMsg: MessageWithMeta = {
      id: `temp-${Date.now()}`,
      conversation_id: convId,
      role: "user",
      content,
      skill_used: null,
      context_snapshot: {},
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);
    setLastPlanId(null);

    try {
      // 使用持久化端点：消息保存到会话 + 多轮记忆 + Skill 匹配 + 职业规划生成
      const res = await chatApi.sendMessage(convId, {
        content,
        skill_hint: skillHint || undefined,
      });

      const aiMsg: MessageWithMeta = {
        id: `ai-${Date.now()}`,
        conversation_id: convId,
        role: "assistant",
        content: res.content || "（AI 未返回内容，请重试）",
        skill_used: res.skill_used || null,
        context_snapshot: {},
        agent_sources: res.agent_sources?.length ? res.agent_sources : undefined,
        agent_confidence: res.agent_confidence ?? undefined,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, aiMsg]);

      // 如果 AI 生成了职业规划方案，显示入口
      if (res.career_plan) {
        setLastPlanId(res.career_plan);
      }

      // 如果是首次对话，刷新标题（后端可能已更新）
      if (messages.length === 0) {
        loadConversations();
      }
    } catch (e) {
      // 修复 P2 bug: 失败时回滚乐观更新的用户消息，避免消息悬空
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
      const err = e as { status?: number; message?: string };
      if (err.status === 503) {
        setShowByokHint(true);
        toast.push("AI 服务未配置，添加你自己的 API Key 即可启用对话", "error");
      } else if (err.status === 504) {
        toast.push("AI 回复超时，请重试", "error");
      } else if (err.status === 429) {
        toast.push("请求过于频繁，请稍后再试", "error");
      } else {
        toast.push("发送失败，请重试", "error");
      }
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确认删除此对话？")) return;
    try {
      await chatApi.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (currentId === id) {
        setCurrentId(null);
        setMessages([]);
      }
      toast.push("已删除", "success");
    } catch {
      toast.push("删除失败", "error");
    }
  };

  const handleRename = async (id: string) => {
    if (!editTitle.trim()) return;
    try {
      await chatApi.updateTitle(id, editTitle.trim());
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: editTitle.trim() } : c)),
      );
      setEditingId(null);
      toast.push("已更新标题", "success");
    } catch {
      toast.push("更新失败", "error");
    }
  };

  const startRename = (conv: Conversation) => {
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const currentSkill = skills.find((s) => s.code === skillHint);

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-4">
      {/* 左侧：对话列表 */}
      <div className="hidden md:flex w-64 flex-col rounded-xl border border-ink-200 bg-white">
        <div className="border-b border-ink-100 p-3">
          <button
            onClick={handleNewConversation}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-3 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700"
          >
            <Plus className="h-4 w-4" />
            新建对话
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loadingConvos ? (
            <LoadingState text="加载对话…" />
          ) : conversations.length === 0 ? (
            <p className="px-3 py-4 text-center text-xs text-ink-400">
              暂无对话
            </p>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                className={cn(
                  "group flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors cursor-pointer",
                  currentId === conv.id
                    ? "bg-brand-50 text-brand-700"
                    : "text-ink-600 hover:bg-ink-100",
                )}
                onClick={() => {
                  setCurrentId(conv.id);
                  setLastPlanId(null);
                }}
              >
                <MessageSquare className="h-4 w-4 shrink-0 opacity-60" />
                {editingId === conv.id ? (
                  <input
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleRename(conv.id);
                      if (e.key === "Escape") setEditingId(null);
                    }}
                    className="flex-1 min-w-0 rounded border border-brand-300 px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-brand-200"
                    autoFocus
                  />
                ) : (
                  <span className="flex-1 truncate">{conv.title}</span>
                )}
                {editingId === conv.id ? (
                  <div className="flex items-center gap-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRename(conv.id);
                      }}
                      className="text-green-600 hover:text-green-700"
                    >
                      <Check className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingId(null);
                      }}
                      className="text-ink-400 hover:text-ink-600"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        startRename(conv);
                      }}
                      className="text-ink-400 hover:text-brand-600"
                      aria-label="重命名"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(conv.id);
                      }}
                      className="text-ink-400 hover:text-red-600"
                      aria-label="删除"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* 右侧：聊天区域 */}
      <div className="flex flex-1 flex-col rounded-xl border border-ink-200 bg-white overflow-hidden">
        {currentId ? (
          <>
            {/* 消息列表 */}
            <div className="flex-1 overflow-y-auto px-4 py-4 md:px-6">
              {loadingMsgs ? (
                <LoadingState text="加载消息…" />
              ) : messages.length === 0 ? (
                <div className="flex h-full flex-col items-center justify-center">
                  <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50">
                    <Bot className="h-7 w-7 text-brand-600" />
                  </div>
                  <h3 className="text-base font-semibold text-ink-700">
                    开始与 AI 职业管家对话
                  </h3>
                  <p className="mt-1 text-sm text-ink-400">
                    我可以根据你的职业数据提供个性化建议
                  </p>
                  <div className="mt-6 grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
                    {QUICK_START_CARDS.map((p) => (
                      <button
                        key={p.title}
                        onClick={() => applyQuickStart(p, false)}
                        className="rounded-lg border border-ink-200 bg-ink-50/50 px-3 py-2.5 text-left transition-colors hover:border-brand-300 hover:bg-brand-50/30"
                      >
                        <p className="text-xs font-medium text-brand-600">
                          <span className="mr-1">{p.sceneIcon}</span>
                          {p.scene} · {p.title}
                        </p>
                        <p className="mt-0.5 line-clamp-2 text-xs text-ink-500">
                          {p.text}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((msg) => (
                    <MessageBubble key={msg.id} message={msg} skills={skills} />
                  ))}
                  {sending && (
                    <div className="flex items-start gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-50">
                        <Bot className="h-4 w-4 text-brand-600" />
                      </div>
                      <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm bg-ink-50 px-4 py-3">
                        <span className="h-2 w-2 animate-bounce rounded-full bg-ink-300 [animation-delay:0ms]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-ink-300 [animation-delay:150ms]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-ink-300 [animation-delay:300ms]" />
                      </div>
                    </div>
                  )}
                  {lastPlanId && (
                    <Link
                      href="/plans"
                      className="flex items-center gap-3 rounded-lg border border-brand-200 bg-brand-50/50 px-4 py-3 transition-colors hover:bg-brand-50"
                    >
                      <Target className="h-5 w-5 text-brand-600" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-brand-700">
                          已生成职业规划方案
                        </p>
                        <p className="text-xs text-brand-500">
                          点击查看里程碑与差距分析
                        </p>
                      </div>
                      <ChevronDown className="h-4 w-4 -rotate-90 text-brand-400" />
                    </Link>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* 输入区域 */}
            <div className="border-t border-ink-100 p-3 md:p-4">
              {/* BYOK 引导：AI 服务未配置时提示用户添加自己的 Key */}
              {showByokHint && (
                <div className="mb-2 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                  <KeyRound className="h-4 w-4 shrink-0" />
                  <span className="flex-1">
                    AI 服务未配置。前往
                    <Link
                      href="/settings"
                      className="mx-0.5 font-medium underline hover:text-amber-800"
                      onClick={() => setShowByokHint(false)}
                    >
                      设置 → AI 对话服务
                    </Link>
                    填入你自己的 API Key 即可开始对话。
                  </span>
                  <button
                    onClick={() => setShowByokHint(false)}
                    className="shrink-0 text-amber-500 hover:text-amber-700"
                    aria-label="关闭提示"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}
              {/* Skill 选择器 */}
              <div className="mb-2 flex items-center gap-2">
                <button
                  onClick={() => setShowSkillDropdown(!showSkillDropdown)}
                  className="flex items-center gap-1.5 rounded-full border border-ink-200 bg-ink-50 px-3 py-1 text-xs text-ink-500 transition-colors hover:border-brand-300 hover:text-brand-600"
                >
                  <Sparkles className="h-3 w-3" />
                  {currentSkill ? currentSkill.name : "自动匹配 Skill"}
                  <ChevronDown className="h-3 w-3" />
                </button>
                {skillHint && (
                  <button
                    onClick={() => {
                      setSkillHint("");
                      setShowSkillDropdown(false);
                    }}
                    className="text-xs text-ink-400 hover:text-ink-600"
                  >
                    清除
                  </button>
                )}
                {showSkillDropdown && (
                  <div className="absolute bottom-16 left-4 z-10 w-64 rounded-lg border border-ink-200 bg-white shadow-lg">
                    <button
                      onClick={() => {
                        setSkillHint("");
                        setShowSkillDropdown(false);
                      }}
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-ink-600 hover:bg-ink-50"
                    >
                      <Sparkles className="h-3 w-3 text-ink-400" />
                      自动匹配（推荐）
                    </button>
                    {skills.map((s) => (
                      <button
                        key={s.code}
                        onClick={() => {
                          setSkillHint(s.code);
                          setShowSkillDropdown(false);
                        }}
                        className="flex w-full items-start gap-2 px-3 py-2 text-left hover:bg-ink-50"
                      >
                        <span className="text-sm">{s.icon}</span>
                        <div>
                          <p className="text-xs font-medium text-ink-700">
                            {s.name}
                          </p>
                          <p className="text-[10px] text-ink-400">
                            {s.description}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* 输入框 */}
              <div className="flex items-end gap-2">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="输入你的问题… (Enter 发送，Shift+Enter 换行)"
                  rows={1}
                  className="flex-1 resize-none rounded-xl border border-ink-200 bg-ink-50 px-4 py-2.5 text-sm text-ink-800 placeholder:text-ink-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
                  disabled={sending}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || sending}
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white transition-colors hover:bg-brand-700 disabled:bg-brand-300 disabled:cursor-not-allowed"
                  aria-label="发送"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center p-8">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50">
              <Bot className="h-8 w-8 text-brand-600" />
            </div>
            <h2 className="text-xl font-bold text-ink-800">AI 职业规划管家</h2>
            <p className="mt-2 max-w-md text-center text-sm text-ink-500">
              结合你的职业数据、知识库和智能 Skill 系统，为你提供个性化的职业规划指导。
              支持选岗、查线、考研考公、就业方向等场景。
            </p>
            <div className="mt-6 grid w-full max-w-lg grid-cols-1 gap-3 sm:grid-cols-2">
              {QUICK_START_CARDS.map((p) => (
                <button
                  key={p.title}
                  onClick={() => applyQuickStart(p, true)}
                  className="rounded-xl border border-ink-200 bg-white px-4 py-3 text-left transition-colors hover:border-brand-300 hover:shadow-sm"
                >
                  <p className="text-sm font-medium text-brand-600">
                    <span className="mr-1">{p.sceneIcon}</span>
                    {p.scene} · {p.title}
                  </p>
                  <p className="mt-1 line-clamp-2 text-xs text-ink-500">
                    {p.text}
                  </p>
                </button>
              ))}
            </div>
            <button
              onClick={handleNewConversation}
              className="mt-6 flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700"
            >
              <Plus className="h-4 w-4" />
              开始新对话
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/** 单条消息气泡 */
function MessageBubble({
  message,
  skills,
}: {
  message: MessageWithMeta;
  skills: ChatSkillInfo[];
}) {
  const isUser = message.role === "user";
  const skill = message.skill_used
    ? skills.find((s) => s.code === message.skill_used)
    : null;
  const sources = message.agent_sources;
  const confidence = message.agent_confidence;

  return (
    <div
      className={cn(
        "flex items-start gap-3",
        isUser && "flex-row-reverse",
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-ink-100" : "bg-brand-50",
        )}
      >
        {isUser ? (
          <UserIcon className="h-4 w-4 text-ink-500" />
        ) : (
          <Bot className="h-4 w-4 text-brand-600" />
        )}
      </div>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3",
          isUser
            ? "rounded-tr-sm bg-brand-600 text-white"
            : "rounded-tl-sm bg-ink-50 text-ink-800",
        )}
      >
        {skill && (
          <div className="mb-1.5 flex items-center gap-1 text-[10px] font-medium text-brand-500">
            <span>{skill.icon}</span>
            <span>{skill.name}</span>
          </div>
        )}
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        ) : (
          <Markdown content={message.content} />
        )}
        {/* Agent 来源列表 */}
        {!isUser && sources && sources.length > 0 && (
          <div className="mt-3 border-t border-ink-200 pt-2">
            <p className="mb-1 text-[10px] font-medium text-ink-400">参考来源</p>
            <div className="flex flex-wrap gap-1.5">
              {sources.map((src, i) => (
                <span
                  key={`${src.title}-${i}`}
                  className={cn(
                    "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px]",
                    src.type === "db"
                      ? "bg-brand-50 text-brand-600"
                      : "bg-green-50 text-green-600",
                  )}
                >
                  {src.type === "db" ? "📚" : "🌐"}
                  {src.title.slice(0, 20)}
                  {src.url && (
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-0.5 hover:underline"
                    >
                      ↗
                    </a>
                  )}
                </span>
              ))}
            </div>
          </div>
        )}
        {/* 置信度 */}
        {!isUser && confidence !== undefined && (
          <div className="mt-2 flex items-center gap-1.5 text-[10px] text-ink-400">
            <span>置信度</span>
            <div className="h-1.5 w-16 overflow-hidden rounded-full bg-ink-200">
              <div
                className={cn(
                  "h-full rounded-full",
                  confidence >= 0.7
                    ? "bg-green-500"
                    : confidence >= 0.5
                      ? "bg-yellow-500"
                      : "bg-red-400",
                )}
                style={{ width: `${confidence * 100}%` }}
              />
            </div>
            <span>{Math.round(confidence * 100)}%</span>
          </div>
        )}
      </div>
    </div>
  );
}
