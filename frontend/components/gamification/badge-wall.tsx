"use client";

import { BadgeCard } from "./badge-card";
import type { Badge } from "@/types";

interface BadgeWallProps {
  earnedBadges: Badge[];
  availableBadges: Badge[];
}

/**
 * 徽章墙：分「已获得」和「待解锁」两个区块展示徽章网格。
 * 响应式：移动端 2 列，桌面端 3-4 列。
 */
export function BadgeWall({ earnedBadges, availableBadges }: BadgeWallProps) {
  return (
    <div className="space-y-6">
      {/* 已获得 */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-slate-700">
          已获得{" "}
          <span className="font-normal text-slate-400">
            ({earnedBadges.length})
          </span>
        </h3>
        {earnedBadges.length === 0 ? (
          <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50 px-4 py-6 text-center text-sm text-slate-400">
            暂无已获得徽章，继续努力解锁吧！
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
            {earnedBadges.map((b) => (
              <BadgeCard key={b.code} badge={b} earned />
            ))}
          </div>
        )}
      </div>

      {/* 待解锁 */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-slate-700">
          待解锁{" "}
          <span className="font-normal text-slate-400">
            ({availableBadges.length})
          </span>
        </h3>
        {availableBadges.length === 0 ? (
          <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50 px-4 py-6 text-center text-sm text-slate-400">
            所有徽章均已解锁！
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
            {availableBadges.map((b) => (
              <BadgeCard key={b.code} badge={b} earned={false} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
