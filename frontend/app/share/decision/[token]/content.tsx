"use client";

// frontend/app/share/decision/[token]/content.tsx
// 公开报考决策报告分享页（客户端组件）。
// 通过公开接口 /api/share/decision/{token} 拉取匿名化报告，
// 只读渲染 DecisionReport（shared 模式），不含任何回传/分享按钮。

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, Lock, Share2 } from "lucide-react";
import { fetchShareDecision } from "@/lib/api";
import { DecisionReport } from "@/components/decision-engine/decision-report";
import type { DecisionEngineResponse } from "@/types/path-comparison";

export function ShareContent({ token }: { token: string }) {
  const [data, setData] = useState<DecisionEngineResponse | null>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "notfound">("loading");

  useEffect(() => {
    if (!token) {
      setStatus("notfound");
      return;
    }
    let active = true;
    (async () => {
      const result = await fetchShareDecision(token);
      if (!active) return;
      if (result) {
        setData(result);
        setStatus("ok");
      } else {
        setStatus("notfound");
      }
    })();
    return () => {
      active = false;
    };
  }, [token]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-ink-50 to-brand-50/40">
      {/* 顶部栏 */}
      <header className="border-b border-ink-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <Link href="/" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
              <FileText className="h-5 w-5" />
            </span>
            <span className="font-semibold text-ink-800">GradPath · 职径</span>
          </Link>
          <span className="inline-flex items-center gap-1 text-xs text-ink-400">
            <Share2 className="h-3.5 w-3.5" />
            公开决策报告分享
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        {status === "loading" && (
          <div className="flex items-center justify-center py-20 text-ink-400">
            <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-ink-300 border-t-brand-500" />
            <span className="ml-2 text-sm">加载中…</span>
          </div>
        )}

        {status === "notfound" && (
          <div className="card mt-8 flex flex-col items-center py-16 text-center">
            <Lock className="h-12 w-12 text-ink-300" />
            <h1 className="mt-4 text-xl font-semibold text-ink-700">
              分享链接无效或已关闭
            </h1>
            <p className="mt-2 max-w-sm text-sm text-ink-400">
              该决策报告分享链接可能已被撤销，或链接地址有误。
              请联系分享者确认是否仍处于开启状态。
            </p>
          </div>
        )}

        {status === "ok" && data && (
          <div className="space-y-6">
            <DecisionReport result={data} shared />

            {/* 页脚 */}
            <p className="pb-4 text-center text-xs text-ink-400">
              由 GradPath 生成 · 此页面为只读公开分享，不含分享者个人信息
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
