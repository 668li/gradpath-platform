"use client";

import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

/**
 * 安全的 Markdown 渲染组件 — 用于 AI 回复内容展示。
 * 支持 GFM（表格、删除线、任务列表等），禁用 raw HTML 防止 XSS。
 */
export const Markdown = memo(function Markdown({ content, className }: { content: string; className?: string }) {
  return (
    <div
      className={cn(
        "max-w-none text-sm text-slate-700",
        // 段落间距
        "[&_p]:my-2 [&_p]:leading-relaxed",
        // 标题
        "[&_h1]:text-lg [&_h1]:font-semibold [&_h1]:mt-4 [&_h1]:mb-2",
        "[&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-3 [&_h2]:mb-2",
        "[&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mt-3 [&_h3]:mb-1",
        // 列表
        "[&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5",
        "[&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5",
        "[&_li]:my-0.5",
        // 代码
        "[&_code]:rounded [&_code]:bg-slate-100 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:text-xs [&_code]:font-mono",
        "[&_pre]:my-3 [&_pre]:rounded-lg [&_pre]:bg-slate-800 [&_pre]:p-3 [&_pre]:overflow-x-auto",
        "[&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_pre_code]:text-slate-100",
        // 引用
        "[&_blockquote]:border-l-[3px] [&_blockquote]:border-brand-300 [&_blockquote]:bg-brand-50/50 [&_blockquote]:pl-3 [&_blockquote]:py-1 [&_blockquote]:my-2",
        "[&_blockquote]:text-slate-600",
        // 表格
        "[&_table]:w-full [&_table]:my-3 [&_table]:border-collapse",
        "[&_th]:border [&_th]:border-slate-200 [&_th]:bg-slate-50 [&_th]:px-3 [&_th]:py-1.5 [&_th]:text-left [&_th]:text-xs [&_th]:font-semibold",
        "[&_td]:border [&_td]:border-slate-200 [&_td]:px-3 [&_td]:py-1.5 [&_td]:text-xs",
        // 链接
        "[&_a]:text-brand-600 [&_a]:underline hover:[&_a]:text-brand-700",
        // 分割线
        "[&_hr]:my-4 [&_hr]:border-slate-200",
        // 任务列表
        "[&_ul:has(>li>input[type=checkbox])]:list-none [&_ul:has(>li>input[type=checkbox])]:pl-2",
        "[&_input[type=checkbox]]:mr-1.5 [&_input[type=checkbox]]:accent-brand-600",
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  );
});
