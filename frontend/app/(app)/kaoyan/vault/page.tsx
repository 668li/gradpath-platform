"use client";

// 信任锚橱窗（009 T3）：只上架库内已有的带源数据（院校情报 + 研招网专业目录）。
// 硬红线：零爬取零新增、无 LLM 补洞、无自造概率/分数线；scoreline/adjustment
// 表 0 行 → 不设区块；未命中 → 明说"没有该校的有源数据" + 外链研招网官方查询
// （纯 <a> 跳转，前端绝不代抓 yz.chsi.com.cn）。
import { useEffect, useState } from "react";
import { ExternalLink, Search, ShieldCheck } from "lucide-react";

import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Button, Input } from "@/components/ui/form-controls";
import { gradIntelApi } from "@/lib/api";
import type { GradYanzhaoProgram, IntelResponse } from "@/types";

const YZ_CHATSI = "https://yz.chsi.com.cn/";

function isUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

/** 源角标：URL 可点击溯源；纯文字标签只展示不包装。 */
function SourceChips({ sources }: { sources: string[] }) {
  if (!sources.length) return null;
  return (
    <div className="flex items-center gap-1.5 flex-wrap mt-3">
      {sources.map((s) =>
        isUrl(s) ? (
          <a
            key={s}
            href={s}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors"
          >
            <ShieldCheck className="h-3 w-3" />
            简章源
            <ExternalLink className="h-3 w-3" />
          </a>
        ) : (
          <span
            key={s}
            className="text-xs px-1.5 py-0.5 rounded bg-paper-100 text-ink-500"
          >
            {s}
          </span>
        ),
      )}
    </div>
  );
}

function IntelCard({ intel }: { intel: IntelResponse }) {
  return (
    <div className="bg-white rounded-xl p-5 border border-paper-200">
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span className="font-semibold text-ink-800">{intel.school_name}</span>
        <span className="text-sm text-ink-500">{intel.major_name}</span>
        <span className="text-xs px-1.5 py-0.5 rounded bg-brand-50 text-brand-600">
          {intel.school_tier}
        </span>
        <span className="text-xs text-ink-400">{intel.year}</span>
      </div>
      {intel.ai_summary && (
        <p className="text-sm text-ink-600 leading-relaxed">{intel.ai_summary}</p>
      )}
      <SourceChips sources={intel.data_sources ?? []} />
    </div>
  );
}

function YanzhaoCard({ program }: { program: GradYanzhaoProgram }) {
  return (
    <div className="bg-white rounded-xl p-4 border border-paper-200">
      <div className="flex items-center gap-2 mb-1 flex-wrap">
        <span className="font-semibold text-ink-800">
          {program.university_name}
        </span>
        <span className="text-sm text-ink-500">{program.major_name}</span>
        <span className="text-xs px-1.5 py-0.5 rounded bg-paper-100 text-ink-500">
          {program.degree_type}
        </span>
        <span className="text-xs text-ink-400">{program.year}</span>
      </div>
      {program.department && (
        <p className="text-xs text-ink-400">{program.department}</p>
      )}
      {program.source_url && (
        <a
          href={program.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs inline-flex items-center gap-1 mt-2 px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors"
        >
          <ShieldCheck className="h-3 w-3" />
          官方目录源
          <ExternalLink className="h-3 w-3" />
        </a>
      )}
    </div>
  );
}

export default function KaoyanVaultPage() {
  const [query, setQuery] = useState("");
  const [searched, setSearched] = useState("");
  const [intel, setIntel] = useState<IntelResponse[] | null>(null);
  const [yanzhao, setYanzhao] = useState<GradYanzhaoProgram[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = (school: string) => {
    setLoading(true);
    setError(false);
    Promise.all([
      gradIntelApi.listPublicIntel(
        school ? { school_name: school, limit: 50 } : { limit: 50 },
      ),
      gradIntelApi.listYanzhaoPrograms(
        school ? { university_name: school, limit: 12 } : { limit: 12 },
      ),
    ])
      .then(([i, y]) => {
        setIntel(i);
        setYanzhao(y);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  // 首屏默认装载全部带源数据；搜索时按校名过滤
  useEffect(() => {
    load("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runSearch = () => {
    setSearched(query.trim());
    load(query.trim());
  };

  const nothing = (intel?.length ?? 0) === 0 && (yanzhao?.length ?? 0) === 0;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-ink-800 mb-2">信任锚橱窗</h1>
        <p className="text-ink-500">
          只上架带源数据：每条可点回简章/官方目录溯源；查不到就明说，不编造
        </p>
      </div>

      {/* 搜索 */}
      <div className="flex gap-2 mb-8 max-w-xl">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && runSearch()}
          placeholder="按校名检索有源数据，如：清华大学"
        />
        <Button onClick={runSearch}>
          <Search className="h-4 w-4 mr-1" />
          查询
        </Button>
      </div>

      {loading && <LoadingState text="加载有源数据…" />}

      {error && (
        <EmptyState
          title="数据加载失败"
          description="稍后再试；橱窗只读库内存量，不会现场抓取"
        />
      )}

      {!loading && !error && searched && nothing && (
        <EmptyState
          title={`我们没有「${searched}」的有源数据`}
          description="宁缺勿错：查不到的校名不会生成任何编造条目。官方信息请去研招网查询（外部链接，本站不代抓）。"
          action={
            <a
              href={YZ_CHATSI}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-brand-600 text-white font-medium hover:opacity-90 transition-opacity"
            >
              去研招网官方查询
              <ExternalLink className="h-4 w-4" />
            </a>
          }
        />
      )}

      {!loading && !error && intel && intel.length > 0 && (
        <section className="mb-10">
          <h2 className="font-display font-bold text-ink-800 mb-4">
            院校情报 <span className="text-sm font-normal text-ink-400">（人工整理 · 带简章源）</span>
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {intel.map((item) => (
              <IntelCard key={item.id} intel={item} />
            ))}
          </div>
        </section>
      )}

      {!loading && !error && yanzhao && yanzhao.length > 0 && (
        <section>
          <h2 className="font-display font-bold text-ink-800 mb-4">
            研招网专业目录 <span className="text-sm font-normal text-ink-400">（每条带官方目录源 · 库内共 150 条，搜索可筛）</span>
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {yanzhao.map((item) => (
              <YanzhaoCard key={item.id} program={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
