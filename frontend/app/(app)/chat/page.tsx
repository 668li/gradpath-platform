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
} from "lucide-react";
import { chatApi, aiAgentApi } from "@/lib/api";
import type { AgentSource } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Markdown } from "@/components/ui/markdown";
import { LoadingState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import type { Conversation, Message, ChatSkillInfo } from "@/types";

/** 扩展消息类型，支持 Agent 来源和置信度 */
interface MessageWithMeta extends Message {
  agent_sources?: AgentSource[];
  agent_confidence?: number;
}

const SUGGESTED_PROMPTS = [
  {
    title: "职业规划",
    text: "我是计算机专业大三学生，想规划进入大厂做后端开发的路径，应该怎么准备？",
  },
  {
    title: "简历诊断",
    text: "帮我看看我的简历，我有一段实习经历和两个项目，投递后端开发岗位有什么建议？",
  },
  {
    title: "面试模拟",
    text: "我想模拟一下字节跳动后端开发岗的面试，请给我出几道高频面试题。",
  },
  {
    title: "深造 vs 就业",
    text: "我目前在纠结考研还是直接就业，能不能根据我的技能和经历帮我分析一下？",
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
      .then((msgs) => setMessages(msgs))
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
      const res = await aiAgentApi.ask({
        question: content,
        context: skillHint || undefined,
      });

      const aiMsg: MessageWithMeta = {
        id: `ai-${Date.now()}`,
        conversation_id: convId,
        role: "assistant",
        // 修复 P1 bug: res.answer 可能为 undefined，导致 Markdown 渲染异常
        content: res.answer || "（AI 未返回内容，请重试）",
        skill_used: null,
        context_snapshot: {},
        created_at: new Date().toISOString(),
        agent_sources: res.sources || [],
        agent_confidence: res.confidence ?? 0,
      };
      setMessages((prev) => [...prev, aiMsg]);

      // 如果是首次对话，刷新标题（后端可能已更新）
      if (messages.length === 0) {
        loadConversations();
      }
    } catch (e) {
      // 修复 P2 bug: 失败时回滚乐观更新的用户消息，避免消息悬空
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
      const err = e as { status?: number };
      if (err.status === 503) {
        toast.push("AI 服务未配置，请联系管理员", "error");
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
      <div className="hidden md:flex w-64 flex-col rounded-xl border border-slate-200 bg-white">
        <div className="border-b border-slate-100 p-3">
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
            <p className="px-3 py-4 text-center text-xs text-slate-400">
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
                    : "text-slate-600 hover:bg-slate-100",
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
                      className="text-slate-400 hover:text-slate-600"
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
                      className="text-slate-400 hover:text-brand-600"
                      aria-label="重命名"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(conv.id);
                      }}
                      className="text-slate-400 hover:text-red-600"
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
      <div className="flex flex-1 flex-col rounded-xl border border-slate-200 bg-white overflow-hidden">
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
                  <h3 className="text-base font-semibold text-slate-700">
                    开始与 AI 职业管家对话
                  </h3>
                  <p className="mt-1 text-sm text-slate-400">
                    我可以根据你的职业数据提供个性化建议
                  </p>
                  <div className="mt-6 grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
                    {SUGGESTED_PROMPTS.map((p) => (
                      <button
                        key={p.title}
                        onClick={() => setInput(p.text)}
                        className="rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-left transition-colors hover:border-brand-300 hover:bg-brand-50/30"
                      >
                        <p className="text-xs font-medium text-brand-600">
                          {p.title}
                        </p>
                        <p className="mt-0.5 line-clamp-2 text-xs text-slate-500">
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
                      <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm bg-slate-50 px-4 py-3">
                        <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 [animation-delay:0ms]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 [animation-delay:150ms]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 [animation-delay:300ms]" />
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
            <div className="border-t border-slate-100 p-3 md:p-4">
              {/* Skill 选择器 */}
              <div className="mb-2 flex items-center gap-2">
                <button
                  onClick={() => setShowSkillDropdown(!showSkillDropdown)}
                  className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-500 transition-colors hover:border-brand-300 hover:text-brand-600"
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
                    className="text-xs text-slate-400 hover:text-slate-600"
                  >
                    清除
                  </button>
                )}
                {showSkillDropdown && (
                  <div className="absolute bottom-16 left-4 z-10 w-64 rounded-lg border border-slate-200 bg-white shadow-lg">
                    <button
                      onClick={() => {
                        setSkillHint("");
                        setShowSkillDropdown(false);
                      }}
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-slate-600 hover:bg-slate-50"
                    >
                      <Sparkles className="h-3 w-3 text-slate-400" />
                      自动匹配（推荐）
                    </button>
                    {skills.map((s) => (
                      <button
                        key={s.code}
                        onClick={() => {
                          setSkillHint(s.code);
                          setShowSkillDropdown(false);
                        }}
                        className="flex w-full items-start gap-2 px-3 py-2 text-left hover:bg-slate-50"
                      >
                        <span className="text-sm">{s.icon}</span>
                        <div>
                          <p className="text-xs font-medium text-slate-700">
                            {s.name}
                          </p>
                          <p className="text-[10px] text-slate-400">
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
                  className="flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
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
            <h2 className="text-xl font-bold text-slate-800">AI 职业规划管家</h2>
            <p className="mt-2 max-w-md text-center text-sm text-slate-500">
              结合你的职业数据、知识库和智能 Skill 系统，为你提供个性化的职业规划指导。
              支持职业规划、简历诊断、面试模拟等场景。
            </p>
            <div className="mt-6 grid w-full max-w-lg grid-cols-1 gap-3 sm:grid-cols-2">
              {SUGGESTED_PROMPTS.map((p) => (
                <button
                  key={p.title}
                  onClick={async () => {
                    await handleNewConversation();
                    setInput(p.text);
                  }}
                  className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-left transition-colors hover:border-brand-300 hover:shadow-sm"
                >
                  <p className="text-sm font-medium text-brand-600">{p.title}</p>
                  <p className="mt-1 line-clamp-2 text-xs text-slate-500">
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
          isUser ? "bg-slate-100" : "bg-brand-50",
        )}
      >
        {isUser ? (
          <UserIcon className="h-4 w-4 text-slate-500" />
        ) : (
          <Bot className="h-4 w-4 text-brand-600" />
        )}
      </div>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3",
          isUser
            ? "rounded-tr-sm bg-brand-600 text-white"
            : "rounded-tl-sm bg-slate-50 text-slate-800",
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
          <div className="mt-3 border-t border-slate-200 pt-2">
            <p className="mb-1 text-[10px] font-medium text-slate-400">参考来源</p>
            <div className="flex flex-wrap gap-1.5">
              {sources.map((src, i) => (
                <span
                  key={`${src.title}-${i}`}
                  className={cn(
                    "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px]",
                    src.type === "db"
                      ? "bg-blue-50 text-blue-600"
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
          <div className="mt-2 flex items-center gap-1.5 text-[10px] text-slate-400">
            <span>置信度</span>
            <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-200">
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
