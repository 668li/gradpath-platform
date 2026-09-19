"use client";

// 外链目录区块（009 T4）：考研主页与考公"外部工具"tab 同形态渲染。
// 空清单=诚实引导文案（点名制），绝不预填假目录。
import { ExternalLink, LinkIcon } from "lucide-react";

import {
  TOOL_CATEGORY_LABELS,
  TOOL_LINKS,
  type ToolLink,
} from "@/lib/toolLinks";
import { cn } from "@/lib/utils";

function ToolCard({ link }: { link: ToolLink }) {
  return (
    <a
      href={link.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group bg-white rounded-xl p-4 border border-paper-200 hover:shadow-md hover:border-brand-200 transition-all"
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="font-semibold text-ink-800">{link.name}</span>
        <span className="text-xs px-1.5 py-0.5 rounded bg-paper-100 text-ink-500">
          {TOOL_CATEGORY_LABELS[link.category]}
        </span>
        <ExternalLink className="h-3.5 w-3.5 text-ink-300 group-hover:text-brand-500 ml-auto" />
      </div>
      <p className="text-sm text-ink-500">{link.note}</p>
      {link.riskNote && (
        <p className="text-xs text-amber-600 mt-1.5">⚠ {link.riskNote}</p>
      )}
    </a>
  );
}

export function ToolLinksBlock({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-xl border border-paper-200 bg-white p-6", className)}>
      <div className="flex items-center gap-3 mb-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50">
          <LinkIcon className="h-5 w-5 text-brand-600" />
        </div>
        <div>
          <h3 className="font-display font-bold text-ink-800">外部工具目录</h3>
          <p className="text-xs text-ink-400">只收实测可达的站点 · 用户点名制收录</p>
        </div>
      </div>

      {TOOL_LINKS.length === 0 ? (
        <p className="text-sm text-ink-500 leading-relaxed">
          目录暂无收录站点——清单由站长点名后实测再入，不预填、不搬运。
          有想推荐的站点？告诉站长即可。
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {TOOL_LINKS.map((link) => (
            <ToolCard key={link.url} link={link} />
          ))}
        </div>
      )}
    </div>
  );
}
