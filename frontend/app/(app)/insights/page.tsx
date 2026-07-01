"use client";

import { useCallback, useEffect, useState } from "react";
import { TrendingUp } from "lucide-react";
import { gamificationApi } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { LoadingState } from "@/components/ui/empty";
import { LevelProgress } from "@/components/gamification/level-progress";
import { BadgeWall } from "@/components/gamification/badge-wall";
import { NewBadgeToast } from "@/components/gamification/new-badge-toast";
import { GrowthInsight } from "@/components/growth-insight";
import type { GamificationProfile, Badge } from "@/types";

export default function InsightsPage() {
  const toast = useToast();
  const [profile, setProfile] = useState<GamificationProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [newBadges, setNewBadges] = useState<Badge[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const p = await gamificationApi.profile();
      setProfile(p);
      // 若有新获得的徽章，弹出提示
      if (p.newly_awarded && p.newly_awarded.length > 0) {
        setNewBadges(p.newly_awarded);
      }
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">成长洞察</h1>
        <p className="mt-1 text-sm text-slate-500">
          纵览你的成长轨迹，AI 助你发现优势与差距
        </p>
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

          {/* AI 成长洞察 */}
          <GrowthInsight />

          {/* 最近成就 */}
          <div className="card">
            <div className="mb-4 flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-brand-600" />
              <h2 className="font-semibold text-slate-800">最近成就</h2>
            </div>
            <BadgeWall
              earnedBadges={profile.earned_badges}
              availableBadges={[]}
            />
          </div>
        </>
      ) : null}

      {/* 新徽章提示 */}
      <NewBadgeToast badges={newBadges} onDismiss={() => setNewBadges([])} />
    </div>
  );
}
