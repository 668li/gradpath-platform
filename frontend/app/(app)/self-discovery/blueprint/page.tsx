"use client";

// frontend/app/(app)/self-discovery/blueprint/page.tsx
// 《个人人生设计蓝图》文档视图（认识自己 V1）——访谈的产出资产。
// V2 将接入分享（token 防枚举，复用决策报告模式）与 interpret 落地路径卡。

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  BookOpen,
  RotateCcw,
  GitCompareArrows,
  Footprints,
  ArrowLeft,
  History,
} from "lucide-react";
import { lifeDesignApi } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button } from "@/components/ui/form-controls";
import type { LifeDesignBlueprint, BlueprintSummary } from "@/types";

export default function BlueprintPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [blueprint, setBlueprint] = useState<LifeDesignBlueprint | null>(null);
  const [all, setAll] = useState<BlueprintSummary[]>([]);

  useEffect(() => {
    const id = searchParams.get("id");
    const tasks: Promise<void>[] = [];
    if (id) {
      tasks.push(
        lifeDesignApi
          .getBlueprint(id)
          .then((b) => setBlueprint(b))
          .catch(() => {}),
      );
    }
    tasks.push(
      lifeDesignApi
        .listBlueprints()
        .then((list) => {
          setAll(list);
          if (!id && list.length > 0) {
            return lifeDesignApi.getBlueprint(list[0].id).then((b) => setBlueprint(b));
          }
        })
        .catch(() => {}),
    );
    Promise.allSettled(tasks).finally(() => setLoading(false));
  }, [searchParams]);

  if (loading) return <LoadingState text="正在打开你的蓝图…" />;

  if (!blueprint) {
    return (
      <div className="max-w-2xl mx-auto animate-fade-in">
        <EmptyState
          title="还没有人生设计蓝图"
          description="完成一次人生设计访谈，就会在这里生成属于你的《个人人生设计蓝图》"
          action={
            <Button onClick={() => router.push("/self-discovery/interview")}>
              开始人生设计访谈
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <button
          onClick={() => router.push("/self-discovery")}
          className="inline-flex items-center gap-1 text-sm text-ink-400 hover:text-ink-600 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          认识自己
        </button>
        {all.length > 1 && (
          <div className="flex items-center gap-1.5">
            <History className="h-3.5 w-3.5 text-ink-400" />
            {all.map((b) => (
              <button
                key={b.id}
                onClick={() => router.push(`/self-discovery/blueprint?id=${b.id}`)}
                className={cn(
                  "rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
                  b.id === blueprint.id
                    ? "bg-brand-600 text-white"
                    : "bg-paper-100 text-ink-500 hover:bg-paper-200",
                )}
              >
                v{b.version}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 蓝图文档 */}
      <div className="card">
        <div className="border-b border-paper-200 pb-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-100">
              <BookOpen className="h-5 w-5 text-brand-600" strokeWidth={1.8} />
            </div>
            <div>
              <h1 className="font-display text-xl font-semibold text-ink-800">{blueprint.title}</h1>
              <p className="text-xs text-ink-400 mt-0.5">
                生成于 {formatDate(blueprint.created_at)} · 共 {blueprint.content.length} 字
              </p>
            </div>
          </div>
        </div>
        <div className="max-h-[65vh] overflow-y-auto whitespace-pre-line text-sm leading-[1.9] text-ink-700 pr-2">
          {blueprint.content}
        </div>
      </div>

      {/* 落地桥接 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link
          href="/decision-engine"
          className="group rounded-xl border border-paper-300 bg-white p-5 transition-all hover:shadow-md"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
            <GitCompareArrows className="h-5 w-5 text-blue-600" strokeWidth={1.8} />
          </div>
          <h3 className="mt-3 font-display font-semibold text-ink-800">把版本变成报考方案</h3>
          <p className="mt-1 text-xs text-ink-400 leading-relaxed">
            用三路决策引擎检验蓝图里的目标：可报边界、进面线、同分人群，每个数字带溯源
          </p>
        </Link>
        <Link
          href="/micro-actions"
          className="group rounded-xl border border-paper-300 bg-white p-5 transition-all hover:shadow-md"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50">
            <Footprints className="h-5 w-5 text-emerald-600" strokeWidth={1.8} />
          </div>
          <h3 className="mt-3 font-display font-semibold text-ink-800">把原型行动落地 7 天</h3>
          <p className="mt-1 text-xs text-ink-400 leading-relaxed">
            蓝图第四阶段的原型行动，从这里变成每天可执行的小步
          </p>
        </Link>
      </div>

      <div className="text-center">
        <button
          onClick={() => router.push("/self-discovery/interview")}
          className="inline-flex items-center gap-1.5 text-sm text-ink-400 hover:text-brand-600 transition-colors"
        >
          <RotateCcw className="h-4 w-4" />
          重新做一次访谈（生成新版本）
        </button>
      </div>
    </div>
  );
}
