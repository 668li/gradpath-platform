"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BadgeCheck,
  BookMarked,
  Check,
  Pencil,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { retrospectivesApi } from "@/lib/api";
import type { RetroPrinciple } from "@/lib/api/retrospectives";
import { Badge, Button, Input } from "@/components/ui/form-controls";
import { EmptyState } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

/**
 * 原则库 — 用户复盘经验沉淀（2026-09-25 复盘深化）。
 *
 * 条目三要素：触发条件(if) + 行动指令(then) + 来源案例。
 * 状态机：draft（草稿）→ verified（复验有效 ×N）/ invalid（失效）。
 * 已入库原则自动注入 AI 对话（chat【个人原则】段）——"下次再发生怎么办"。
 */

const STATUS_BADGE: Record<
  RetroPrinciple["status"],
  { label: string; color: "green" | "amber" | "slate" }
> = {
  verified: { label: "已验证", color: "green" },
  draft: { label: "待验证", color: "amber" },
  invalid: { label: "已失效", color: "slate" },
};

export function PrincipleLibrary() {
  const toast = useToast();
  const [principles, setPrinciples] = useState<RetroPrinciple[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await retrospectivesApi.listPrinciples();
      setPrinciples(resp.principles);
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "原则库加载失败", "error");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleVerify = async (
    p: RetroPrinciple,
    verdict: "again" | "ineffective" | "pending",
  ) => {
    try {
      const updated = await retrospectivesApi.verifyPrinciple(p.id, verdict);
      setPrinciples((prev) => prev.map((x) => (x.id === p.id ? updated : x)));
      if (verdict === "again") {
        toast.push(`已验证 ×${updated.verify_count}——好原则越用越准`, "success");
      } else if (verdict === "ineffective") {
        toast.push("已标记失效——留着当反面教材，AI 不再引用", "info");
      }
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "操作失败", "error");
    }
  };

  const handleDelete = async (p: RetroPrinciple) => {
    if (!window.confirm("删除这条原则？（AI 对话将不再引用它）")) return;
    try {
      await retrospectivesApi.removePrinciple(p.id);
      setPrinciples((prev) => prev.filter((x) => x.id !== p.id));
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "删除失败", "error");
    }
  };

  const handleCreate = async (data: {
    trigger_scene: string;
    action: string;
    rationale: string;
  }) => {
    try {
      const created = await retrospectivesApi.createPrinciple({
        trigger_scene: data.trigger_scene,
        action: data.action,
        rationale: data.rationale || null,
      });
      setPrinciples((prev) => [created, ...prev]);
      setCreating(false);
      toast.push("已入库——AI 对话会记住这条原则", "success");
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "创建失败", "error");
    }
  };

  const handleUpdate = async (
    p: RetroPrinciple,
    data: { trigger_scene: string; action: string; rationale: string },
  ) => {
    try {
      const updated = await retrospectivesApi.updatePrinciple(p.id, {
        trigger_scene: data.trigger_scene,
        action: data.action,
        rationale: data.rationale || null,
      });
      setPrinciples((prev) => prev.map((x) => (x.id === p.id ? updated : x)));
      setEditingId(null);
      toast.push("已修订——回待验证状态重新攒验证", "info");
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "修订失败", "error");
    }
  };

  const activeCount = principles.filter((p) => p.status !== "invalid").length;
  const verifiedCount = principles.filter((p) => p.status === "verified").length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold text-ink-800">
            <BookMarked className="h-5 w-5 text-brand-500" />
            我的复盘原则库
          </h2>
          <p className="mt-1 text-sm text-ink-500">
            每条 = 「下次遇到____时 → 我应该____」。
            {activeCount > 0 && (
              <>
                现有 <b className="text-ink-700">{activeCount}</b> 条活跃原则
                {verifiedCount > 0 && <>（{verifiedCount} 条已验证）</>}，AI 对话会在同类情境自动引用。
              </>
            )}
          </p>
        </div>
        <Button onClick={() => setCreating(true)} size="sm">
          <Plus className="h-4 w-4" /> 手动加一条
        </Button>
      </div>

      {creating && (
        <PrincipleEditor
          onCancel={() => setCreating(false)}
          onSave={handleCreate}
        />
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="card space-y-2 p-4">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-2/3" />
            </div>
          ))}
        </div>
      ) : principles.length === 0 ? (
        <EmptyState
          title="原则库是空的"
          description="做完复盘后提炼你的第一条原则——它会长久地帮你在同类情境做对选择"
        />
      ) : (
        <div className="space-y-3">
          {principles.map((p) =>
            editingId === p.id ? (
              <PrincipleEditor
                key={p.id}
                initial={p}
                onCancel={() => setEditingId(null)}
                onSave={(d) => handleUpdate(p, d)}
              />
            ) : (
              <div key={p.id} className={`card p-4 ${p.status === "invalid" ? "opacity-55" : ""}`}>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge color={STATUS_BADGE[p.status].color}>
                    {STATUS_BADGE[p.status].label}
                    {p.status === "verified" && p.verify_count > 0 ? ` ×${p.verify_count}` : ""}
                  </Badge>
                  {p.is_example && (
                    <Badge color="blue">
                      <Sparkles className="mr-1 h-3 w-3" /> 示例
                    </Badge>
                  )}
                  {p.scene_tags.map((t) => (
                    <span
                      key={t}
                      className="rounded-full bg-ink-100 px-2 py-0.5 text-[10px] text-ink-500"
                    >
                      #{t}
                    </span>
                  ))}
                  <div className="ml-auto flex items-center gap-1">
                    {p.status !== "invalid" && (
                      <>
                        <button
                          onClick={() => handleVerify(p, "again")}
                          className="rounded-md p-1.5 text-green-600 hover:bg-green-50"
                          title="最近又用上了且有效 → 验证 +1"
                          aria-label="验证有效"
                        >
                          <BadgeCheck className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleVerify(p, "ineffective")}
                          className="rounded-md p-1.5 text-ink-400 hover:bg-ink-100"
                          title="试了没用 → 标记失效"
                          aria-label="标记失效"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => setEditingId(p.id)}
                      className="rounded-md p-1.5 text-ink-400 hover:bg-ink-100 hover:text-brand-600"
                      aria-label="修订"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(p)}
                      className="rounded-md p-1.5 text-ink-400 hover:bg-red-50 hover:text-red-600"
                      aria-label="删除"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div className="mt-2.5 text-sm leading-6">
                  <p>
                    <span className="text-ink-400">当</span>
                    <span className="font-medium text-ink-800">{p.trigger_scene}</span>
                  </p>
                  <p>
                    <span className="text-ink-400">→ 我应该</span>
                    <span className="text-ink-700">{p.action}</span>
                  </p>
                  {p.rationale && (
                    <p className="mt-1 text-xs text-ink-400">因为 {p.rationale}</p>
                  )}
                </div>

                <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-ink-100 pt-2 text-xs text-ink-400">
                  {p.source_title ? (
                    <span>来源复盘：{p.source_title}</span>
                  ) : (
                    <span>{p.is_example ? "示例原则（可改成你自己的）" : "手动添加"}</span>
                  )}
                  {p.next_review_at && p.status !== "invalid" && (
                    <span className="flex items-center gap-1">
                      <RefreshCw className="h-3 w-3" /> 建议下次回顾：{p.next_review_at}
                    </span>
                  )}
                </div>
              </div>
            ),
          )}
        </div>
      )}
    </div>
  );
}

