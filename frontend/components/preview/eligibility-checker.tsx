"use client";

/**
 * 免费可报性预览 — 免登录「先尝一口」的转化漏斗入口。
 *
 * 访客无需注册：搜职位/院校 → 勾身份字段 → 立即看到可报性判定和卡在哪。
 * 与登录后条件账本共用同一套后端判定；考研赛道看「估分 vs 复试线」档位。
 * 所有请求走 request()（免登录）；结果卡底部给「登录保存这份判定」引导。
 *
 * 落地页（/）与独立公开路由（/preview）共用此组件。
 */

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Crosshair, Play, RotateCcw, Search, X } from "lucide-react";
import { authApi } from "@/lib/api/auth";
import { getToken } from "@/lib/api/client";
import { gradIntelApi } from "@/lib/api/grad";
import { gwyPositionsApi, provincePositionsApi } from "@/lib/api/gwy";
import { conditionPreviewApi, type ConditionPreviewResponse } from "@/lib/api/preview";
import {
  clearIdentitySnapshot,
  isIdentitySnapshotEmpty,
  loadIdentitySnapshot,
  saveIdentitySnapshot,
} from "@/lib/identity-snapshot";
import { cn } from "@/lib/utils";
import type { GwyPositionResponse, GwyProvincePositionResponse, GradYanzhaoProgram } from "@/types";


const SOURCES = [
  { key: "national", label: "国考" },
  { key: "province", label: "省考" },
  { key: "kaoyan", label: "考研" },
] as const;
type SourceKey = (typeof SOURCES)[number]["key"];

// 身份字段取值（与决策引擎 engine-form 同源，保证口径一致）
const FRESH_STATUSES = [
  { value: "", label: "不限" },
  { value: "应届", label: "应届毕业生" },
  { value: "非应届", label: "非应届" },
];
const PARTY_STATUSES = [
  { value: "", label: "不限" },
  { value: "中共党员", label: "中共党员" },
  { value: "党员或团员", label: "中共党员或共青团员" },
  { value: "群众", label: "群众" },
];
const EDUCATIONS = [
  { value: "", label: "不限" },
  { value: "本科", label: "本科" },
  { value: "硕士", label: "硕士" },
  { value: "博士", label: "博士" },
  { value: "大专", label: "大专" },
];
const GENDERS = [
  { value: "", label: "不限" },
  { value: "男", label: "男" },
  { value: "女", label: "女" },
];
const GRASSROOTS = [
  { value: "", label: "不限" },
  { value: "yes", label: "已满足" },
  { value: "no", label: "不满足" },
];

// 搜索结果为最小统一形状：国考/省考/考研三个 API 都满足
interface PositionOption {
  id: string;
  position_name: string | null;
  dept_name: string | null;
  position_code: string;
  education_req: string | null;
  recruit_count: number | null;
  source: SourceKey;
}

interface IdentityState {
  fresh_status: string;
  party_status: string;
  education: string;
  gender: string;
  grassroots: string; // "" | "yes" | "no"
  estimated_score: string;
  kaoyan_estimated_score: string;
}

const EMPTY_IDENTITY: IdentityState = {
  fresh_status: "",
  party_status: "",
  education: "",
  gender: "",
  grassroots: "",
  estimated_score: "",
  kaoyan_estimated_score: "",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-medium text-ink-500">{label}</span>
      {children}
    </label>
  );
}

