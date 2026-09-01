"use client";

/**
 * 目标条件对照卡 — 技能树从观赏到实用的转型落点。
 *
 * 选定一个真实国考职位（数据来自官方职位表），系统自动生成该职位的
 * 报考条件清单（零手动录入，每条带字段溯源），用户逐条勾选
 * 未满足/进行中/已满足，完成率即北极星指标「条件完成率」的职位级视图。
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Crosshair, Search, RotateCcw, X } from "lucide-react";
import { conditionChecklistApi } from "@/lib/api";
import { gradIntelApi } from "@/lib/api/grad";
import { gwyPositionsApi, provincePositionsApi } from "@/lib/api/gwy";
import { cn } from "@/lib/utils";
import type {
  ConditionChecklistResponse,
  ConditionStatusUpdateRequest,
  MyProfileSummary,
} from "@/types";


const TARGET_POSITION_STORAGE_KEY = "skills:target-position-id";

// 赛道：national=国考 / province=省考
const SOURCES = [
  { key: "national", label: "国考" },
  { key: "province", label: "省考(广东)" },
  { key: "kaoyan", label: "考研" },
] as const;
type SourceKey = (typeof SOURCES)[number]["key"];

const STATUS_ORDER = ["unmet", "in_progress", "met"] as const;
const STATUS_LABEL: Record<string, string> = {
  unmet: "未满足",
  in_progress: "进行中",
  met: "已满足",
};

const STATUS_BUTTON_STYLE: Record<string, string> = {
  unmet: "bg-ink-100 text-ink-600",
  in_progress: "bg-amber-100 text-amber-700",
  met: "bg-brand-600 text-white",
};

function StatusSegment({
  current,
  onChange,
}: {
  current: string;
  onChange: (next: string) => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-paper-300 bg-white p-0.5 shrink-0">
      {STATUS_ORDER.map((s) => (
        <button
          key={s}
          type="button"
          onClick={() => onChange(s)}
          className={cn(
            "rounded-md px-2 py-1 text-[11px] font-medium transition-colors",
            current === s
              ? STATUS_BUTTON_STYLE[s]
              : "text-ink-500 hover:bg-ink-50",
          )}
        >
          {STATUS_LABEL[s]}
        </button>
      ))}
    </div>
  );
}

export function TargetConditionCard() {
  const [source, setSource] = useState<SourceKey>("national");
  const [checklist, setChecklist] = useState<ConditionChecklistResponse | null>(null);
  const [summary, setSummary] = useState<MyProfileSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");
  // 搜索结果统一为最小形状：两个职位表的列表项都满足
  interface PositionOption {
    id: string;
    position_name: string | null;
    dept_name: string | null;
    position_code: string;
    education_req: string | null;
    recruit_count: number | null;
  }
  const [results, setResults] = useState<PositionOption[]>([]);
  const [searching, setSearching] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refreshSummary = useCallback(async () => {
    try {
      setSummary(await conditionChecklistApi.getProfileSummary());
    } catch {
      // 结算接口不可用时不影响清单主流程
    }
  }, []);

  const loadChecklist = useCallback(async (positionId: string, src: SourceKey) => {
    setLoading(true);
    try {
      const data = await conditionChecklistApi.getChecklist(positionId, src);
      setChecklist(data);
      setSource(src);
      refreshSummary();
    } catch {
      // 职位可能已不在当前批次，清掉本地记忆回到搜索态
      localStorage.removeItem(TARGET_POSITION_STORAGE_KEY);
      setChecklist(null);
      setSummary(null);
      setShowSearch(true);
    } finally {
      setLoading(false);
    }
  }, [refreshSummary]);

  // 恢复上次选定的目标职位
  useEffect(() => {
    const saved = localStorage.getItem(TARGET_POSITION_STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as { id: string; source: SourceKey };
        loadChecklist(parsed.id, parsed.source);
        return;
      } catch {
        // 旧格式裸 id → 国考
        loadChecklist(saved, "national");
        return;
      }
    }
    setShowSearch(true);
  }, [loadChecklist]);

  // 关键词搜索（防抖）
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length < 2) {
      setResults([]);
      setSearching(false);
      return;
    }
    setSearching(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const q = query.trim();
        if (source === "kaoyan") {
          const programs = await gradIntelApi.listYanzhaoPrograms({
            university_name: q,
            limit: 4,
          });
          const byMajor =
            programs.length > 0
              ? programs
              : await gradIntelApi.listYanzhaoPrograms({ major_name: q, limit: 4 });
          setResults(
            byMajor.map((p) => ({
              id: String(p.id),
              position_name: p.major_name,
              dept_name: p.university_name,
              position_code: p.department,
              education_req: p.degree_type,
              recruit_count: p.enrollment_quota,
            })),
          );
        } else {
          const resp =
            source === "province"
              ? await provincePositionsApi.list({ q, province: "广东", page_size: 8 })
              : await gwyPositionsApi.list({ q, page_size: 8 });
          setResults(resp.items);
        }
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, source]);

  const selectPosition = (p: PositionOption) => {
    localStorage.setItem(TARGET_POSITION_STORAGE_KEY, JSON.stringify({ id: p.id, source }));
    setQuery("");
    setResults([]);
    setShowSearch(false);
    loadChecklist(p.id, source);
  };

  const clearTarget = () => {
    localStorage.removeItem(TARGET_POSITION_STORAGE_KEY);
    setChecklist(null);
    setSummary(null);
    setShowSearch(true);
  };

  const mark = async (conditionKey: string, status: string) => {
    if (!checklist) return;
    const body: ConditionStatusUpdateRequest = {
      position_id: checklist.position_id,
      exam_source: checklist.exam_source,
      condition_key: conditionKey,
      status,
    };
    // 后端返回更新后的完整清单（含重算的完成率），直接替换状态
    const updated = await conditionChecklistApi.updateStatus(body);
    setChecklist(updated);
    refreshSummary();
  };

  const progress = checklist?.progress;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <Crosshair className="h-4 w-4 text-brand-600 shrink-0" />
          <h2 className="font-semibold text-ink-800 text-sm">目标条件对照</h2>
          <span className="text-xs text-ink-400">· 来自官方职位表，勾选即得完成率</span>
        </div>
        {checklist && (
          <button
            type="button"
            onClick={clearTarget}
            className="text-xs text-ink-400 hover:text-ink-600 inline-flex items-center gap-1"
          >
            <RotateCcw className="h-3 w-3" /> 换个职位
          </button>
        )}
      </div>

      {/* 职位搜索 */}
      {showSearch && (
        <div className="mt-3 relative">
          <div className="flex items-center gap-2 rounded-lg border border-paper-300 bg-white px-3 py-2">
            <Search className="h-4 w-4 text-ink-400 shrink-0" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={
                source === "kaoyan"
                  ? "搜索院校或专业（如：清华大学、计算机）"
                  : "搜索职位名称 / 部门 / 专业（如：海关、计算机）"
              }
              className="flex-1 text-sm outline-none bg-transparent text-ink-800 placeholder:text-ink-300"
            />
            {query && (
              <button type="button" onClick={() => setQuery("")} aria-label="清空搜索">
                <X className="h-4 w-4 text-ink-300 hover:text-ink-500" />
              </button>
            )}
          </div>
          {searching && <p className="text-xs text-ink-400 mt-2 px-1">搜索中…</p>}
          {results.length > 0 && (
            <div className="mt-1 rounded-lg border border-paper-300 bg-white divide-y divide-ink-50 overflow-hidden">
              {results.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => selectPosition(p)}
                  className="w-full text-left px-3 py-2 hover:bg-ink-50 transition-colors"
                >
                  <p className="text-sm font-medium text-ink-800 truncate">
                    {p.dept_name} · {p.position_name}
                  </p>
                  <p className="text-[11px] text-ink-400 truncate">
                    {p.position_code} | {p.education_req} | 招{p.recruit_count ?? "?"}人
                  </p>
                </button>
              ))}
            </div>
          )}
          {!searching && query.trim().length >= 2 && results.length === 0 && (
            <p className="text-xs text-ink-400 mt-2 px-1">没有匹配的职位，换个关键词试试</p>
          )}
        </div>
      )}

      {/* 清单加载中 */}
      {loading && <p className="text-xs text-ink-400 mt-3">加载条件清单…</p>}

      {/* 条件清单 + 完成率 */}
      {checklist && !loading && progress && (
        <>
          <div className="mt-3 flex items-baseline gap-2">
            <p className="text-sm font-medium text-ink-800 truncate">
              {checklist.dept_name} · {checklist.position_name}
            </p>
            <span className="text-[11px] text-ink-400 shrink-0">{checklist.position_code}</span>
          </div>
          <div className="mt-2 flex items-center gap-3">
            <div className="flex-1 h-2 rounded-full bg-paper-200 overflow-hidden">
              <div
                className="h-full rounded-full bg-brand-500 transition-all"
                style={{ width: `${progress.rate}%` }}
              />
            </div>
            <span className="text-sm font-bold text-brand-600 shrink-0">
              {progress.rate}%
            </span>
            <span className="text-[11px] text-ink-400 shrink-0">
              已满足 {progress.met}/{progress.total}
              {progress.in_progress > 0 && ` · 进行中 ${progress.in_progress}`}
            </span>
          </div>

          {/* 可报性结论：回答「能不能报 / 还差什么」 */}
          {summary?.verdict && (
            <div
              className={cn(
                "mt-3 rounded-lg px-3 py-2 text-xs leading-relaxed",
                summary.unmet?.hard_gate?.length
                  ? "bg-rose-50 text-rose-700 border border-rose-100"
                  : "bg-emerald-50 text-emerald-700 border border-emerald-100",
              )}
            >
              <p className="font-medium mb-1">
                {summary.unmet?.hard_gate?.length ? "⚠️ 暂不可报" : "✓ 可报性判定"}
              </p>
              <p>{summary.verdict}</p>
              {summary.unmet?.actionable && summary.unmet.actionable.length > 0 && (
                <div className="mt-2 space-y-1">
                  <p className="font-medium">可补项（不影响报考资格，但提高上岸把握）：</p>
                  {summary.unmet.actionable.map((u) => (
                    <p key={u.key}>
                      · <span className="font-medium">{u.label}</span>
                      {u.hint ? `：${u.hint}` : ""}
                    </p>
                  ))}
                </div>
              )}
              {summary.unmet?.hard_gate
                ? summary.unmet.hard_gate.map((u) => (
                    <p key={u.key} className="mt-1">
                      · <span className="font-medium line-through">{u.label}</span>
                      {u.hint ? `：${u.hint}` : ""}
                    </p>
                  ))
                : null}
            </div>
          )}

          <div className="mt-3 space-y-2">
            {checklist.conditions.map((c) => {
              const status = checklist.statuses[c.key] ?? "unmet";
              return (
                <div
                  key={c.key}
                  className="flex items-center justify-between gap-3 rounded-lg border border-paper-300 bg-white px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-ink-500 flex items-center gap-1.5">
                      {c.label}
                      {c.category === "hard_gate" && (
                        <span className="shrink-0 rounded bg-rose-50 text-rose-500 border border-rose-100 px-1 text-[10px] leading-4">
                          硬门槛
                        </span>
                      )}
                      {c.category === "actionable" && (
                        <span className="shrink-0 rounded bg-amber-50 text-amber-600 border border-amber-100 px-1 text-[10px] leading-4">
                          可补项
                        </span>
                      )}
                      {c.category === "unclassified" && (
                        <span className="shrink-0 rounded bg-ink-50 text-ink-400 border border-ink-100 px-1 text-[10px] leading-4">
                          需人工核对
                        </span>
                      )}
                    </p>
                    <p className="text-sm text-ink-800 truncate" title={c.required}>
                      {c.required}
                    </p>
                  </div>
                  <StatusSegment
                    current={status}
                    onChange={(next) => mark(c.key, next)}
                  />
                </div>
              );
            })}
          </div>
          <p className="text-[11px] text-ink-400 mt-2">
            共 {progress.total} 条硬性/备考条件（「不限」类已自动略去），逐条核对后完成率即你离这个职位的距离
          </p>
        </>
      )}
    </div>
  );
}