/* ── 原则编辑器（创建/修订共用） ── */

function PrincipleEditor({
  initial,
  onSave,
  onCancel,
}: {
  initial?: RetroPrinciple;
  onSave: (d: { trigger_scene: string; action: string; rationale: string }) => Promise<void> | void;
  onCancel: () => void;
}) {
  const [trigger, setTrigger] = useState(initial?.trigger_scene ?? "");
  const [action, setAction] = useState(initial?.action ?? "");
  const [rationale, setRationale] = useState(initial?.rationale ?? "");
  const [saving, setSaving] = useState(false);

  const valid = trigger.trim().length >= 6 && action.trim().length >= 6;

  return (
    <div className="card border-brand-200 bg-brand-50/30 p-4">
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-xs text-ink-500">
            触发条件——下次遇到什么情况时？（越具体越容易被想起）
          </label>
          <Input
            value={trigger}
            onChange={(e) => setTrigger(e.target.value)}
            placeholder="当数学大题时间快失控的时候"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-ink-500">
            行动指令——我应该做什么？（要具体可执行，拒绝"更努力"式空话）
          </label>
          <Input
            value={action}
            onChange={(e) => setAction(e.target.value)}
            placeholder="先跳过最后一问，把后面两道大题的第一问拿到手再回头"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-ink-500">原理（选填）——为什么有效？</label>
          <Input
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            placeholder="大题第一问通常是送分步，先收割确定分值"
          />
        </div>
      </div>
      <div className="mt-3 flex justify-end gap-2">
        <Button variant="secondary" size="sm" onClick={onCancel}>
          取消
        </Button>
        <Button
          size="sm"
          disabled={!valid || saving}
          onClick={async () => {
            setSaving(true);
            try {
              await onSave({
                trigger_scene: trigger.trim(),
                action: action.trim(),
                rationale: rationale.trim(),
              });
            } finally {
              setSaving(false);
            }
          }}
        >
          <Check className="h-4 w-4" /> {initial ? "保存修订" : "入库"}
        </Button>
      </div>
    </div>
  );
}
