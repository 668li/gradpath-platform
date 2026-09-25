"use client";

// Decision OS 工作台（D9 垂直切片）。
// 纪律：010 观察期内本页不接入导航，仅直连 URL /decision-os 可达；
// AI 只拆解不决定（确认创建由用户点击）；证据创建即"内部未验证"。

import { useEffect, useState } from "react";
import {
  decisionOsApi,
  type DecisionCard,
  type StructuredDraft,
  type HypothesisImportance,
  type EvidenceStance,
  type HypothesisStatus,
  type ActionResultStance,
  type OutcomeKind,
  type MatchStatus,
  type ProviderInfo,
  type EvidenceCandidate,
} from "@/lib/api/decisionOs";

const IMPORTANCE_LABEL: Record<HypothesisImportance, string> = {
  critical: "致命",
  high: "重要",
  supporting: "次要",
};
const HYP_STATUS_LABEL: Record<HypothesisStatus, string> = {
  untested: "未验证",
  supporting: "有支持",
  refuted: "已证伪",
  obsolete: "已失效",
};
const STANCE_LABEL: Record<EvidenceStance, string> = {
  supporting: "支持",
  contradicting: "反对",
  neutral: "中立",
};
const VERIFICATION_LABEL: Record<string, string> = {
  internal_unverified: "内部未验证",
  externally_verified: "外部已验证",
  contradicted: "来源冲突",
  stale: "已过期",
  unverifiable: "无法验证",
};
const OUTCOME_KIND_LABEL: Record<OutcomeKind, string> = {
  direct: "直接可见",
  partial: "部分可见",
  unobservable: "不可观测",
  counterfactual_unknown: "反事实未知",
};
const MATCH_LABEL: Record<MatchStatus, string> = {
  matched: "符合预期",
  partial: "部分符合",
  missed: "偏离预期",
  unknown: "未判定",
};
const DESTINATION_TYPES = [
  "postgrad",
  "civil_service",
  "employment",
  "abroad",
  "phd",
  "startup",
  "gap_year",
];

const inputCls =
  "w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none";
const btnCls =
  "rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50";
const btnGhostCls =
  "rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50";
const cardCls = "rounded-xl border border-gray-200 bg-white p-5 shadow-sm";
const labelCls = "mb-1 block text-xs font-medium text-gray-500";

