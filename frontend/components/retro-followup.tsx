"use client";

import { useState } from "react";
import { Check, Plus, Sparkles, Trash2, Zap } from "lucide-react";
import { retrospectivesApi } from "@/lib/api";
import { Badge, Button, Input } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";

/**
 * 复盘跟进面板 — 复盘保存后的两件落地事（2026-09-25 复盘深化）：
 * 1. Try 行动卡（≤3 条，KPT 铁律）：带触发场景 + 复审日期的"下次怎么办"
 * 2. AI 提炼原则：从复盘内容提炼 if-then 草稿，用户勾选后入原则库
 *
 * AAR 时间铁律的 UI 化：复盘一半的产出应该花在"下次怎么办"上。
 */

interface FollowupProps {
  retroId: string;
  retroTitle: string;
  /** 供 AI 提炼的复盘内容（成就/挑战/教训/下一步 拼接） */
  retroContent: string;
  period: { start: string; end: string };
  onClose: () => void;
}

export function RetroFollowup({ retroId, retroTitle, retroContent, period, onClose }: FollowupProps) {
  const toast = useToast();
  const [items, setItems] = useState<Array<{ content: string; trigger_scene: string }>>([
    { content: "", trigger_scene: "" },
  ]);
  const [savingActions, setSavingActions] = useState(false);
  const [savedActions, setSavedActions] = useState(false);

  const [drafting, setDrafting] = useState(false);
  const [drafts, setDrafts] = useState<
    Array<{ trigger_scene: string; action: string; rationale: string | null; scene_tags: string[]; picked: boolean }>
  >([]);
  const [savedPrinciples, setSavedPrinciples] = useState(0);

  const validItems = items.filter((i) => i.content.trim().length >= 6 && i.trigger_scene.trim().length >= 4);

  const saveActions = async () => {
    if (!validItems.length) return;
    setSavingActions(true);
    try {
      await retrospectivesApi.createActions(
        retroId,
        validItems.map((i) => ({ content: i.content.trim(), trigger_scene: i.trigger_scene.trim() })),
      );
      setSavedActions(true);
      toast.push(`已存 ${validItems.length} 张行动卡——到期会出现在复盘页顶部提醒你复审`, "success");
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "保存失败", "error");
    } finally {
      setSavingActions(false);
    }
  };

  const draftPrinciples = async () => {
    setDrafting(true);
    try {
      const resp = await retrospectivesApi.principleDraft({
        retro_content: retroContent,
        source_retro_id: retroId,
        period_start: period.start,
        period_end: period.end,
      });
      setDrafts(
        (resp.principles ?? []).map((p) => ({ ...p, picked: true })),
      );
      if (!resp.principles?.length) {
        toast.push("这次复盘没提炼出足够具体的原则——试试在复盘里多写点具体情境", "info");
      }
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "AI 提炼失败（可以手动在原则库添加）", "error");
    } finally {
      setDrafting(false);
    }
  };

  const savePickedPrinciples = async () => {
    const picked = drafts.filter((d) => d.picked);
    if (!picked.length) return;
    let ok = 0;
    for (const d of picked) {
      try {
        await retrospectivesApi.createPrinciple({
          trigger_scene: d.trigger_scene,
          action: d.action,
          rationale: d.rationale,
          scene_tags: d.scene_tags,
          source_retro_id: retroId,
        });
        ok += 1;
      } catch {
        // 单条失败不阻塞其余
      }
    }
    setSavedPrinciples(ok);
    if (ok) toast.push(`${ok} 条原则已入库——AI 对话会在同类情境引用它们`, "success");
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-semibold text-ink-900">
          复盘存好了——现在做最重要的部分：下次怎么办
        </h3>
        <p className="mt-1 text-sm text-ink-500">
          「{retroTitle}」的经验只有变成<b className="text-ink-700">下次遇到同类情况的具体动作</b>
          才算没白复盘。两步都很快。
        </p>
      </div>

      {/* ── 第 1 步：Try 行动卡 ── */}
      <section className="rounded-xl border border-line-200 bg-white p-4">
        <h4 className="mb-1 flex items-center gap-2 text-sm font-semibold text-ink-800">
          <Zap className="h-4 w-4 text-amber-500" /> ① 立几张行动卡（最多 3 张）
        </h4>
        <p className="mb-3 text-xs text-ink-400">
          每张 = 「当____的时候 → 我做____」，14 天后复盘页会提醒你回来验证有没有用
        </p>
        {savedActions ? (
          <p className="flex items-center gap-2 text-sm text-green-600">
            <Check className="h-4 w-4" /> 行动卡已保存
          </p>
        ) : (
          <div className="space-y-2">
            {items.map((it, idx) => (
              <div key={idx} className="grid grid-cols-1 gap-2 rounded-lg bg-ink-50 p-2 sm:grid-cols-[1fr_1fr_auto]">
                <Input
                  value={it.trigger_scene}
                  onChange={(e) =>
                    setItems((prev) =>
                      prev.map((x, i) => (i === idx ? { ...x, trigger_scene: e.target.value } : x)),
                    )
                  }
                  placeholder="当____的时候"
                  className="!py-1.5 text-sm"
                />
                <Input
                  value={it.content}
                  onChange={(e) =>
                    setItems((prev) =>
                      prev.map((x, i) => (i === idx ? { ...x, content: e.target.value } : x)),
                    )
                  }
                  placeholder="我要做____（具体动作）"
                  className="!py-1.5 text-sm"
                />
                <div className="flex items-center gap-1">
                  {idx > 0 && (
                    <button
                      onClick={() => setItems((prev) => prev.filter((_, i) => i !== idx))}
                      className="rounded-md p-1.5 text-ink-400 hover:bg-red-50 hover:text-red-500"
                      aria-label="删除此卡"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                  {idx === items.length - 1 && items.length < 3 && (
                    <button
                      onClick={() => setItems((prev) => [...prev, { content: "", trigger_scene: "" }])}
                      className="rounded-md p-1.5 text-brand-600 hover:bg-brand-50"
                      aria-label="加一张"
                    >
                      <Plus className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
            <div className="flex justify-end">
              <Button size="sm" disabled={!validItems.length || savingActions} onClick={saveActions}>
                {savingActions ? "保存中…" : `保存 ${validItems.length} 张行动卡`}
              </Button>
            </div>
          </div>
        )}
      </section>

      {/* ── 第 2 步：AI 提炼原则 ── */}
      <section className="rounded-xl border border-line-200 bg-white p-4">
        <h4 className="mb-1 flex items-center gap-2 text-sm font-semibold text-ink-800">
          <Sparkles className="h-4 w-4 text-brand-500" /> ② 让 AI 帮你把经验提炼成原则
        </h4>
        <p className="mb-3 text-xs text-ink-400">
          从这份复盘提炼「触发条件 → 行动」条目，入库后 AI 对话会在同类情境自动引用
        </p>
        {!drafts.length ? (
          <Button size="sm" variant="secondary" onClick={draftPrinciples} disabled={drafting}>
            {drafting ? "提炼中…" : "AI 提炼原则草稿"}
          </Button>
        ) : savedPrinciples > 0 ? (
          <p className="flex items-center gap-2 text-sm text-green-600">
            <Check className="h-4 w-4" /> {savedPrinciples} 条原则已入原则库
          </p>
        ) : (
          <div className="space-y-2">
            {drafts.map((d, i) => (
              <label
                key={i}
                className="flex cursor-pointer items-start gap-2 rounded-lg border border-line-200 p-3 hover:bg-ink-50"
              >
                <input
                  type="checkbox"
                  checked={d.picked}
                  onChange={() =>
                    setDrafts((prev) =>
                      prev.map((x, xi) => (xi === i ? { ...x, picked: !x.picked } : x)),
                    )
                  }
                  className="mt-1 h-4 w-4 accent-brand-500"
                />
                <div className="min-w-0 flex-1 text-sm leading-6">
                  <p>
                    <span className="text-ink-400">当</span>
                    <span className="font-medium text-ink-800">{d.trigger_scene}</span>
                    <span className="text-ink-400">→ </span>
                    <span className="text-ink-700">{d.action}</span>
                  </p>
                  {d.scene_tags.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {d.scene_tags.map((t) => (
                        <Badge key={t} color="blue">
                          #{t}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </label>
            ))}
            <div className="flex justify-end">
              <Button
                size="sm"
                onClick={savePickedPrinciples}
                disabled={!drafts.some((d) => d.picked)}
              >
                入库选中的 {drafts.filter((d) => d.picked).length} 条
              </Button>
            </div>
          </div>
        )}
      </section>

      <div className="flex justify-end">
        <Button variant="secondary" onClick={onClose}>
          {savedActions || savedPrinciples ? "完成" : "跳过（以后也可以补）"}
        </Button>
      </div>
    </div>
  );
}
