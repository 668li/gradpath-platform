"use client";

// 门道库（/intel/cards，批次 B+ 2026-09-26）：门道信息差的"库"出口。
// 内容为公开信息提炼、非官方；置信度三档徽章逐卡明标；孤证卡警示标注。

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, BadgeCheck, ExternalLink, ShieldAlert, Users } from "lucide-react";
import { intelCardsApi, type IntelCard, type IntelQuestionGroup } from "@/lib/api/intel-cards";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { cn } from "@/lib/utils";

const CATEGORY_META: Record<string, { label: string; desc: string }> = {
  rule: { label: "A 组·门道潜规则", desc: "官方不说、约定俗成的做法" },
  circle: { label: "C 组·圈内消息", desc: "圈内流传、官方不发布的动态信号" },
  evidence: { label: "D 组·内幕实锤", desc: "可交叉验证的硬证据与判定方法" },
};

function ConfidenceBadge({ confidence }: { confidence: string }) {
  if (confidence === "official") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
        <BadgeCheck className="h-3 w-3" /> 官方实证
      </span>
    );
  }
  if (confidence === "multi_source") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
        <Users className="h-3 w-3" /> 多源交叉
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
      <ShieldAlert className="h-3 w-3" /> 孤证（单一来源）
    </span>
  );
}

function CardItem({ card }: { card: IntelCard }) {
  return (
    <div className="rounded-xl border border-paper-200 bg-white p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <ConfidenceBadge confidence={card.confidence} />
        <span className="text-xs text-ink-400">时效：{card.as_of}</span>
      </div>
      <h4 className="font-medium text-ink-800">{card.title}</h4>
      <p className="mt-1.5 text-sm leading-relaxed text-ink-600">{card.conclusion}</p>
      {card.conditions && (
        <p className="mt-2 text-xs leading-relaxed text-ink-500">
          <span className="font-medium text-ink-600">适用条件：</span>
          {card.conditions}
        </p>
      )}
      {card.counterexample && (
        <p className="mt-1 text-xs leading-relaxed text-ink-500">
          <span className="font-medium text-ink-600">反例/例外：</span>
          {card.counterexample}
        </p>
      )}
      {card.sources.length > 0 && (
        <div className="mt-3 border-t border-paper-100 pt-2">
          <p className="text-xs font-medium text-ink-500">来源链（可点开查证）：</p>
          <ul className="mt-1 space-y-1">
            {card.sources.map((s, i) => (
              <li key={i} className="text-xs">
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-brand-600 hover:underline"
                >
                  <ExternalLink className="h-3 w-3" />
                  {s.title || s.url}
                </a>
                {s.supports && <span className="ml-1 text-ink-400">— {s.supports}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function IntelCardsPage() {
  const [groups, setGroups] = useState<IntelQuestionGroup[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    intelCardsApi
      .byQuestion()
      .then((d) => {
        setGroups(d.groups);
        setTotal(d.total);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4">
        <Link
          href="/intel"
          className="inline-flex items-center gap-1 text-sm text-ink-400 hover:text-ink-600"
        >
          <ArrowLeft className="h-4 w-4" /> 情报中心
        </Link>
      </div>
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-ink-800">考研门道库</h1>
        <p className="mt-1 text-sm text-ink-500">
          官方不会说、圈内才知道的门道与实锤——每条带来源链与置信度，可点开查证。
        </p>
      </div>

      <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50/60 px-4 py-3 text-xs leading-relaxed text-amber-800">
        免责声明：本库内容为公开信息提炼、非官方；「孤证」卡为单一来源观点，请谨慎采信；
        招生政策年年调整，请以目标院校最新官方公告为准。
      </div>

      {loading ? (
        <LoadingState text="加载门道卡…" />
      ) : total === 0 ? (
        <EmptyState
          title="暂无门道卡"
          description="门道卡按「多源交叉验证」标准策展，宁缺毋滥；暂无满足标准的卡片。"
        />
      ) : (
        <div className="space-y-8">
          {(["rule", "circle", "evidence"] as const).map((cat) => {
            const catGroups = groups.filter((g) => g.category === cat);
            if (catGroups.length === 0) return null;
            const meta = CATEGORY_META[cat];
            return (
              <section key={cat}>
                <div className="mb-3">
                  <h2 className="text-lg font-semibold text-ink-800">{meta.label}</h2>
                  <p className="text-xs text-ink-400">{meta.desc}</p>
                </div>
                <div className="space-y-5">
                  {catGroups.map((g) => (
                    <div key={g.question_id}>
                      <h3 className="mb-2 flex items-baseline gap-2 text-sm font-medium text-ink-700">
                        <span className="rounded bg-paper-100 px-1.5 py-0.5 font-mono text-xs text-ink-500">
                          {g.question_id}
                        </span>
                        {g.question_text}
                      </h3>
                      <div className={cn("grid gap-3", g.cards.length > 1 && "md:grid-cols-2")}>
                        {g.cards.map((c) => (
                          <CardItem key={c.id} card={c} />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
