"use client";

import { memo, useCallback, useEffect, useState } from "react";
import {
  Target,
  Shield,
  AlertTriangle,
  Brain,
  TrendingUp,
  XCircle,
  Bookmark,
} from "lucide-react";
import { gradIntelApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button, Input, Textarea, Select, Field } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { ErrorBoundary } from "@/components/error-boundary";
import type {
  PositioningResponse,
  PositioningCreateRequest,
  SchoolRecommendation,
} from "@/types";

function PositioningResult({ result }: { result: PositioningResponse }) {
  return (
    <div className="space-y-4">
      {result.success_probability != null && (
        <div className="rounded-xl border border-brand-200 bg-gradient-to-br from-brand-50 to-white p-5 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="relative flex h-20 w-20 flex-shrink-0 items-center justify-center">
              <svg className="h-20 w-20 -rotate-90" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="34" fill="none" stroke="#e2e8f0" strokeWidth="6" />
                <circle
                  cx="40"
                  cy="40"
                  r="34"
                  fill="none"
                  stroke="#0d9488"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 34 * result.success_probability / 100} ${2 * Math.PI * 34}`}
                />
              </svg>
              <span className="absolute text-xl font-bold text-brand-700">
                {result.success_probability}%
              </span>
            </div>
            <div>
              <h3 className="text-base font-semibold text-ink-800">整体上岸概率评估</h3>
              <p className="text-sm text-ink-500">
                {result.success_probability >= 70
                  ? "竞争力较强，合理报考有较大概率成功"
                  : result.success_probability >= 50
                  ? "有一定竞争力，需精心选校和努力备考"
                  : result.success_probability >= 30
                  ? "竞争力偏弱，建议以保守策略为主"
                  : "竞争力不足，建议大幅调整目标或补齐短板"}
              </p>
            </div>
          </div>
        </div>
      )}

      {result.ai_assessment && (
        <div className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
          <div className="mb-2 flex items-center gap-1.5">
            <Brain className="h-5 w-5 text-brand-600" />
            <h3 className="text-base font-semibold text-ink-800">AI 评估报告</h3>
          </div>
          <p className="text-sm text-ink-600 whitespace-pre-line leading-relaxed">{result.ai_assessment}</p>
        </div>
      )}

      {result.risk_warnings.length > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <div className="mb-2 flex items-center gap-1.5">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            <h3 className="text-base font-semibold text-red-800">风险提示</h3>
          </div>
          <ul className="space-y-1.5">
            {result.risk_warnings.map((w, i) => (
              <li key={`warn-${i}`} className="text-sm text-red-700 flex gap-2">
                <span className="text-red-400 flex-shrink-0">•</span>
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <SchoolTierCard
          title="冲刺"
          icon={TrendingUp}
          color="red"
          schools={result.reach_schools}
          desc="20-40% 概率"
        />
        <SchoolTierCard
          title="稳妥"
          icon={Target}
          color="green"
          schools={result.target_schools}
          desc="50-70% 概率"
        />
        <SchoolTierCard
          title="保底"
          icon={Shield}
          color="blue"
          schools={result.safety_schools}
          desc="80-95% 概率"
        />
      </div>
    </div>
  );
}

function SchoolTierCard({
  title,
  icon: Icon,
  color,
  schools,
  desc,
}: {
  title: string;
  icon: typeof Target;
  color: "red" | "green" | "blue";
  schools: SchoolRecommendation[];
  desc: string;
}) {
  const colorMap = {
    red: { bg: "bg-red-50", border: "border-red-200", text: "text-red-700", badge: "bg-red-100 text-red-700" },
    green: { bg: "bg-brand-50", border: "border-brand-200", text: "text-brand-700", badge: "bg-brand-100 text-brand-700" },
    blue: { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700", badge: "bg-blue-100 text-blue-700" },
  };
  const c = colorMap[color];

  return (
    <div className={cn("rounded-xl border p-4", c.border, c.bg)}>
      <div className="mb-3 flex items-center gap-2">
        <Icon className={cn("h-5 w-5", c.text)} strokeWidth={2} />
        <div>
          <h4 className={cn("font-bold", c.text)}>{title}</h4>
          <p className="text-xs text-ink-400">{desc}</p>
        </div>
      </div>
      {schools.length === 0 ? (
        <p className="text-sm text-ink-400 py-4 text-center">暂无推荐</p>
      ) : (
        <div className="space-y-2">
          {schools.map((s, i) => (
            <div key={`${s.name}-${i}`} className="rounded-lg bg-white/70 p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-ink-800">{s.name}</span>
                <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", c.badge)}>
                  {s.probability}%
                </span>
              </div>
              {s.major && <p className="text-xs text-ink-500 mt-0.5">{s.major}</p>}
              {s.tier && <p className="text-xs text-ink-400">{s.tier}</p>}
              {s.reason && <p className="text-xs text-ink-500 mt-1">{s.reason}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export const SelfPositioning = memo(function SelfPositioning() {
  const toast = useToast();
  const [form, setForm] = useState<PositioningCreateRequest>({
    undergrad_tier: "",
    undergrad_major: "",
    gpa: undefined,
    gpa_rank: "",
    english_level: "",
    english_score: undefined,
    research_experience: "",
    competitions: [],
    internships: "",
    target_major: "",
    target_region: "",
    other_info: "",
  });
  const [competitionInput, setCompetitionInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<PositioningResponse | null>(null);
  const [loadingLatest, setLoadingLatest] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [history, setHistory] = useState<PositioningResponse[]>([]);

  const loadLatest = useCallback(async () => {
    setLoadingLatest(true);
    setLoadError(false);
    try {
      const [latest, hist] = await Promise.all([
        gradIntelApi.getLatestPositioning(),
        gradIntelApi.getPositioningHistory(),
      ]);
      if (latest) setResult(latest);
      setHistory(hist);
    } catch {
      setLoadError(true);
    } finally {
      setLoadingLatest(false);
    }
  }, []);

  useEffect(() => {
    loadLatest();
  }, [loadLatest]);

  const handleSubmit = async () => {
    if (!form.undergrad_tier) {
      toast.push("请选择本科层次", "info");
      return;
    }
    setSubmitting(true);
    try {
      const res = await gradIntelApi.createPositioning(form);
      setResult(res);
      toast.push("AI 定位分析完成", "success");
      const hist = await gradIntelApi.getPositioningHistory();
      setHistory(hist);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "分析失败";
      toast.push(msg, "error");
    } finally {
      setSubmitting(false);
    }
  };

  const addCompetition = () => {
    const val = competitionInput.trim();
    const current = form.competitions || [];
    if (val && !current.includes(val)) {
      setForm({ ...form, competitions: [...current, val] });
      setCompetitionInput("");
    }
  };

  const removeCompetition = (idx: number) => {
    const current = form.competitions || [];
    setForm({ ...form, competitions: current.filter((_, i) => i !== idx) });
  };

  if (loadingLatest) {
    return <LoadingState text="加载定位数据…" />;
  }

  if (loadError && !result) {
    return (
      <EmptyState
        title="加载失败"
        description="无法加载定位数据，请稍后重试"
        action={
          <Button size="sm" variant="secondary" onClick={loadLatest}>
            重试
          </Button>
        }
      />
    );
  }

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <div className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
          <h2 className="mb-1 text-base font-semibold text-ink-800">背景信息录入</h2>
          <p className="mb-4 text-sm text-ink-400">
            如实填写你的背景，AI 会评估竞争力并推荐冲刺/稳妥/保底三档院校。
          </p>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="本科层次" required>
              <Select
                value={form.undergrad_tier}
                onChange={(e) => setForm({ ...form, undergrad_tier: e.target.value })}
              >
                <option value="">请选择</option>
                <option value="985">985</option>
                <option value="211">211</option>
                <option value="双一流">双一流（非985/211）</option>
                <option value="一本">普通一本</option>
                <option value="二本">二本</option>
                <option value="三本">三本/独立学院</option>
                <option value="专升本">专升本</option>
              </Select>
            </Field>
            <Field label="本科专业">
              <Input
                value={form.undergrad_major || ""}
                onChange={(e) => setForm({ ...form, undergrad_major: e.target.value })}
                placeholder="如：软件工程"
              />
            </Field>
            <Field label="GPA" hint="如 3.5 / 4.0">
              <Input
                type="number"
                step="0.01"
                value={form.gpa ?? ""}
                onChange={(e) => setForm({ ...form, gpa: e.target.value ? parseFloat(e.target.value) : undefined })}
                placeholder="3.5"
              />
            </Field>
            <Field label="排名" hint="如 专业前 20%">
              <Input
                value={form.gpa_rank || ""}
                onChange={(e) => setForm({ ...form, gpa_rank: e.target.value })}
                placeholder="前 20%"
              />
            </Field>
            <Field label="英语等级">
              <Select
                value={form.english_level || ""}
                onChange={(e) => setForm({ ...form, english_level: e.target.value })}
              >
                <option value="">请选择</option>
                <option value="cet4">CET-4</option>
                <option value="cet6">CET-6</option>
                <option value="ielts">IELTS</option>
                <option value="toefl">TOEFL</option>
                <option value="none">未考</option>
              </Select>
            </Field>
            <Field label="英语分数">
              <Input
                type="number"
                value={form.english_score ?? ""}
                onChange={(e) => setForm({ ...form, english_score: e.target.value ? parseInt(e.target.value) : undefined })}
                placeholder="如 550"
              />
            </Field>
            <Field label="科研经历" hint="论文、项目、实验室等">
              <Textarea
                value={form.research_experience || ""}
                onChange={(e) => setForm({ ...form, research_experience: e.target.value })}
                placeholder="如：参与导师 XX 课题，发表 1 篇 EI 会议论文"
                className="min-h-[60px]"
              />
            </Field>
            <Field label="实习经历">
              <Textarea
                value={form.internships || ""}
                onChange={(e) => setForm({ ...form, internships: e.target.value })}
                placeholder="如：字节跳动后端实习 3 个月"
                className="min-h-[60px]"
              />
            </Field>
            <Field label="目标专业">
              <Input
                value={form.target_major || ""}
                onChange={(e) => setForm({ ...form, target_major: e.target.value })}
                placeholder="如：计算机技术（专硕）"
              />
            </Field>
            <Field label="目标地区">
              <Input
                value={form.target_region || ""}
                onChange={(e) => setForm({ ...form, target_region: e.target.value })}
                placeholder="如：江浙沪"
              />
            </Field>
          </div>

          <div className="mt-4">
            <Field label="竞赛获奖">
              <div className="flex gap-2">
                <Input
                  value={competitionInput}
                  onChange={(e) => setCompetitionInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addCompetition();
                    }
                  }}
                  placeholder="如：数学建模国赛二等奖"
                />
                <Button variant="secondary" size="sm" onClick={addCompetition} type="button">
                  添加
                </Button>
              </div>
              {(form.competitions || []).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {(form.competitions || []).map((c, i) => (
                    <span
                      key={`comp-${i}`}
                      className="inline-flex items-center gap-1 rounded-full bg-brand-100 px-2.5 py-1 text-xs text-brand-700"
                    >
                      {c}
                      <button
                        onClick={() => removeCompetition(i)}
                        aria-label={`移除竞赛 ${c}`}
                        className="text-brand-400 hover:text-brand-600"
                      >
                        <XCircle className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </Field>
          </div>

          <Field label="其他补充信息">
            <Textarea
              value={form.other_info || ""}
              onChange={(e) => setForm({ ...form, other_info: e.target.value })}
              placeholder="任何你觉得对评估有帮助的信息"
              className="min-h-[60px]"
            />
          </Field>

          <div className="mt-4">
            <Button onClick={handleSubmit} loading={submitting}>
              <Target className="h-4 w-4" />
              生成定位分析
            </Button>
          </div>
        </div>

        {submitting && (
          <div className="rounded-xl border border-paper-200 bg-white p-8">
            <LoadingState text="AI 正在评估你的竞争力并推荐院校…" />
          </div>
        )}

        {result && !submitting && <PositioningResult result={result} />}

        {history.length > 1 && (
          <div>
            <div className="mb-3 flex items-center gap-2">
              <Bookmark className="h-4 w-4 text-ink-400" />
              <h2 className="text-sm font-semibold text-ink-700">历史定位</h2>
            </div>
            <div className="space-y-2">
              {history.slice(1).map((h) => (
                <button
                  key={h.id}
                  onClick={() => setResult(h)}
                  className="w-full rounded-lg border border-paper-200 bg-white p-3 text-left hover:border-brand-300 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-ink-700">
                      {h.undergrad_tier} · {h.target_major || "未指定专业"}
                    </span>
                    <span className="text-xs text-ink-400">
                      {new Date(h.created_at).toLocaleDateString("zh-CN")}
                    </span>
                  </div>
                  {h.success_probability != null && (
                    <span className="text-xs text-brand-600">
                      成功概率: {h.success_probability}%
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
});