function SelectField({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-paper-300 bg-white px-2.5 py-2 text-sm text-ink-800 outline-none focus:border-brand-400"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export function EligibilityChecker() {
  const [source, setSource] = useState<SourceKey>("national");
  const [identity, setIdentity] = useState<IdentityState>(EMPTY_IDENTITY);
  const [selected, setSelected] = useState<PositionOption | null>(null);

  // 搜索态
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PositionOption[]>([]);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 判定
  const [verdict, setVerdict] = useState<ConditionPreviewResponse | null>(null);
  const [verdictLoading, setVerdictLoading] = useState(false);
  const [verdictError, setVerdictError] = useState<string | null>(null);

  // 登录态与档案保存（W1-D3/D4 身份包预填）
  const [loggedIn, setLoggedIn] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");

  const setIdentityField = (key: keyof IdentityState, value: string) =>
    setIdentity((prev) => ({ ...prev, [key]: value }));

  // 身份包预填：登录用户读档案，访客读上次预览快照（刷新不丢）
  useEffect(() => {
    const boolToStr = (v: boolean | null | undefined) =>
      v === null || v === undefined ? "" : v ? "yes" : "no";
    if (getToken()) {
      setLoggedIn(true);
      authApi
        .me()
        .then((user) => {
          setIdentity((prev) => ({
            ...prev,
            fresh_status: user.fresh_status ?? prev.fresh_status,
            party_status: user.party_status ?? prev.party_status,
            education: user.education ?? prev.education,
            gender: user.gender ?? prev.gender,
            grassroots: boolToStr(user.has_grassroots) || prev.grassroots,
          }));
        })
        .catch(() => {
          // 档案读取失败不阻塞预览主流程
        });
    } else {
      const snap = loadIdentitySnapshot();
      if (!isIdentitySnapshotEmpty(snap)) {
        setIdentity((prev) => ({
          ...prev,
          fresh_status: snap!.fresh_status ?? prev.fresh_status,
          party_status: snap!.party_status ?? prev.party_status,
          education: snap!.education ?? prev.education,
          gender: snap!.gender ?? prev.gender,
          grassroots: boolToStr(snap!.has_grassroots) || prev.grassroots,
        }));
      }
    }
  }, []);

  // 关键词搜索（防抖，复用 target-condition-card 的搜索模式）
  const doSearch = useCallback(async (q: string, src: SourceKey) => {
    setSearching(true);
    try {
      if (src === "kaoyan") {
        const programs = await gradIntelApi.listYanzhaoPrograms({
          university_name: q,
          limit: 5,
        });
        const byMajor =
          programs.length > 0
            ? programs
            : await gradIntelApi.listYanzhaoPrograms({ major_name: q, limit: 5 });
        setResults(
          byMajor.map((p: GradYanzhaoProgram) => ({
            id: String(p.id),
            position_name: p.major_name,
            dept_name: p.university_name,
            position_code: p.department,
            education_req: p.degree_type,
            recruit_count: p.enrollment_quota,
            source: "kaoyan",
          })),
        );
      } else {
        const resp =
          src === "province"
            ? await provincePositionsApi.list({ q, province: "广东", page_size: 8 })
            : await gwyPositionsApi.list({ q, page_size: 8 });
        setResults(
          resp.items.map((p: GwyPositionResponse | GwyProvincePositionResponse) => ({
            id: String(p.id),
            position_name: p.position_name,
            dept_name: p.dept_name,
            position_code: p.position_code,
            education_req: p.education_req,
            recruit_count: p.recruit_count,
            source: src,
          })),
        );
      }
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  const handleQueryChange = (q: string) => {
    setQuery(q);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (q.trim().length < 2) {
      setResults([]);
      setSearching(false);
      return;
    }
    debounceRef.current = setTimeout(() => doSearch(q.trim(), source), 300);
  };

  const switchSource = (src: SourceKey) => {
    setSource(src);
    setSelected(null);
    setVerdict(null);
    setVerdictError(null);
    setResults([]);
    setQuery("");
  };

  const selectPosition = (p: PositionOption) => {
    setSelected(p);
    setQuery("");
    setResults([]);
    setVerdict(null);
    setVerdictError(null);
  };

  const runPreview = async () => {
    if (!selected) return;
    setVerdictLoading(true);
    setVerdictError(null);
    try {
      const data = await conditionPreviewApi.preview({
        exam_source: selected.source,
        position_ref: selected.id,
        fresh_status: identity.fresh_status || undefined,
        party_status: identity.party_status || undefined,
        education: identity.education || undefined,
        gender: identity.gender || undefined,
        has_grassroots:
          identity.grassroots === "" ? undefined : identity.grassroots === "yes",
        estimated_score: identity.estimated_score
          ? Number(identity.estimated_score)
          : undefined,
        kaoyan_estimated_score: identity.kaoyan_estimated_score
          ? Number(identity.kaoyan_estimated_score)
          : undefined,
      });
      setVerdict(data);
      // 身份快照：注册/登录时带回（W1-D3/D4），仅存身份字段不含估分
      saveIdentitySnapshot({
        fresh_status: identity.fresh_status || null,
        party_status: identity.party_status || null,
        education: identity.education || null,
        gender: identity.gender || null,
        has_grassroots:
          identity.grassroots === "" ? null : identity.grassroots === "yes",
      });
    } catch {
      setVerdictError("判定失败，请稍后重试。");
    } finally {
      setVerdictLoading(false);
    }
  };

  // 登录用户：把当前身份包保存到档案（只传已填字段，exclude_unset 不清空已存值）
  const handleSaveToProfile = async () => {
    setSaveState("saving");
    try {
      const updates: Record<string, string | boolean> = {};
      if (identity.fresh_status) updates.fresh_status = identity.fresh_status;
      if (identity.party_status) updates.party_status = identity.party_status;
      if (identity.education) updates.education = identity.education;
      if (identity.gender) updates.gender = identity.gender;
      if (identity.grassroots !== "") updates.has_grassroots = identity.grassroots === "yes";
      if (Object.keys(updates).length > 0) {
        await authApi.updateMe(updates);
      }
      clearIdentitySnapshot();
      setSaveState("saved");
    } catch {
      setSaveState("error");
    }
  };

  const resetAll = () => {
    setSelected(null);
    setVerdict(null);
    setVerdictError(null);
    setIdentity(EMPTY_IDENTITY);
  };

  const showKaoyan = source === "kaoyan";

  return (
    <div className="rounded-2xl border border-paper-200 bg-white/90 p-5 shadow-sm backdrop-blur sm:p-6">
      {/* 赛道切换 */}
      <div className="flex items-center gap-1.5">
        {SOURCES.map((s) => (
          <button
            key={s.key}
            type="button"
            onClick={() => switchSource(s.key)}
            className={cn(
              "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              source === s.key
                ? "bg-brand-600 text-white"
                : "bg-ink-50 text-ink-600 hover:bg-ink-100",
            )}
          >
            {s.label}
          </button>
        ))}
      </div>
      <p className="mt-2 text-xs text-ink-500">
        {showKaoyan
          ? "搜院校/专业 → 填考研模考估分 → 看复试线档位建议"
          : "搜职位 → 勾选你的身份条件 → 立即看能不能报、卡在哪"}
      </p>

      {/* 职位/院校选择 */}
      {!selected ? (
        <div className="mt-3 relative">
          <div className="flex items-center gap-2 rounded-lg border border-paper-300 bg-white px-3 py-2">
            <Search className="h-4 w-4 text-ink-400 shrink-0" />
            <input
              value={query}
              onChange={(e) => handleQueryChange(e.target.value)}
              placeholder={
                showKaoyan
                  ? "搜索院校或专业（如：清华大学、计算机）"
                  : "搜索职位名称 / 部门 / 专业（如：海关、计算机）"
              }
              className="flex-1 text-sm outline-none bg-transparent text-ink-800 placeholder:text-ink-300"
            />
            {query && (
              <button type="button" onClick={() => handleQueryChange("")} aria-label="清空搜索">
                <X className="h-4 w-4 text-ink-300 hover:text-ink-500" />
              </button>
            )}
          </div>
          {searching && <p className="text-xs text-ink-400 mt-2 px-1">搜索中…</p>}
          {results.length > 0 && (
            <div className="mt-1 max-h-72 overflow-y-auto rounded-lg border border-paper-300 bg-white divide-y divide-ink-50 shadow-sm">
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
                    {p.position_code} | {p.education_req ?? "不限"} | 招{p.recruit_count ?? "?"}人
                  </p>
                </button>
              ))}
            </div>
          )}
          {!searching && query.trim().length >= 2 && results.length === 0 && (
            <p className="text-xs text-ink-400 mt-2 px-1">没有匹配的职位，换个关键词试试</p>
          )}
        </div>
      ) : (
        <div className="mt-3 rounded-lg border border-brand-100 bg-brand-50 px-3 py-2">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="text-sm font-medium text-ink-800 truncate">
                {selected.dept_name} · {selected.position_name}
              </p>
              <p className="text-[11px] text-ink-500 truncate">
                {selected.position_code} | {selected.education_req ?? "不限"} | 招{selected.recruit_count ?? "?"}人
              </p>
            </div>
            <button
              type="button"
              onClick={resetAll}
              className="inline-flex shrink-0 items-center gap-1 text-xs text-ink-400 hover:text-ink-600"
            >
              <RotateCcw className="h-3 w-3" /> 换一个
            </button>
          </div>
        </div>
      )}

      {/* 身份字段表单 */}
      {selected && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {!showKaoyan && (
              <>
                <Field label="应届状态">
                  <SelectField
                    value={identity.fresh_status}
                    onChange={(v) => setIdentityField("fresh_status", v)}
                    options={FRESH_STATUSES}
                  />
                </Field>
                <Field label="政治面貌">
                  <SelectField
                    value={identity.party_status}
                    onChange={(v) => setIdentityField("party_status", v)}
                    options={PARTY_STATUSES}
                  />
                </Field>
                <Field label="最高学历">
                  <SelectField
                    value={identity.education}
                    onChange={(v) => setIdentityField("education", v)}
                    options={EDUCATIONS}
                  />
                </Field>
                <Field label="性别">
                  <SelectField
                    value={identity.gender}
                    onChange={(v) => setIdentityField("gender", v)}
                    options={GENDERS}
                  />
                </Field>
                <Field label="基层工作经历">
                  <SelectField
                    value={identity.grassroots}
                    onChange={(v) => setIdentityField("grassroots", v)}
                    options={GRASSROOTS}
                  />
                </Field>
              </>
            )}
            {showKaoyan && (
              <Field label="考研模考估分（初试 500 分制）">
                <input
                  type="number"
                  min={0}
                  max={500}
                  value={identity.kaoyan_estimated_score}
                  onChange={(e) => setIdentityField("kaoyan_estimated_score", e.target.value)}
                  placeholder="如 345"
                  className="w-full rounded-lg border border-paper-300 bg-white px-2.5 py-2 text-sm text-ink-800 outline-none focus:border-brand-400"
                />
              </Field>
            )}
          </div>

          <button
            type="button"
            onClick={runPreview}
            disabled={verdictLoading}
            className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60 sm:w-auto"
          >
            <Play className="h-4 w-4" />
            {verdictLoading ? "判定中…" : showKaoyan ? "查看报考档位" : "立即判定能否报考"}
          </button>

          {/* 判定结果卡 */}
          {verdict && (
            <div className="mt-4 rounded-xl border border-paper-300 bg-white p-4">
              {showKaoyan ? (
                <KaoyanVerdict verdict={verdict} />
              ) : (
                <EligibilityVerdict verdict={verdict} />
              )}
              <div className="mt-3 border-t border-paper-100 pt-3">
                {loggedIn ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={handleSaveToProfile}
                      disabled={saveState === "saving" || saveState === "saved"}
                      className="text-xs font-medium text-brand-600 hover:text-brand-700 disabled:opacity-60"
                    >
                      {saveState === "saved"
                        ? "✓ 已保存到我的档案"
                        : saveState === "saving"
                          ? "保存中…"
                          : "保存这份身份到我的档案 →"}
                    </button>
                    <Link
                      href="/decision-engine"
                      className="text-xs text-ink-400 hover:text-ink-600"
                    >
                      去生成完整报考决策报告 →
                    </Link>
                  </div>
                ) : (
                  <Link
                    href="/register"
                    className="text-xs font-medium text-brand-600 hover:text-brand-700"
                  >
                    登录保存这份判定，并解锁完整条件账本 →
                  </Link>
                )}
                {saveState === "error" && (
                  <p className="mt-1 text-xs text-rose-600">保存失败，请稍后重试。</p>
                )}
              </div>
            </div>
          )}
          {verdictError && (
            <p className="mt-3 text-xs text-rose-600">{verdictError}</p>
          )}
        </>
      )}
    </div>
  );
}

