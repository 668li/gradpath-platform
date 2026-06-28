"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Compass,
  History as TimelineIcon,
  Network,
  ClipboardList,
  Plus,
  ArrowRight,
  MapPin,
} from "lucide-react";
import { dashboardApi } from "@/lib/api";
import { formatDate, cn } from "@/lib/utils";
import {
  DESTINATION_TYPE_LABEL,
  EVENT_TYPE_LABEL,
} from "@/lib/constants";
import { StatCard } from "@/components/stat-card";
import { SkillRadar } from "@/components/charts";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Button } from "@/components/ui/form-controls";
import type { DashboardOverview } from "@/types";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const overview = await dashboardApi.overview();
        if (alive) setData(overview);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  if (loading) return <LoadingState />;
  if (!data) return null;

  const isEmpty =
    data.decisions_count === 0 &&
    data.events_count === 0 &&
    data.skills_count === 0 &&
    data.retrospectives_count === 0;

  const radarData = Object.entries(data.skill_categories).map(
    ([category, count]) => ({ category, count }),
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">个人看板</h1>
          <p className="text-sm text-slate-500 mt-1">
            一览你的职业轨迹全貌
          </p>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="去向决策"
          value={data.decisions_count}
          icon={<Compass className="h-6 w-6" />}
          color="blue"
          hint={data.latest_decision ? DESTINATION_TYPE_LABEL[data.latest_decision.destination_type as keyof typeof DESTINATION_TYPE_LABEL] ?? data.latest_decision.destination_type : "暂无"}
        />
        <StatCard
          label="成长事件"
          value={data.events_count}
          icon={<TimelineIcon className="h-6 w-6" />}
          color="green"
          hint={data.recent_events[0]?.title ?? "暂无"}
        />
        <StatCard
          label="技能节点"
          value={data.skills_count}
          icon={<Network className="h-6 w-6" />}
          color="amber"
          hint={`${Object.keys(data.skill_categories).length} 个分类`}
        />
        <StatCard
          label="阶段复盘"
          value={data.retrospectives_count}
          icon={<ClipboardList className="h-6 w-6" />}
          color="purple"
          hint={data.latest_retrospective?.title ?? "暂无"}
        />
      </div>

      {isEmpty && (
        <EmptyState
          title="欢迎来到 GradPath"
          description="开始记录你的第一条职业轨迹吧。建议从「去向决策」开始，记录你的毕业方向选择。"
          action={
            <Link href="/decisions">
              <Button>
                <Plus className="h-4 w-4" /> 创建第一条决策
              </Button>
            </Link>
          }
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 职业旅程时间线 */}
        <div className="lg:col-span-2 card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-slate-800">职业旅程时间线</h2>
            <Link
              href="/timeline"
              className="text-sm text-brand-600 hover:underline inline-flex items-center"
            >
              查看全部 <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          {data.timeline.length === 0 ? (
            <EmptyState title="暂无时间线数据" description="创建决策或事件后将出现在这里" />
          ) : (
            <TimelineList items={data.timeline.slice(0, 10)} />
          )}
        </div>

        {/* 技能分类雷达图 */}
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-semibold text-slate-800">技能分类分布</h2>
            <Link
              href="/skills"
              className="text-sm text-brand-600 hover:underline"
            >
              管理
            </Link>
          </div>
          {radarData.length === 0 ? (
            <EmptyState title="暂无技能" description="在技能树页面添加你的技能" />
          ) : (
            <SkillRadar data={radarData} />
          )}
        </div>
      </div>

      {/* 最近事件 */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-slate-800">最近事件</h2>
          <Link
            href="/timeline"
            className="text-sm text-brand-600 hover:underline inline-flex items-center"
          >
            查看全部 <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
        {data.recent_events.length === 0 ? (
          <EmptyState title="暂无事件" description="记录入职、晋升、项目等职业事件" />
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.recent_events.map((e) => (
              <li key={e.id} className="flex items-center gap-3 py-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  <TimelineIcon className="h-4 w-4" />
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">
                    {e.title}
                  </p>
                  <p className="text-xs text-slate-400">
                    {EVENT_TYPE_LABEL[e.event_type as keyof typeof EVENT_TYPE_LABEL] ?? e.event_type}
                    {" · "}
                    {formatDate(e.event_date)}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function TimelineList({
  items,
}: {
  items: DashboardOverview["timeline"];
}) {
  return (
    <ol className="relative space-y-4 before:absolute before:left-[7px] before:top-2 before:bottom-2 before:w-px before:bg-slate-200">
      {items.map((item) => {
        const isDecision = item.type === "decision";
        return (
          <li key={`${item.type}-${item.id}`} className="relative pl-7">
            <span
              className={cn(
                "absolute left-0 top-1.5 flex h-[15px] w-[15px] items-center justify-center rounded-full ring-4 ring-white",
                isDecision ? "bg-brand-500" : "bg-green-500",
              )}
            />
            <div className="flex items-baseline justify-between gap-2">
              <p className="text-sm font-medium text-slate-800">
                {isDecision
                  ? `去向决策: ${DESTINATION_TYPE_LABEL[item.title.replace("去向决策: ", "") as keyof typeof DESTINATION_TYPE_LABEL] ?? item.title.replace("去向决策: ", "")}`
                  : item.title}
                {item.subtitle && (
                  <span className="ml-2 text-slate-400 font-normal">
                    {isDecision
                      ? item.subtitle
                      : EVENT_TYPE_LABEL[item.subtitle as keyof typeof EVENT_TYPE_LABEL] ?? item.subtitle}
                  </span>
                )}
              </p>
              <span className="text-xs text-slate-400 whitespace-nowrap">
                {formatDate(item.date)}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {isDecision ? "去向决策" : "成长事件"}
            </p>
          </li>
        );
      })}
    </ol>
  );
}
