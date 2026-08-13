"use client";

import { MapPin } from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import {
  DESTINATION_TYPE_LABEL,
  EVENT_TYPE_LABEL,
} from "@/lib/constants";
import type { DashboardOverview } from "@/types";

export function TimelineList({
  items,
}: {
  items: DashboardOverview["timeline"];
}) {
  return (
    <ol className="relative space-y-4 before:absolute before:left-[7px] before:top-2 before:bottom-2 before:w-px before:bg-paper-300">
      {items.map((item) => {
        const isDecision = item.type === "decision";
        return (
          <li key={`${item.type}-${item.id}`} className="relative pl-7">
            <span
              className={cn(
                "absolute left-0 top-1.5 flex h-[15px] w-[15px] items-center justify-center rounded-full ring-4 ring-white",
                isDecision ? "bg-brand-500" : "bg-brand-300",
              )}
            />
            <div className="flex items-baseline justify-between gap-2">
              <p className="text-sm font-medium text-ink-800">
                {isDecision
                  ? `去向决策: ${DESTINATION_TYPE_LABEL[item.title.replace("去向决策: ", "") as keyof typeof DESTINATION_TYPE_LABEL] ?? item.title.replace("去向决策: ", "")}`
                  : item.title}
                {item.subtitle && (
                  <span className="ml-2 text-ink-400 font-normal">
                    {isDecision
                      ? item.subtitle
                      : EVENT_TYPE_LABEL[item.subtitle as keyof typeof EVENT_TYPE_LABEL] ?? item.subtitle}
                  </span>
                )}
              </p>
              <span className="text-xs text-ink-400 whitespace-nowrap">
                {formatDate(item.date)}
              </span>
            </div>
            <p className="text-xs text-ink-400 mt-0.5 flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {isDecision ? "去向决策" : "成长事件"}
            </p>
          </li>
        );
      })}
    </ol>
  );
}
