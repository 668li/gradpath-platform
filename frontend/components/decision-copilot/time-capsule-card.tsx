"use client";

import { useState, useCallback, useEffect } from "react";
import { Mail, Lock, Unlock, Send, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { decisionJournalApi } from "@/lib/api";
import type { TimeCapsuleResponse } from "@/lib/api/decisions";

/**
 * 决策时间胶囊 — 创意功能。
 * 决策时写一封信给未来的自己，封存后只有到回溯日期才能拆开。
 * 让决策复盘从冷冰冰的打分，变成一场与过去自己的对话。
 *
 * 三种状态：
 * 1. 未封存 → 显示写信表单
 * 2. 已封存未到日期 → 显示"封存中，X 日后可拆"
 * 3. 可拆封 → 显示信件内容
 */
export function TimeCapsuleCard({ decisionId }: { decisionId: string }) {
  const toast = useToast();
  const [capsule, setCapsule] = useState<TimeCapsuleResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [letterDraft, setLetterDraft] = useState("");
  const [sealing, setSealing] = useState(false);
  const [revealed, setRevealed] = useState(false);

  const loadCapsule = useCallback(async () => {
    setLoading(true);
    try {
      const res = await decisionJournalApi.openTimeCapsule(decisionId);
      setCapsule(res);
      if (res.can_open && res.letter) setRevealed(true);
    } catch {
      // 静默失败
    } finally {
      setLoading(false);
    }
  }, [decisionId]);

  useEffect(() => {
    loadCapsule();
  }, [loadCapsule]);

  const handleSeal = async () => {
    if (!letterDraft.trim()) {
      toast.push("写点什么给未来的自己吧", "error");
      return;
    }
    setSealing(true);
    try {
      await decisionJournalApi.sealTimeCapsule(decisionId, letterDraft);
      toast.push("时间胶囊已封存", "success");
      setLetterDraft("");
      await loadCapsule();
    } catch {
      toast.push("封存失败，请重试", "error");
    } finally {
      setSealing(false);
    }
  };

  const handleReveal = async () => {
    setRevealed(true);
  };

  if (loading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-36 rounded bg-paper-200 mb-3" />
        <div className="h-3 w-full rounded bg-paper-200" />
      </div>
    );
  }

  // 状态 1：未封存 — 写信表单
  if (!capsule || !capsule.has_capsule) {
    return (
      <div className="card border border-dashed border-brand-200 bg-brand-50/30 p-5 animate-fade-in">
        <div className="mb-2 flex items-center gap-2">
          <Mail className="h-4 w-4 text-brand-600" />
          <h3 className="font-display font-semibold text-ink-800">写给未来自己的信</h3>
        </div>
        <p className="mb-3 text-xs text-ink-500">
          此刻你为什么做这个决定？你期待什么、害怕什么？封存后，回溯那天才能拆开。
        </p>
        <textarea
          value={letterDraft}
          onChange={(e) => setLetterDraft(e.target.value)}
          placeholder="亲爱的未来的我：今天我决定了……"
          rows={4}
          maxLength={2000}
          className="w-full rounded-lg border border-paper-300 bg-white p-3 text-sm text-ink-700 placeholder:text-ink-300 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
        />
        <div className="mt-3 flex items-center justify-between">
          <span className="text-[11px] text-ink-400">{letterDraft.length}/2000</span>
          <Button onClick={handleSeal} loading={sealing} disabled={sealing} size="sm">
            <Lock className="h-3.5 w-3.5" />
            封存这封信
          </Button>
        </div>
      </div>
    );
  }

  // 状态 2：已封存但不可拆 — 等待中
  if (!capsule.can_open && !revealed) {
    return (
      <div className="card bg-gradient-to-br from-brand-50 to-paper-50 p-5 animate-fade-in">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
            <Lock className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="font-display font-semibold text-ink-800">时间胶囊封存中</h3>
            <p className="mt-1 text-sm text-ink-500">{capsule.message}</p>
            <div className="mt-2 flex items-center gap-2 text-xs text-ink-400">
              {capsule.sealed_at && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  封存于 {capsule.sealed_at}
                </span>
              )}
              {capsule.opens_on && (
                <span className="rounded-full bg-brand-100 px-2 py-0.5 font-medium text-brand-700">
                  {capsule.opens_on} 可拆封
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 状态 3：可拆封 — 显示信件
  return (
    <div className="card border-l-4 border-l-brand-400 bg-brand-50/40 p-5 animate-fade-in">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Unlock className="h-4 w-4 text-brand-600" />
          <h3 className="font-display font-semibold text-ink-800">来自过去的你</h3>
        </div>
        {capsule.sealed_at && (
          <span className="text-[11px] text-ink-400">写于 {capsule.sealed_at}</span>
        )}
      </div>
      {revealed && capsule.letter ? (
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-700">
            {capsule.letter}
          </p>
        </div>
      ) : (
        <div className="text-center">
          <Button onClick={handleReveal} size="sm">
            <Unlock className="h-3.5 w-3.5" />
            拆开这封信
          </Button>
        </div>
      )}
    </div>
  );
}