export default function DecisionOsPage() {
  const [rawText, setRawText] = useState("");
  const [draft, setDraft] = useState<StructuredDraft | null>(null);
  const [destType, setDestType] = useState("postgrad");
  const [card, setCard] = useState<DecisionCard | null>(null);
  const [openId, setOpenId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "请求失败");
    } finally {
      setBusy(false);
    }
  }

  const structure = () =>
    run(async () => {
      setDraft(await decisionOsApi.structure(rawText));
    });

  const confirmDraft = () =>
    run(async () => {
      if (!draft) return;
      const c = await decisionOsApi.confirmDraft(draft, destType);
      setCard(c);
      setOpenId(c.decision.id);
      setDraft(null);
    });

  const loadCard = () =>
    run(async () => {
      const c = await decisionOsApi.card(openId.trim());
      setCard(c);
    });

  // 深链：/decision-os?decision=<id>（dashboard 当前决策卡等入口直接带 id 进来）
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("decision");
    if (!id) return;
    setOpenId(id);
    run(async () => {
      try {
        setCard(await decisionOsApi.card(id));
      } catch {
        /* 深链失效时保持空态，由用户手动输入 */
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <header>
        <h1 className="text-xl font-bold">决策 OS</h1>
        <p className="mt-1 text-sm text-gray-500">
          把重大决策变成可验证的系统：决策 → 关键假设 → 证据 → 验证行动 → 结果 → 复盘。
          系统不替你决定，只帮你把不确定性一个个消掉。
        </p>
      </header>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* 第一步：自然语言 → 结构化草稿 */}
      <section className={cardCls}>
        <h2 className="text-base font-semibold">1 · 你现在在纠结什么决定？</h2>
        <textarea
          className={`${inputCls} mt-3 h-24`}
          placeholder="用一段话描述，例如：我不知道大学毕业后应该考研还是直接工作，家里希望我考公，但我担心……"
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
        />
        <div className="mt-3 flex items-center gap-3">
          <button className={btnCls} onClick={structure} disabled={busy || rawText.trim().length < 5}>
            AI 拆解成决策卡草稿
          </button>
          <span className="text-xs text-gray-400">AI 只拆解，不替你决定</span>
        </div>

        {draft && (
          <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50/50 p-4">
            {draft.ai_used ? (
              <span className="text-xs text-gray-500">AI 结构化草稿（请核对后确认）</span>
            ) : (
              <span className="text-xs text-amber-600">
                AI 暂不可用，已降级为原文——假设需要你手工补充
              </span>
            )}
            <p className="mt-2 text-sm font-medium">{draft.question}</p>
            {draft.context && <p className="mt-1 text-xs text-gray-500">背景：{draft.context}</p>}
            {draft.options.length > 0 && (
              <p className="mt-1 text-xs text-gray-600">选项：{draft.options.join(" / ")}</p>
            )}
            {draft.constraints.length > 0 && (
              <p className="mt-1 text-xs text-gray-600">约束：{draft.constraints.join("；")}</p>
            )}
            {draft.desired_outcome && (
              <p className="mt-1 text-xs text-gray-600">期望结果：{draft.desired_outcome}</p>
            )}
            <div className="mt-3 space-y-2">
              {draft.hypotheses.map((h, i) => (
                <div key={i} className="rounded-md border border-blue-100 bg-white p-3 text-sm">
                  <span className="mr-2 rounded bg-gray-100 px-1.5 py-0.5 text-xs">
                    假设 {i + 1} · {IMPORTANCE_LABEL[h.importance] ?? h.importance}
                  </span>
                  {h.statement}
                  {h.impact && <div className="mt-1 text-xs text-gray-500">若被证伪：{h.impact}</div>}
                </div>
              ))}
              {draft.hypotheses.length === 0 && (
                <p className="text-xs text-gray-500">（暂无假设，可先创建决策再手工添加）</p>
              )}
            </div>
            {draft.evidence_needs.length > 0 && (
              <p className="mt-2 text-xs text-gray-500">最缺的证据：{draft.evidence_needs.join("；")}</p>
            )}
            <div className="mt-4 flex items-center gap-3">
              <select className={inputCls} value={destType} onChange={(e) => setDestType(e.target.value)}>
                {DESTINATION_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <button className={btnCls} onClick={confirmDraft} disabled={busy}>
                确认，创建决策卡
              </button>
            </div>
          </div>
        )}
      </section>

      {/* 打开已有决策 */}
      <section className={cardCls}>
        <h2 className="text-base font-semibold">2 · 打开已有决策</h2>
        <div className="mt-3 flex gap-3">
          <input
            className={inputCls}
            placeholder="决策 ID（创建成功后自动填入）"
            value={openId}
            onChange={(e) => setOpenId(e.target.value)}
          />
          <button className={btnGhostCls} onClick={loadCard} disabled={busy || !openId.trim()}>
            加载
          </button>
        </div>
      </section>

      {card && <DecisionCardBody card={card} onChanged={loadCard} busy={busy} run={run} />}
    </div>
  );
}

function DecisionCardBody({
  card,
  onChanged,
  busy,
  run,
}: {
  card: DecisionCard;
  onChanged: () => void;
  busy: boolean;
  run: (fn: () => Promise<void>) => void;
}) {
  const d = card.decision;
  const [evForm, setEvForm] = useState<Record<string, { claim: string; stance: EvidenceStance }>>({});
  const [actionTitle, setActionTitle] = useState("");
  const [actionHyp, setActionHyp] = useState("");
  const [doneActionId, setDoneActionId] = useState<string | null>(null);
  const [doneForm, setDoneForm] = useState<{
    result: string;
    stance: ActionResultStance;
    hyp_update: string;
  }>({ result: "", stance: "hypothesis_supported", hyp_update: "" });
  const [outcomeForm, setOutcomeForm] = useState<{ kind: OutcomeKind; summary: string }>({
    kind: "direct",
    summary: "",
  });
  const [reflectForm, setReflectForm] = useState<{
    lesson: string;
    wrong_assumption: string;
    match_status: MatchStatus;
    new_principle: string;
  }>({ lesson: "", wrong_assumption: "", match_status: "unknown", new_principle: "" });

  // Provider Router（白名单内部库候选证据）
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [provOpen, setProvOpen] = useState<string | null>(null);
  const [provSel, setProvSel] = useState("grad_scoreline");
  const [provQuery, setProvQuery] = useState("");
  const [provResults, setProvResults] = useState<EvidenceCandidate[]>([]);

  // 外部验证
  const [verifyUrl, setVerifyUrl] = useState<Record<string, string>>({});
  const [verifyMsg, setVerifyMsg] = useState<Record<string, string>>({});

  const openProv = (hypId: string) =>
    run(async () => {
      if (provOpen === hypId) {
        setProvOpen(null);
        return;
      }
      setProvOpen(hypId);
      setProvResults([]);
      setProviders(await decisionOsApi.listProviders(hypId));
    });

  const searchProv = (hypId: string) =>
    run(async () => {
      setProvResults(await decisionOsApi.searchProvider(hypId, provSel, provQuery));
    });

  const recordCandidate = (hypId: string, c: EvidenceCandidate) =>
    run(async () => {
      await decisionOsApi.addHypothesisEvidence(hypId, {
        claim: c.claim,
        stance: "neutral",
        provider: c.provider,
        source_url: c.source_url ?? undefined,
      });
      onChanged();
    });

  const doVerify = (evId: string) =>
    run(async () => {
      const r = await decisionOsApi.externalVerify(evId, verifyUrl[evId]);
      const verdictText =
        r.verdict === "agree"
          ? "外部来源支持"
          : r.verdict === "contradict"
            ? "外部来源反对（已另立一条外部证据，原证据留痕）"
            : r.verdict === "stale"
              ? "外部信息已过时"
              : "来源与此证据无关，状态未动";
      setVerifyMsg({ ...verifyMsg, [evId]: `核查结论：${verdictText}——${r.summary}` });
      onChanged();
    });

  return (
    <section className={cardCls}>
      <div className="flex items-baseline justify-between">
        <h2 className="text-base font-semibold">{d.question ?? "（未命名决策）"}</h2>
        <span className="text-xs text-gray-400">
          {d.destination_type} · {d.status} · 置信 {d.confidence}/5
        </span>
      </div>
      {d.options.length > 0 && <p className="mt-1 text-sm text-gray-600">选项：{d.options.join(" / ")}</p>}
      {d.constraints.length > 0 && (
        <p className="mt-1 text-xs text-gray-500">约束：{d.constraints.join("；")}</p>
      )}

      {/* 关键假设 */}
      <h3 className="mt-5 text-sm font-semibold">关键假设（未验证 = 决策还没落地）</h3>
      <div className="mt-2 space-y-3">
        {card.hypotheses.map((h) => (
          <div key={h.id} className="rounded-lg border border-gray-200 p-3">
            <div className="flex items-baseline justify-between gap-2">
              <p className="text-sm">{h.statement}</p>
              <span className="shrink-0 text-xs text-gray-400">
                {IMPORTANCE_LABEL[h.importance]} · {HYP_STATUS_LABEL[h.status]}
              </span>
            </div>
            {h.impact && <p className="mt-1 text-xs text-gray-500">若被证伪：{h.impact}</p>}
            <div className="mt-2 flex gap-3 text-xs">
              <span className="text-green-700">支持 {h.supporting}</span>
              <span className="text-red-700">反对 {h.contradicting}</span>
              <span className="text-gray-500">中立 {h.neutral}</span>
            </div>

            {/* 挂证据 */}
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <input
                className="w-56 rounded border border-gray-200 px-2 py-1 text-xs"
                placeholder="新证据：一条具体的 claim"
                value={evForm[h.id]?.claim ?? ""}
                onChange={(e) =>
                  setEvForm({ ...evForm, [h.id]: { claim: e.target.value, stance: evForm[h.id]?.stance ?? "supporting" } })
                }
              />
              <select
                className="rounded border border-gray-200 px-1 py-1 text-xs"
                value={evForm[h.id]?.stance ?? "supporting"}
                onChange={(e) =>
                  setEvForm({
                    ...evForm,
                    [h.id]: { claim: evForm[h.id]?.claim ?? "", stance: e.target.value as EvidenceStance },
                  })
                }
              >
                <option value="supporting">支持</option>
                <option value="contradicting">反对</option>
                <option value="neutral">中立</option>
              </select>
              <button
                className={btnGhostCls}
                disabled={busy || !evForm[h.id]?.claim}
                onClick={() =>
                  run(async () => {
                    await decisionOsApi.addHypothesisEvidence(h.id, {
                      claim: evForm[h.id].claim,
                      stance: evForm[h.id].stance,
                    });
                    setEvForm({ ...evForm, [h.id]: { claim: "", stance: "supporting" } });
                    onChanged();
                  })
                }
              >
                记为证据（默认"内部未验证"）
              </button>
              <button className={btnGhostCls} onClick={() => openProv(h.id)}>
                从站内库找证据
              </button>
            </div>
            {provOpen === h.id && (
              <div className="mt-2 space-y-2 rounded-md bg-gray-50 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    className="rounded border border-gray-200 px-1 py-1 text-xs"
                    value={provSel}
                    onChange={(e) => setProvSel(e.target.value)}
                  >
                    {providers.map((p) => (
                      <option key={p.name} value={p.name}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                  <input
                    className="w-56 rounded border border-gray-200 px-2 py-1 text-xs"
                    placeholder="检索词：学校/专业/岗位/指标"
                    value={provQuery}
                    onChange={(e) => setProvQuery(e.target.value)}
                  />
                  <button
                    className={btnGhostCls}
                    disabled={busy || !provQuery.trim()}
                    onClick={() => searchProv(h.id)}
                  >
                    搜索候选
                  </button>
                </div>
                {provResults.map((c, i) => (
                  <div key={i} className="rounded border border-gray-100 bg-white p-2 text-xs">
                    <p className="text-gray-700">{c.claim}</p>
                    <p className="mt-0.5 text-gray-400">
                      {c.provider} · 可靠性 {c.reliability}
                      {c.source_url && (
                        <a
                          href={c.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="ml-1 text-blue-500"
                        >
                          查看来源
                        </a>
                      )}
                    </p>
                    <button
                      className={`${btnGhostCls} mt-1`}
                      disabled={busy}
                      onClick={() => recordCandidate(h.id, c)}
                    >
                      记为证据（入账仍标"内部未验证"）
                    </button>
                  </div>
                ))}
                {provResults.length === 0 && (
                  <p className="text-xs text-gray-400">（无候选——换个检索词，或用下方外部核查）</p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 证据清单 */}
      {card.evidence.length > 0 && (
        <>
          <h3 className="mt-5 text-sm font-semibold">证据清单（库里有 ≠ 已验证）</h3>
          <ul className="mt-2 space-y-1 text-xs text-gray-600">
            {card.evidence.map((ev) => (
              <li key={ev.id} className="rounded border border-gray-100 px-2 py-1">
                <span
                  className={`mr-2 rounded px-1.5 py-0.5 ${
                    ev.verification_status === "externally_verified"
                      ? "bg-green-100 text-green-700"
                      : ev.verification_status === "contradicted"
                        ? "bg-red-100 text-red-700"
                        : "bg-gray-100"
                  }`}
                >
                  {VERIFICATION_LABEL[ev.verification_status] ?? ev.verification_status}
                </span>
                {STANCE_LABEL[ev.stance]} · {ev.claim}
                {ev.provider && <span className="ml-1 text-gray-400">[{ev.provider}]</span>}
                {ev.verification_status === "internal_unverified" && (
                  <span className="mt-1 flex items-center gap-1">
                    <input
                      className="w-56 rounded border border-gray-200 px-1.5 py-0.5"
                      placeholder="外部来源 URL（官方页/新闻）"
                      value={verifyUrl[ev.id] ?? ""}
                      onChange={(e) => setVerifyUrl({ ...verifyUrl, [ev.id]: e.target.value })}
                    />
                    <button
                      className={btnGhostCls}
                      disabled={busy || !verifyUrl[ev.id]}
                      onClick={() => doVerify(ev.id)}
                    >
                      外部核查
                    </button>
                  </span>
                )}
                {verifyMsg[ev.id] && <p className="mt-1 text-gray-500">{verifyMsg[ev.id]}</p>}
              </li>
            ))}
          </ul>
        </>
      )}

      {/* 验证行动 */}
      <h3 className="mt-5 text-sm font-semibold">下一步最小验证行动</h3>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <input
          className="w-72 rounded border border-gray-200 px-2 py-1 text-sm"
          placeholder="例如：采访 3 名跨考上岸学生"
          value={actionTitle}
          onChange={(e) => setActionTitle(e.target.value)}
        />
        <select
          className="rounded border border-gray-200 px-1 py-1 text-xs"
          value={actionHyp}
          onChange={(e) => setActionHyp(e.target.value)}
        >
          <option value="">（可选）挂到假设</option>
          {card.hypotheses.map((h) => (
            <option key={h.id} value={h.id}>
              {h.statement.slice(0, 24)}…
            </option>
          ))}
        </select>
        <button
          className={btnGhostCls}
          disabled={busy || !actionTitle.trim()}
          onClick={() =>
            run(async () => {
              await decisionOsApi.addAction(d.id, {
                title: actionTitle,
                hypothesis_id: actionHyp || null,
              });
              setActionTitle("");
              onChanged();
            })
          }
        >
          添加行动
        </button>
      </div>
      <ul className="mt-2 space-y-2">
        {card.actions.map((a) => (
          <li key={a.id} className="rounded-lg border border-gray-200 p-3 text-sm">
            <div className="flex items-baseline justify-between">
              <span>{a.title}</span>
              <span className="text-xs text-gray-400">
                {a.status === "done" ? `已完成 · ${a.result_stance ?? ""}` : a.status}
              </span>
            </div>
            {a.status !== "done" && (
              <button className={`${btnGhostCls} mt-2`} onClick={() => setDoneActionId(a.id)}>
                记录结果
              </button>
            )}
            {a.result && <p className="mt-1 text-xs text-gray-600">结果：{a.result}</p>}
            {doneActionId === a.id && (
              <div className="mt-2 space-y-2 rounded-md bg-gray-50 p-3">
                <input
                  className={inputCls}
                  placeholder="实际发生了什么？"
                  value={doneForm.result}
                  onChange={(e) => setDoneForm({ ...doneForm, result: e.target.value })}
                />
                <select
                  className={inputCls}
                  value={doneForm.stance}
                  onChange={(e) => setDoneForm({ ...doneForm, stance: e.target.value as ActionResultStance })}
                >
                  <option value="hypothesis_supported">结果支持假设</option>
                  <option value="hypothesis_weakened">结果削弱假设</option>
                  <option value="inconclusive">说不上</option>
                </select>
                <select
                  className={inputCls}
                  value={doneForm.hyp_update}
                  onChange={(e) => setDoneForm({ ...doneForm, hyp_update: e.target.value })}
                >
                  <option value="">不改假设状态（我还没想好）</option>
                  {card.hypotheses
                    .filter((h) => h.id === a.hypothesis_id)
                    .map((h) => (
                      <option key={h.id} value="supporting">
                        把假设标为「有支持」
                      </option>
                    ))}
                  {card.hypotheses
                    .filter((h) => h.id === a.hypothesis_id)
                    .map((h) => (
                      <option key={h.id} value="refuted">
                        把假设标为「已证伪」
                      </option>
                    ))}
                </select>
                <button
                  className={btnCls}
                  disabled={busy || !doneForm.result}
                  onClick={() =>
                    run(async () => {
                      await decisionOsApi.completeAction(a.id, {
                        result: doneForm.result,
                        result_stance: doneForm.stance,
                        hypothesis_status_update: doneForm.hyp_update
                          ? (doneForm.hyp_update as HypothesisStatus)
                          : null,
                      });
                      setDoneActionId(null);
                      setDoneForm({ result: "", stance: "hypothesis_supported", hyp_update: "" });
                      onChanged();
                    })
                  }
                >
                  完成并记录
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>

      {/* 结果与复盘 */}
      <h3 className="mt-5 text-sm font-semibold">真实结果</h3>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <select
          className="rounded border border-gray-200 px-1 py-1 text-xs"
          value={outcomeForm.kind}
          onChange={(e) => setOutcomeForm({ ...outcomeForm, kind: e.target.value as OutcomeKind })}
        >
          <option value="direct">直接可见</option>
          <option value="partial">部分可见</option>
          <option value="unobservable">不可观测</option>
          <option value="counterfactual_unknown">反事实未知</option>
        </select>
        <input
          className="w-72 rounded border border-gray-200 px-2 py-1 text-sm"
          placeholder="发生了什么？"
          value={outcomeForm.summary}
          onChange={(e) => setOutcomeForm({ ...outcomeForm, summary: e.target.value })}
        />
        <button
          className={btnGhostCls}
          disabled={busy || !outcomeForm.summary.trim()}
          onClick={() =>
            run(async () => {
              await decisionOsApi.addOutcome(d.id, outcomeForm);
              setOutcomeForm({ kind: "direct", summary: "" });
              onChanged();
            })
          }
        >
          记录结果
        </button>
      </div>
      {card.outcomes.map((o) => (
        <p key={o.id} className="mt-1 text-xs text-gray-600">
          [{OUTCOME_KIND_LABEL[o.kind]}] {o.summary}
        </p>
      ))}

      <h3 className="mt-5 text-sm font-semibold">复盘</h3>
      <div className="mt-2 space-y-2">
        <input
          className={inputCls}
          placeholder="哪个假设错了？"
          value={reflectForm.wrong_assumption}
          onChange={(e) => setReflectForm({ ...reflectForm, wrong_assumption: e.target.value })}
        />
        <input
          className={inputCls}
          placeholder="学到了什么（教训）？"
          value={reflectForm.lesson}
          onChange={(e) => setReflectForm({ ...reflectForm, lesson: e.target.value })}
        />
        <input
          className={inputCls}
          placeholder="沉淀成的新原则（可选，如「先做一套真题再立假设」）"
          value={reflectForm.new_principle}
          onChange={(e) => setReflectForm({ ...reflectForm, new_principle: e.target.value })}
        />
        <div className="flex items-center gap-2">
          <select
            className="rounded border border-gray-200 px-1 py-1 text-xs"
            value={reflectForm.match_status}
            onChange={(e) => setReflectForm({ ...reflectForm, match_status: e.target.value as MatchStatus })}
          >
            <option value="unknown">未判定</option>
            <option value="matched">符合预期</option>
            <option value="partial">部分符合</option>
            <option value="missed">偏离预期</option>
          </select>
          <button
            className={btnGhostCls}
            disabled={
              busy ||
              (!reflectForm.lesson.trim() &&
                !reflectForm.wrong_assumption.trim() &&
                !reflectForm.new_principle.trim())
            }
            onClick={() =>
              run(async () => {
                await decisionOsApi.addReflection(d.id, reflectForm);
                setReflectForm({ lesson: "", wrong_assumption: "", match_status: "unknown", new_principle: "" });
                onChanged();
              })
            }
          >
            写入复盘
          </button>
        </div>
      </div>
      {card.reflections.map((r) => (
        <div key={r.id} className="mt-2 rounded-md bg-amber-50 p-3 text-xs text-gray-700">
          [{MATCH_LABEL[r.match_status]}]
          {r.wrong_assumption && <div>错在：{r.wrong_assumption}</div>}
          {r.lesson && <div>教训：{r.lesson}</div>}
          {r.new_principle && <div>新原则：{r.new_principle}</div>}
        </div>
      ))}
    </section>
  );
}
