"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { GraduationCap, Share2, Lock } from "lucide-react";
import { fetchShareSkills } from "@/lib/api";
import type { ShareableSkills } from "@/types";

/**
 * 公开技能分享页面内容（客户端组件）。
 *
 * 路由：/share/skills/[token]
 * 通过公开接口 /api/share/skills/{token} 拉取技能数据。
 * 仅展示用户姓名与技能树，不包含任何其他个人数据。
 */
export function ShareContent({ token }: { token: string }) {
  const [data, setData] = useState<ShareableSkills | null>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "notfound">("loading");

  useEffect(() => {
    if (!token) {
      setStatus("notfound");
      return;
    }
    let active = true;
    (async () => {
      const result = await fetchShareSkills(token);
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

  // 按分类分组的技能
  const groupedSkills = useMemo(() => {
    if (!data?.skills?.length) return [];
    const map = new Map<string, ShareableSkills["skills"]>();
    data.skills.forEach((s) => {
      const cat = s.category || "未分类";
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat)!.push(s);
    });
    return Array.from(map.entries());
  }, [data]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-ink-50 to-brand-50/40">
      {/* 顶部栏 */}
      <header className="border-b border-ink-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <Link href="/" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
              <GraduationCap className="h-5 w-5" />
            </span>
            <span className="font-semibold text-ink-800">GradPath · 职径</span>
          </Link>
          <span className="inline-flex items-center gap-1 text-xs text-ink-400">
            <Share2 className="h-3.5 w-3.5" />
            公开技能分享
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
              该技能分享链接可能已被撤销，或链接地址有误。
              请联系分享者确认是否仍处于开启状态。
            </p>
          </div>
        )}

        {status === "ok" && data && (
          <div className="space-y-6">
            {/* 用户标题 */}
            <div className="card flex items-center gap-4">
              <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-100 text-2xl font-bold text-brand-600">
                {data.user_name?.charAt(0) || "?"}
              </span>
              <div>
                <h1 className="text-2xl font-bold text-ink-800">
                  {data.user_name} 的技能树
                </h1>
                <p className="mt-1 text-sm text-ink-500">
                  共 {data.skills.length} 项技能 ·{" "}
                  {groupedSkills.length} 个分类
                </p>
              </div>
            </div>

            {/* 技能列表（按分类分组） */}
            {data.skills.length === 0 ? (
              <div className="card py-12 text-center text-ink-400">
                该用户暂未公开任何技能。
              </div>
            ) : (
              <div className="space-y-4">
                {groupedSkills.map(([category, skills]) => (
                  <section key={category} className="card">
                    <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink-700">
                      <span className="inline-block h-3 w-3 rounded-sm bg-brand-500" />
                      {category}
                      <span className="text-xs font-normal text-ink-400">
                        ({skills.length})
                      </span>
                    </h2>
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {skills.map((skill) => (
                        <div
                          key={skill.id}
                          className="rounded-lg border border-ink-200 bg-ink-50/60 p-3"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-ink-800">
                              {skill.name}
                            </span>
                            <span className="text-xs font-medium text-amber-600">
                              {"★".repeat(Math.min(5, skill.level))}
                              <span className="text-ink-300">
                                {"★".repeat(Math.max(0, 5 - skill.level))}
                              </span>
                            </span>
                          </div>
                          <div className="mt-1 flex items-center gap-3 text-xs text-ink-500">
                            <span>等级 Lv.{skill.level}</span>
                            {skill.acquired_date && (
                              <span>· {skill.acquired_date}</span>
                            )}
                          </div>
                          {skill.notes && (
                            <p className="mt-2 text-xs text-ink-500">
                              {skill.notes}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            )}

            {/* 页脚 */}
            <p className="pb-4 text-center text-xs text-ink-400">
              由 GradPath 生成 · 此页面为只读公开分享
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
