"use client";

import Link from "next/link";
import {
  Shield,
  Flag,
  Users,
  Bug,
  Inbox,
  Network,
  ArrowRight,
} from "lucide-react";

const ADMIN_CARDS = [
  {
    href: "/admin/moderation",
    title: "内容审核",
    desc: "审核待发布的经验贴与问答，通过或拒绝",
    icon: Shield,
    color: "text-brand-600 bg-brand-50",
  },
  {
    href: "/admin/reports",
    title: "举报管理",
    desc: "处理用户举报：下架违规内容、联动封禁作者",
    icon: Flag,
    color: "text-red-600 bg-red-50",
  },
  {
    href: "/admin/users",
    title: "用户管理",
    desc: "搜索用户、封禁违规账号 / 解封恢复",
    icon: Users,
    color: "text-blue-600 bg-blue-50",
  },
  {
    href: "/admin/crawlers",
    title: "爬虫管理",
    desc: "查看采集任务运行状态与调度",
    icon: Bug,
    color: "text-emerald-600 bg-emerald-50",
  },
  {
    href: "/admin/research-queue",
    title: "调研数据审核",
    desc: "人工确认采集数据入库（真实数据红线）",
    icon: Inbox,
    color: "text-purple-600 bg-purple-50",
  },
  {
    href: "/admin/skills",
    title: "技能管理",
    desc: "维护技能树节点与分类",
    icon: Network,
    color: "text-amber-600 bg-amber-50",
  },
];

export default function AdminHomePage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink-800 tracking-tight">
          后台管理
        </h1>
        <p className="mt-1 text-sm text-ink-500">
          社区治理与内容运营工作台
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {ADMIN_CARDS.map((card) => {
          const Icon = card.icon;
          return (
            <Link
              key={card.href}
              href={card.href}
              className="group flex flex-col gap-3 rounded-2xl border border-paper-300 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
            >
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-xl ${card.color}`}
              >
                <Icon className="h-5 w-5" strokeWidth={2} />
              </div>
              <div>
                <p className="flex items-center gap-1.5 font-semibold text-ink-800">
                  {card.title}
                  <ArrowRight className="h-3.5 w-3.5 text-ink-300 transition-transform group-hover:translate-x-0.5" />
                </p>
                <p className="mt-1 text-xs leading-relaxed text-ink-500">
                  {card.desc}
                </p>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
