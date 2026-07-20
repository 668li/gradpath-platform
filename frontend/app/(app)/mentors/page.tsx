"use client";

import { useCallback, useEffect, useState } from "react";
import { Sparkles, Send, Check, Loader2 } from "lucide-react";
import { mentorsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button, Textarea } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type { MentorPersona, MentorPerspectiveResult } from "@/types";

// 导师卡片颜色映射
const PERSONA_COLORS: Record<string, { bg: string; border: string; text: string; accentHex: string }> = {
  strategist: { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700", accentHex: "#3b82f6" },
  accountability: { bg: "bg-orange-50", border: "border-orange-200", text: "text-orange-700", accentHex: "#f97316" },
  devil_advocate: { bg: "bg-red-50", border: "border-red-200", text: "text-red-700", accentHex: "#ef4444" },
  career_strategist: { bg: "bg-brand-50", border: "border-brand-200", text: "text-brand-700", accentHex: "#0d9488" },
};

export default function MentorsPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [personas, setPersonas] = useState<MentorPersona[]>([]);
  const [question, setQuestion] = useState("");
  const [context, setContext] = useState("");
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [perspectives, setPerspectives] = useState<MentorPerspectiveResult[]>([]);
  const [asking, setAsking] = useState(false);

  const loadPersonas = useCallback(async () => {
    setLoading(true);
    try {
      const list = await mentorsApi.listPersonas();
      setPersonas(list);
    } catch {
      toast.push("加载导师列表失败", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadPersonas();
  }, [loadPersonas]);

  const togglePersona = (code: string) => {
    setSelectedCodes(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    );
  };

  const handleAsk = async () => {
    if (!question.trim()) {
      toast.push("请输入你的问题", "error");
      return;
    }
    if (selectedCodes.length === 0) {
      toast.push("请至少选择一位导师", "error");
      return;
    }
    setAsking(true);
    setPerspectives([]);
    try {
      const res = await mentorsApi.getMultiPerspective({
        persona_codes: selectedCodes,
        question,
        user_context: context.trim() || undefined,
      });
      setPerspectives(res.perspectives);
    } catch {
      toast.push("获取导师建议失败，请重试", "error");
    } finally {
      setAsking(false);
    }
  };

  if (loading) return <LoadingState />;

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      {/* 头部 */}
      <div className="text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
          <Sparkles className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
        </div>
        <h1 className="page-title">AI 导师团</h1>
        <p className="text-sm text-ink-400 mt-2 leading-relaxed">
          4 位不同视角的 AI 导师
          <br />
          同一个问题，多维分析，避免单一视角盲区
        </p>
      </div>

      {/* 导师选择 */}
      <div className="card space-y-4">
        <div>
          <p className="text-sm font-medium text-ink-700 mb-3">选择导师（可多选）</p>
          <div className="grid grid-cols-2 gap-3">
            {personas.map(p => {
              const selected = selectedCodes.includes(p.code);
              const colors = PERSONA_COLORS[p.code] || PERSONA_COLORS.career_strategist;
              return (
                <button
                  key={p.code}
                  onClick={() => togglePersona(p.code)}
                  className={cn(
                    "relative rounded-xl border p-4 text-left transition-all",
                    selected
                      ? `${colors.bg} ${colors.border} ring-2 ring-offset-1 ring-brand-200`
                      : "bg-white border-paper-300 hover:border-ink-200",
                  )}
                >
                  {selected && (
                    <span className="absolute top-2 right-2 flex h-5 w-5 items-center justify-center rounded-full bg-brand-600 text-white">
                      <Check className="h-3 w-3" strokeWidth={3} />
                    </span>
                  )}
                  <div className="text-2xl mb-2">{p.icon}</div>
                  <p className={cn("text-sm font-semibold", selected ? colors.text : "text-ink-800")}>
                    {p.name}
                  </p>
                  <p className="text-xs text-ink-400 mt-0.5">{p.tagline}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* 问题描述 */}
        <div className="space-y-3">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-700">
              你的问题 <span className="text-red-500">*</span>
            </label>
            <Textarea
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="例如：我拿到了两个 offer，一个大厂一个创业公司，该怎么选？"
              className="resize-y min-h-[80px]"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-700">
              背景信息 <span className="text-ink-400 font-normal">（可选，帮助导师给出更精准的建议）</span>
            </label>
            <Textarea
              value={context}
              onChange={e => setContext(e.target.value)}
              placeholder="例如：3 年后端经验，当前 28 岁，目标是 35 岁前做到技术管理…"
              className="resize-y min-h-[60px]"
            />
          </div>
        </div>

        <Button
          onClick={handleAsk}
          loading={asking}
          disabled={selectedCodes.length === 0 || !question.trim()}
          className="w-full"
          size="md"
        >
          <Send className="h-4 w-4" />
          向 {selectedCodes.length || 0} 位导师提问
        </Button>
      </div>

      {/* 导师回复 */}
      {asking && (
        <div className="space-y-3">
          {selectedCodes.map(code => {
            const persona = personas.find(p => p.code === code);
            const colors = PERSONA_COLORS[code] || PERSONA_COLORS.career_strategist;
            return (
              <div key={code} className={cn("card border", colors.border, colors.bg)}>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xl">{persona?.icon}</span>
                  <span className={cn("text-sm font-semibold", colors.text)}>{persona?.name}</span>
                  <Loader2 className="h-4 w-4 animate-spin text-ink-300 ml-auto" />
                </div>
                <div className="space-y-1.5">
                  <div className="h-3 w-full rounded-full bg-white/60 animate-pulse" />
                  <div className="h-3 w-11/12 rounded-full bg-white/60 animate-pulse" />
                  <div className="h-3 w-4/5 rounded-full bg-white/60 animate-pulse" />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {!asking && perspectives.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-ink-500">
            <Sparkles className="h-4 w-4 text-brand-500" />
            <span>{perspectives.length} 位导师的视角</span>
          </div>
          {perspectives.map((p, i) => {
            const colors = PERSONA_COLORS[p.persona_code] || PERSONA_COLORS.career_strategist;
            return (
              <div key={p.persona_code} className={cn("card border-l-4", colors.border)} style={{ borderLeftColor: colors.accentHex }}>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xl">{p.persona_icon}</span>
                  <div>
                    <p className={cn("text-sm font-semibold", colors.text)}>{p.persona_name}</p>
                    <p className="text-[11px] text-ink-400">
                      {personas.find(per => per.code === p.persona_code)?.tagline}
                    </p>
                  </div>
                </div>
                <p className="text-sm text-ink-700 leading-relaxed whitespace-pre-line">
                  {p.advice}
                </p>
              </div>
            );
          })}

          {/* 综合提示 */}
          <div className="card bg-brand-50 border-brand-200">
            <div className="flex items-start gap-2">
              <Sparkles className="h-4 w-4 text-brand-600 mt-0.5 shrink-0" />
              <p className="text-xs text-ink-600 leading-relaxed">
                每位导师从不同角度分析了你的问题。注意他们观点的<strong>分歧点</strong>——
                那通常是你需要最认真思考的地方。不要只听你认同的那个，重点看挑战你假设的那个。
              </p>
            </div>
          </div>
        </div>
      )}

      {!asking && perspectives.length === 0 && (
        <EmptyState
          title="等待你的提问"
          description="选择上方的导师，输入你的问题，获取多维度的分析建议。"
        />
      )}
    </div>
  );
}
