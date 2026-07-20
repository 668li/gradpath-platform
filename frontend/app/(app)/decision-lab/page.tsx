"use client";

import { useCallback, useEffect, useState } from "react";
import { Scale, Sparkles, AlertTriangle, Shield, Swords, Plus, Trash2, Trophy, ChevronDown, ChevronRight } from "lucide-react";
import { decisionAnalysisApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button, Input, Textarea, Field } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type { DecisionAnalysisResponse, Criterion } from "@/types";

type Step = "setup" | "premortem" | "matrix" | "redteam" | "summary";

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

export default function DecisionLabPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [analyses, setAnalyses] = useState<DecisionAnalysisResponse[]>([]);
  const [selectedAnalysis, setSelectedAnalysis] = useState<DecisionAnalysisResponse | null>(null);
  const [showNew, setShowNew] = useState(false);

  // 新建分析表单
  const [title, setTitle] = useState("");
  const [options, setOptions] = useState<string[]>(["", ""]);
  const [step, setStep] = useState<Step>("setup");

  // 预验尸
  const [premortemReasons, setPremortemReasons] = useState<string[]>([""]);
  const [premortemResult, setPremortemResult] = useState<{ categories: { category: string; reasons: string[] }[]; safeguards: { category: string; action: string }[] } | null>(null);
  const [premortemLoading, setPremortemLoading] = useState(false);

  // 决策矩阵
  const [criteria, setCriteria] = useState<Criterion[]>([{ criterion: "", weight: 30 }]);
  const [matrixScores, setMatrixScores] = useState<Record<string, number>[]>([]);
  const [matrixResult, setMatrixResult] = useState<{ results: { name: string; total: number; details: Record<string, number> }[]; winner: string } | null>(null);
  const [matrixLoading, setMatrixLoading] = useState(false);

  // 红队
  const [redTeamQuestions, setRedTeamQuestions] = useState<string[]>([]);
  const [redTeamAnswers, setRedTeamAnswers] = useState<Record<number, string>>({});
  const [redTeamLoading, setRedTeamLoading] = useState(false);

  // AI 综合分析
  const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [savedAnalysisId, setSavedAnalysisId] = useState<string | null>(null);

  const loadAnalyses = useCallback(async () => {
    setLoading(true);
    try {
      const list = await decisionAnalysisApi.list();
      setAnalyses(list);
    } catch {
      toast.push("加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadAnalyses();
  }, [loadAnalyses]);

  // 初始化矩阵评分
  useEffect(() => {
    if (options.filter(o => o.trim()).length >= 2 && matrixScores.length === 0) {
      setMatrixScores(options.map(() => ({})));
    }
  }, [options, matrixScores.length]);

  const resetForm = () => {
    setTitle("");
    setOptions(["", ""]);
    setPremortemReasons([""]);
    setPremortemResult(null);
    setCriteria([{ criterion: "", weight: 30 }]);
    setMatrixScores([]);
    setMatrixResult(null);
    setRedTeamQuestions([]);
    setRedTeamAnswers({});
    setAiAnalysis(null);
    setSavedAnalysisId(null);
    setStep("setup");
  };

  // 预验尸分析
  const handlePremortem = async () => {
    const validReasons = premortemReasons.filter(r => r.trim());
    if (validReasons.length < 3) {
      toast.push("请至少列出 3 个可能的失败原因", "error");
      return;
    }
    setPremortemLoading(true);
    try {
      const result = await decisionAnalysisApi.analyzePremortem({
        title,
        options: options.filter(o => o.trim()),
        premortem_reasons: validReasons,
      });
      setPremortemResult(result);
    } catch {
      toast.push("AI 分析失败，请重试", "error");
    } finally {
      setPremortemLoading(false);
    }
  };

  // 计算矩阵
  const handleComputeMatrix = async () => {
    const validCriteria = criteria.filter(c => c.criterion.trim() && c.weight > 0);
    if (validCriteria.length === 0) {
      toast.push("请至少添加一个评估标准", "error");
      return;
    }
    const totalWeight = validCriteria.reduce((sum, c) => sum + c.weight, 0);
    if (totalWeight !== 100) {
      toast.push(`权重总和需要等于 100，当前为 ${totalWeight}`, "error");
      return;
    }
    const validOptions = options.filter(o => o.trim());
    if (validOptions.length < 2) {
      toast.push("请至少填写 2 个选项", "error");
      return;
    }
    setMatrixLoading(true);
    try {
      const result = await decisionAnalysisApi.computeMatrix({
        criteria: validCriteria,
        matrix_scores: validOptions.map((name, i) => ({
          name,
          scores: matrixScores[i] || {},
        })),
      });
      setMatrixResult(result);
    } catch {
      toast.push("矩阵计算失败", "error");
    } finally {
      setMatrixLoading(false);
    }
  };

  // 生成红队问题
  const handleRedTeam = async () => {
    setRedTeamLoading(true);
    try {
      const result = await decisionAnalysisApi.generateRedTeamQuestions({
        title,
        options: options.filter(o => o.trim()),
      });
      setRedTeamQuestions(result.questions);
      setRedTeamAnswers({});
    } catch {
      toast.push("生成红队问题失败", "error");
    } finally {
      setRedTeamLoading(false);
    }
  };

  // 保存并 AI 分析
  const handleSaveAndAnalyze = async () => {
    setAiLoading(true);
    try {
      const validCriteria = criteria.filter(c => c.criterion.trim());
      const validOptions = options.filter(o => o.trim());
      const validReasons = premortemReasons.filter(r => r.trim());

      const analysis = await decisionAnalysisApi.create({
        title,
        options: validOptions,
        premortem_reasons: validReasons.map(r => ({ reason: r, category: "" })),
        premortem_categories: premortemResult?.categories.map(c => c.category) || [],
        safeguards: premortemResult?.safeguards || [],
        criteria: validCriteria,
        matrix_scores: validOptions.map((name, i) => ({
          name,
          scores: matrixScores[i] || {},
        })),
        red_team_questions: redTeamQuestions,
        red_team_answers: Object.values(redTeamAnswers),
      });
      setSavedAnalysisId(analysis.id);
      const aiRes = await decisionAnalysisApi.generateAiAnalysis(analysis.id);
      setAiAnalysis(aiRes.ai_analysis);
      toast.push("分析已保存！", "success");
      loadAnalyses();
    } catch {
      toast.push("保存失败，请重试", "error");
    } finally {
      setAiLoading(false);
    }
  };

  if (loading) return <LoadingState />;

  // ====== 查看已有分析 ======
  if (selectedAnalysis) {
    return <AnalysisDetail analysis={selectedAnalysis} onBack={() => setSelectedAnalysis(null)} />;
  }

  // ====== 新建分析流程 ======
  if (showNew) {
    const validOptions = options.filter(o => o.trim());

    return (
      <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
        {/* 步骤指示器 */}
        <div className="flex items-center gap-1 text-xs">
          {([
            { key: "setup", label: "基本信息" },
            { key: "premortem", label: "预验尸" },
            { key: "matrix", label: "决策矩阵" },
            { key: "redteam", label: "红队质疑" },
            { key: "summary", label: "综合分析" },
          ] as { key: Step; label: string }[]).map((s, i, arr) => {
            const active = step === s.key;
            const passed = arr.findIndex(a => a.key === step) > i;
            return (
              <div key={s.key} className="flex items-center">
                <button
                  onClick={() => {
                    if (i === 0 || (title && validOptions.length >= 2)) setStep(s.key);
                  }}
                  className={cn(
                    "inline-flex items-center gap-1 rounded-full px-2.5 py-1 font-medium transition-all",
                    active ? "bg-brand-600 text-white" : passed ? "bg-brand-100 text-brand-700" : "bg-paper-200 text-ink-400",
                  )}
                >
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-white/30 text-[10px]">{i + 1}</span>
                  {s.label}
                </button>
                {i < arr.length - 1 && <span className="mx-0.5 text-ink-300">→</span>}
              </div>
            );
          })}
        </div>

        {/* Step 1: 基本信息 */}
        {step === "setup" && (
          <div className="card space-y-5">
            <div className="flex items-center gap-2">
              <Scale className="h-5 w-5 text-brand-600" />
              <h1 className="font-display text-lg font-semibold text-ink-800">新建决策分析</h1>
            </div>
            <Field label="决策标题" required>
              <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="例如：应该去大厂还是创业公司？" data-testid="decision-title-input" />
            </Field>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-ink-700">备选项 <span className="text-red-500">*</span></span>
                <button onClick={() => setOptions(prev => [...prev, ""])} className="text-xs text-brand-600 font-medium">
                  <Plus className="inline h-3.5 w-3.5" /> 添加选项
                </button>
              </div>
              {options.map((opt, i) => (
                <div key={`opt-${i}`} className="flex items-center gap-2">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-medium text-brand-700">
                    {String.fromCharCode(65 + i)}
                  </span>
                  <Input
                    value={opt}
                    onChange={e => setOptions(prev => prev.map((o, idx) => idx === i ? e.target.value : o))}
                    placeholder={`选项 ${String.fromCharCode(65 + i)}`}
                    data-testid={`option-${String.fromCharCode(65 + i).toLowerCase()}-input`}
                    className="flex-1"
                  />
                  {options.length > 2 && (
                    <button onClick={() => setOptions(prev => prev.filter((_, idx) => idx !== i))} className="text-ink-300 hover:text-red-500">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <div className="flex justify-end">
              <Button
                onClick={() => {
                  if (!title.trim()) { toast.push("请填写决策标题", "error"); return; }
                  if (validOptions.length < 2) { toast.push("请至少填写 2 个选项", "error"); return; }
                  setStep("premortem");
                }}
                data-testid="decision-next-button"
              >
                下一步：预验尸
              </Button>
            </div>
          </div>
        )}

        {/* Step 2: 预验尸 */}
        {step === "premortem" && (
          <div className="card space-y-5">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              <h2 className="font-display text-lg font-semibold text-ink-800">预验尸分析</h2>
            </div>
            <p className="text-sm text-ink-500 leading-relaxed">
              想象 6 个月后这个决策彻底失败了。列出所有可能导致失败的原因。
              AI 将帮你把原因聚类，并生成对应的保障措施。
            </p>
            <div className="space-y-2">
              {premortemReasons.map((reason, i) => (
                <div key={`reason-${i}`} className="flex items-center gap-2">
                  <span className="text-xs text-ink-400 shrink-0 w-6">{i + 1}.</span>
                  <Input
                    value={reason}
                    onChange={e => setPremortemReasons(prev => prev.map((r, idx) => idx === i ? e.target.value : r))}
                    placeholder="例如：市场突然变化导致需求消失"
                    className="flex-1"
                  />
                  {premortemReasons.length > 1 && (
                    <button onClick={() => setPremortemReasons(prev => prev.filter((_, idx) => idx !== i))} className="text-ink-300 hover:text-red-500">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
              <button onClick={() => setPremortemReasons(prev => [...prev, ""])} className="text-xs text-brand-600 font-medium">
                <Plus className="inline h-3.5 w-3.5" /> 添加原因
              </button>
            </div>
            <Button onClick={handlePremortem} loading={premortemLoading} variant="secondary" className="w-full">
              <Sparkles className="h-4 w-4" /> AI 分析风险
            </Button>

            {premortemResult && (
              <div className="space-y-4 rounded-lg border border-paper-200 bg-paper-50 p-4">
                <div>
                  <p className="text-sm font-medium text-ink-700 mb-2">风险聚类</p>
                  {premortemResult.categories.map((cat, i) => (
                    <div key={`${cat.category}-${i}`} className="mb-2">
                      <span className="inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-600 mb-1">
                        {cat.category}
                      </span>
                      <ul className="ml-4 space-y-0.5">
                        {cat.reasons.map((r, j) => (
                          <li key={j} className="text-xs text-ink-600">• {r}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <Shield className="h-4 w-4 text-brand-600" />
                    <p className="text-sm font-medium text-ink-700">保障措施</p>
                  </div>
                  {premortemResult.safeguards.map((s, i) => (
                    <div key={`${s.category}-${i}`} className="mb-1.5 rounded-md bg-white p-2 border border-paper-200">
                      <span className="text-xs font-medium text-brand-600">{s.category}：</span>
                      <span className="text-xs text-ink-600">{s.action}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setStep("setup")}>上一步</Button>
              <Button onClick={() => setStep("matrix")}>下一步：决策矩阵</Button>
            </div>
          </div>
        )}

        {/* Step 3: 决策矩阵 */}
        {step === "matrix" && (
          <div className="card space-y-5">
            <div className="flex items-center gap-2">
              <Scale className="h-5 w-5 text-brand-600" />
              <h2 className="font-display text-lg font-semibold text-ink-800">决策矩阵</h2>
            </div>
            <p className="text-sm text-ink-500">
              为每个评估标准设定权重（总和 100），然后为每个选项在每个标准上打分（1-10）。
            </p>

            {/* 标准与权重 */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-ink-700">评估标准与权重</span>
                <button onClick={() => setCriteria(prev => [...prev, { criterion: "", weight: 10 }])} className="text-xs text-brand-600 font-medium">
                  <Plus className="inline h-3.5 w-3.5" /> 添加标准
                </button>
              </div>
              {criteria.map((c, i) => (
                <div key={`${c.criterion}-${i}`} className="flex items-center gap-2">
                  <Input
                    value={c.criterion}
                    onChange={e => setCriteria(prev => prev.map((item, idx) => idx === i ? { ...item, criterion: e.target.value } : item))}
                    placeholder="例如：薪资水平"
                    className="flex-1"
                  />
                  <Input
                    type="number"
                    min={1}
                    max={100}
                    value={c.weight}
                    onChange={e => setCriteria(prev => prev.map((item, idx) => idx === i ? { ...item, weight: Number(e.target.value) } : item))}
                    className="w-20"
                  />
                  <span className="text-xs text-ink-400">%</span>
                  {criteria.length > 1 && (
                    <button onClick={() => setCriteria(prev => prev.filter((_, idx) => idx !== i))} className="text-ink-300 hover:text-red-500">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
              <p className="text-xs text-ink-400">
                权重总和：{criteria.reduce((s, c) => s + c.weight, 0)} / 100
              </p>
            </div>

            {/* 评分矩阵 */}
            {criteria.some(c => c.criterion.trim()) && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr>
                      <th className="text-left p-2 text-xs font-medium text-ink-500">选项</th>
                      {criteria.filter(c => c.criterion.trim()).map((c, i) => (
                        <th key={`${c.criterion}-${i}`} className="p-2 text-xs font-medium text-ink-500 text-center min-w-[80px]">
                          {c.criterion}
                          <br />
                          <span className="text-[10px] text-ink-400">权重 {c.weight}%</span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {validOptions.map((opt, optIdx) => (
                      <tr key={optIdx} className="border-t border-paper-200">
                        <td className="p-2 text-sm font-medium text-ink-700">{opt}</td>
                        {criteria.filter(c => c.criterion.trim()).map((c, critIdx) => {
                          const actualCritIdx = criteria.indexOf(c);
                          const score = matrixScores[optIdx]?.[c.criterion] || 0;
                          return (
                            <td key={critIdx} className="p-2 text-center">
                              <input
                                type="number"
                                min={1}
                                max={10}
                                value={score || ""}
                                onChange={e => {
                                  setMatrixScores(prev => {
                                    const next = [...prev];
                                    while (next.length <= optIdx) next.push({});
                                    next[optIdx] = { ...next[optIdx], [c.criterion]: Number(e.target.value) };
                                    return next;
                                  });
                                }}
                                className="w-14 rounded-md border border-paper-300 px-2 py-1 text-center text-sm focus:border-brand-500 focus:outline-none"
                                placeholder="-"
                              />
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <Button onClick={handleComputeMatrix} loading={matrixLoading} variant="secondary" className="w-full">
              <Sparkles className="h-4 w-4" /> 计算加权得分
            </Button>

            {matrixResult && (
              <div className="space-y-3 rounded-lg border border-paper-200 bg-paper-50 p-4">
                {matrixResult.results.map((r, i) => (
                  <div key={r.name} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-ink-700 flex items-center gap-1.5">
                        {r.name === matrixResult.winner && <Trophy className="h-4 w-4 text-amber-500" />}
                        {r.name}
                      </span>
                      <span className={cn("text-sm font-bold", r.name === matrixResult.winner ? "text-brand-600" : "text-ink-500")}>
                        {r.total.toFixed(1)}
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-paper-200">
                      <div
                        className={cn("h-full rounded-full", r.name === matrixResult.winner ? "bg-brand-500" : "bg-ink-300")}
                        style={{ width: `${Math.min(100, (r.total / (matrixResult.results[0]?.total || 1)) * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
                {matrixResult.winner && (
                  <p className="text-center text-sm text-brand-600 font-medium pt-2">
                    <Trophy className="inline h-4 w-4" /> 推荐选项：{matrixResult.winner}
                  </p>
                )}
              </div>
            )}

            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setStep("premortem")}>上一步</Button>
              <Button onClick={() => setStep("redteam")}>下一步：红队质疑</Button>
            </div>
          </div>
        )}

        {/* Step 4: 红队质疑 */}
        {step === "redteam" && (
          <div className="card space-y-5">
            <div className="flex items-center gap-2">
              <Swords className="h-5 w-5 text-red-500" />
              <h2 className="font-display text-lg font-semibold text-ink-800">红队质疑</h2>
            </div>
            <p className="text-sm text-ink-500">
              AI 将生成 7 个尖锐的质疑问题，挑战你的决策假设。认真回答每个问题，让你的决策更健壮。
            </p>

            {redTeamQuestions.length === 0 ? (
              <Button onClick={handleRedTeam} loading={redTeamLoading} variant="secondary" className="w-full">
                <Sparkles className="h-4 w-4" /> 生成红队问题
              </Button>
            ) : (
              <div className="space-y-4">
                {redTeamQuestions.map((q, i) => (
                  <div key={`q-${i}`} className="space-y-1.5">
                    <div className="flex items-start gap-2">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-50 text-xs font-bold text-red-600 mt-0.5">
                        {i + 1}
                      </span>
                      <p className="text-sm text-ink-700 font-medium">{q}</p>
                    </div>
                    <Textarea
                      value={redTeamAnswers[i] || ""}
                      onChange={e => setRedTeamAnswers(prev => ({ ...prev, [i]: e.target.value }))}
                      placeholder="认真思考并回答…"
                      className="ml-7 resize-y min-h-[50px]"
                    />
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setStep("matrix")}>上一步</Button>
              <Button onClick={() => setStep("summary")}>下一步：综合分析</Button>
            </div>
          </div>
        )}

        {/* Step 5: 综合分析 */}
        {step === "summary" && (
          <div className="card space-y-5">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-brand-600" />
              <h2 className="font-display text-lg font-semibold text-ink-800">AI 综合分析</h2>
            </div>
            <p className="text-sm text-ink-500">
              AI 将综合预验尸、决策矩阵和红队质疑的结果，给出最终的决策建议。
            </p>

            {!aiAnalysis && !aiLoading && (
              <Button onClick={handleSaveAndAnalyze} loading={aiLoading} className="w-full" data-testid="analyze-button">
                <Sparkles className="h-4 w-4" /> 保存并生成 AI 分析
              </Button>
            )}

            {aiLoading && (
              <div className="flex items-center gap-2 text-sm text-ink-400 py-4 justify-center">
                <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-paper-300 border-t-brand-500" />
                AI 正在综合分析你的决策…
              </div>
            )}

            {aiAnalysis && (
              <div className="rounded-lg border border-brand-200 bg-brand-50 p-4">
                <p className="text-sm text-ink-700 leading-relaxed whitespace-pre-line">{aiAnalysis}</p>
              </div>
            )}

            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setStep("redteam")}>上一步</Button>
              <Button variant="secondary" onClick={() => { resetForm(); setShowNew(false); }}>
                完成
              </Button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ====== 列表页 ======
  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div className="text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
          <Scale className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
        </div>
        <h1 className="page-title">决策实验室</h1>
        <p className="text-sm text-ink-400 mt-2 leading-relaxed">
          预验尸 + 决策矩阵 + 红队质疑
          <br />
          三重防线让重要决策更健壮
        </p>
      </div>

      <div className="card">
        <Button onClick={() => { resetForm(); setShowNew(true); }} className="w-full" data-testid="new-decision-button">
          <Plus className="h-4 w-4" /> 新建决策分析
        </Button>
      </div>

      {analyses.length === 0 ? (
        <EmptyState
          title="还没有决策分析"
          description="创建你的第一个决策分析，用预验尸和红队质疑来压力测试你的决策。"
        />
      ) : (
        <div className="card space-y-2">
          <h2 className="font-display font-semibold text-ink-800 mb-2">历史分析</h2>
          {analyses.map(a => (
            <button
              key={a.id}
              onClick={() => setSelectedAnalysis(a)}
              className="flex items-center justify-between w-full rounded-lg border border-paper-200 p-3 hover:border-brand-300 transition-colors text-left"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-ink-800 truncate">{a.title}</p>
                <p className="text-xs text-ink-400 mt-0.5">
                  {a.options.join(" vs ")} · {formatDate(a.created_at)}
                </p>
              </div>
              {a.winner && (
                <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-600 shrink-0 ml-2">
                  <Trophy className="h-3 w-3" /> {a.winner}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ====== 分析详情 ======
function AnalysisDetail({ analysis, onBack }: { analysis: DecisionAnalysisResponse; onBack: () => void }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <button onClick={onBack} className="text-sm text-ink-400 hover:text-ink-600 transition-colors">
        ← 返回列表
      </button>

      <div className="card">
        <h1 className="font-display text-xl font-semibold text-ink-800">{analysis.title}</h1>
        <p className="text-sm text-ink-400 mt-1">
          {analysis.options.join(" vs ")} · {formatDate(analysis.created_at)}
        </p>
        {analysis.winner && (
          <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1 text-sm font-medium text-amber-600">
            <Trophy className="h-4 w-4" /> 推荐选项：{analysis.winner}
          </div>
        )}
      </div>

      {/* 加权结果 */}
      {analysis.weighted_results && analysis.weighted_results.length > 0 && (
        <div className="card space-y-3">
          <h2 className="font-display font-semibold text-ink-800">决策矩阵结果</h2>
          {analysis.weighted_results.map((r, i) => (
            <div key={r.name} className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-ink-700 flex items-center gap-1.5">
                  {r.name === analysis.winner && <Trophy className="h-4 w-4 text-amber-500" />}
                  {r.name}
                </span>
                <span className={cn("text-sm font-bold", r.name === analysis.winner ? "text-brand-600" : "text-ink-500")}>
                  {Number(r.total).toFixed(1)}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-paper-200">
                <div
                  className={cn("h-full rounded-full", r.name === analysis.winner ? "bg-brand-500" : "bg-ink-300")}
                  style={{ width: `${Math.min(100, (Number(r.total) / (Number(analysis.weighted_results[0]?.total) || 1)) * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 预验尸结果 */}
      {analysis.safeguards && analysis.safeguards.length > 0 && (
        <div className="card space-y-3">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-brand-600" />
            <h2 className="font-display font-semibold text-ink-800">保障措施</h2>
          </div>
          {analysis.safeguards.map((s, i) => (
            <div key={s.category} className="rounded-md bg-paper-50 p-2 border border-paper-200">
              <span className="text-xs font-medium text-brand-600">{s.category}：</span>
              <span className="text-xs text-ink-600">{s.action}</span>
            </div>
          ))}
        </div>
      )}

      {/* 红队问答 */}
      {analysis.red_team_questions && analysis.red_team_questions.length > 0 && (
        <div className="card space-y-3">
          <div className="flex items-center gap-2">
            <Swords className="h-4 w-4 text-red-500" />
            <h2 className="font-display font-semibold text-ink-800">红队问答</h2>
          </div>
          <button onClick={() => setExpanded(!expanded)} className="text-xs text-ink-400">
            {expanded ? <ChevronDown className="inline h-3.5 w-3.5" /> : <ChevronRight className="inline h-3.5 w-3.5" />}
            {expanded ? "收起" : "展开"}
          </button>
          {expanded && analysis.red_team_questions.map((q, i) => (
            <div key={`q-${i}`} className="space-y-1">
              <p className="text-sm text-ink-700 font-medium">Q{i + 1}. {q}</p>
              {analysis.red_team_answers[i] && (
                <p className="text-xs text-ink-500 ml-4">A: {analysis.red_team_answers[i]}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* AI 分析 */}
      {analysis.ai_analysis && (
        <div className="card space-y-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-brand-600" />
            <h2 className="font-display font-semibold text-ink-800">AI 综合分析</h2>
          </div>
          <p className="text-sm text-ink-600 leading-relaxed whitespace-pre-line">{analysis.ai_analysis}</p>
        </div>
      )}
    </div>
  );
}