function EligibilityVerdict({ verdict }: { verdict: ConditionPreviewResponse }) {
  const eligible = verdict.eligible;
  return (
    <>
      <div
        className={cn(
          "rounded-lg px-3 py-2 text-sm font-medium border",
          eligible
            ? "bg-emerald-50 text-emerald-700 border-emerald-100"
            : "bg-rose-50 text-rose-700 border-rose-100",
        )}
      >
        {eligible ? "✓ 你的条件可以报考" : "✕ 该职位暂不可报"}
      </div>
      <p className="mt-2 text-xs text-ink-600 leading-relaxed">{verdict.verdict_text}</p>
      {verdict.blockers.length > 0 && (
        <ul className="mt-2 space-y-1.5">
          {verdict.blockers.map((b) => (
            <li key={b.key} className="flex gap-2 text-xs text-ink-700">
              <span className="shrink-0 rounded bg-rose-50 text-rose-500 border border-rose-100 px-1.5 py-0.5 text-[11px] font-medium">
                {b.label}
              </span>
              <span className="leading-relaxed">{b.reason}</span>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function KaoyanVerdict({ verdict }: { verdict: ConditionPreviewResponse }) {
  const level = verdict.level;
  const levelStyle: Record<string, string> = {
    稳健: "bg-emerald-50 text-emerald-700 border-emerald-100",
    均衡: "bg-amber-50 text-amber-700 border-amber-100",
    冲刺: "bg-rose-50 text-rose-700 border-rose-100",
  };
  return (
    <>
      <div className="flex items-center gap-2">
        <Crosshair className="h-4 w-4 text-brand-600" />
        <p className="text-sm font-semibold text-ink-800 truncate">
          {verdict.university_name} · {verdict.major_name}
        </p>
      </div>
      {level ? (
        <>
          <div
            className={cn(
              "mt-2 inline-block rounded-lg border px-3 py-1.5 text-sm font-medium",
              levelStyle[level] ?? "bg-ink-50 text-ink-600 border-ink-100",
            )}
          >
            报考档位：{level}
          </div>
          <p className="mt-2 text-xs text-ink-600 leading-relaxed">{verdict.verdict_text}</p>
          {verdict.score_lines && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {Object.entries(verdict.score_lines).map(([k, v]) => (
                <span key={k} className="rounded bg-ink-50 px-1.5 py-0.5 text-[11px] text-ink-500">
                  {k}: {v}
                </span>
              ))}
            </div>
          )}
        </>
      ) : (
        <p className="mt-2 text-xs text-ink-600 leading-relaxed">{verdict.verdict_text}</p>
      )}
    </>
  );
}
