"use client";

import { useCallback, useEffect, useState } from "react";
import { Award, Zap, Star, TrendingUp, Share2, Copy, Check, Link2 } from "lucide-react";
import { gamificationApi } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { LoadingState } from "@/components/ui/empty";
import { LevelProgress } from "@/components/gamification/level-progress";
import { BadgeWall } from "@/components/gamification/badge-wall";
import { ExportButton } from "@/components/export-button";
import type { GamificationProfile, UserSetting } from "@/types";

export default function AchievementsPage() {
  const toast = useToast();
  const [profile, setProfile] = useState<GamificationProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // 分享设置
  const [settings, setSettings] = useState<UserSetting | null>(null);
  const [toggling, setToggling] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, s] = await Promise.all([
        gamificationApi.profile(),
        gamificationApi.getSettings(),
      ]);
      setProfile(p);
      setSettings(s);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const shareLink =
    settings?.share_skills_enabled && settings.share_token
      ? `${typeof window !== "undefined" ? window.location.origin : ""}/share/skills/${settings.share_token}`
      : "";

  const handleToggleShare = async (enabled: boolean) => {
    setToggling(true);
    try {
      const updated = await gamificationApi.updateSettings({
        share_skills_enabled: enabled,
      });
      setSettings(updated);
      toast.push(
        enabled ? "已开启技能分享" : "已关闭技能分享",
        "success",
      );
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "更新失败", "error");
    } finally {
      setToggling(false);
    }
  };

  const handleCopyLink = async () => {
    if (!shareLink) return;
    try {
      await navigator.clipboard.writeText(shareLink);
      setCopied(true);
      toast.push("分享链接已复制", "success");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.push("复制失败，请手动复制链接", "error");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="page-title">成就墙</h1>
          <p className="mt-1 text-sm text-slate-500">
            记录你的成长里程碑，解锁更多徽章
          </p>
        </div>
        <ExportButton />
      </div>

      {loading ? (
        <LoadingState />
      ) : profile ? (
        <>
          {/* 等级进度 */}
          <div className="card">
            <LevelProgress
              xp={profile.xp}
              level={profile.level}
              levelName={profile.level_name}
              progress={profile.progress}
            />
          </div>

          {/* 经验值明细 */}
          <div className="card">
            <div className="mb-4 flex items-center gap-2">
              <Zap className="h-5 w-5 text-brand-600" />
              <h2 className="font-semibold text-slate-800">经验值明细</h2>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-100 text-brand-600">
                  <TrendingUp className="h-5 w-5" />
                </span>
                <div>
                  <p className="text-xs text-slate-500">当前等级</p>
                  <p className="text-lg font-bold text-slate-800">
                    Lv.{profile.level}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
                  <Zap className="h-5 w-5" />
                </span>
                <div>
                  <p className="text-xs text-slate-500">累计经验</p>
                  <p className="text-lg font-bold text-slate-800">
                    {profile.xp} XP
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 text-green-600">
                  <Star className="h-5 w-5" />
                </span>
                <div>
                  <p className="text-xs text-slate-500">已获徽章</p>
                  <p className="text-lg font-bold text-slate-800">
                    {profile.earned_badges.length} 枚
                  </p>
                </div>
              </div>
            </div>
            <div className="mt-3 rounded-lg bg-brand-50 px-4 py-3">
              <p className="text-sm text-brand-700">
                距离下一级还需{" "}
                <span className="font-semibold">
                  {Math.max(0, profile.progress.needed - profile.progress.current)} XP
                </span>
                ，当前进度 {profile.progress.percent}%
              </p>
            </div>
          </div>

          {/* 徽章墙 */}
          <div className="card">
            <div className="mb-4 flex items-center gap-2">
              <Award className="h-5 w-5 text-brand-600" />
              <h2 className="font-semibold text-slate-800">徽章收藏</h2>
            </div>
            <BadgeWall
              earnedBadges={profile.earned_badges}
              availableBadges={profile.available_badges}
            />
          </div>

          {/* 技能分享设置 */}
          <div className="card">
            <div className="mb-4 flex items-center gap-2">
              <Share2 className="h-5 w-5 text-brand-600" />
              <h2 className="font-semibold text-slate-800">技能分享</h2>
            </div>
            <p className="mb-4 text-sm text-slate-500">
              开启后可生成一个公开链接，他人无需登录即可查看你的技能树（仅展示姓名与技能，不含其他个人数据）。
            </p>

            {/* 开关 */}
            <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
              <div>
                <p className="text-sm font-medium text-slate-700">公开技能树</p>
                <p className="text-xs text-slate-400">
                  {settings?.share_skills_enabled ? "已开启，链接可访问" : "已关闭，链接不可访问"}
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={settings?.share_skills_enabled ?? false}
                disabled={toggling}
                onClick={() => handleToggleShare(!settings?.share_skills_enabled)}
                className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                  settings?.share_skills_enabled ? "bg-brand-600" : "bg-slate-300"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings?.share_skills_enabled ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>

            {/* 分享链接 */}
            {settings?.share_skills_enabled && shareLink && (
              <div className="mt-3">
                <label className="mb-1 block text-xs font-medium text-slate-500">
                  分享链接
                </label>
                <div className="flex items-center gap-2">
                  <div className="flex flex-1 items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2">
                    <Link2 className="h-4 w-4 shrink-0 text-slate-400" />
                    <input
                      readOnly
                      value={shareLink}
                      onClick={(e) => (e.target as HTMLInputElement).select()}
                      className="w-full truncate bg-transparent text-sm text-slate-700 outline-none"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleCopyLink}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                  >
                    {copied ? (
                      <>
                        <Check className="h-4 w-4 text-green-600" />
                        已复制
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4" />
                        复制
                      </>
                    )}
                  </button>
                </div>
                <a
                  href={shareLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-block text-xs text-brand-600 hover:underline"
                >
                  在新标签页预览 →
                </a>
              </div>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
