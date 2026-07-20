"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Compass,
  ArrowLeft,
  ArrowRight,
  Check,
  Sparkles,
  GraduationCap,
  Landmark,
  Briefcase,
  Plane,
  Rocket,
  Coffee,
  Brain,
  Users,
  Target,
  Lightbulb,
  AlertCircle,
} from "lucide-react";
import { onboardingApi } from "@/lib/api";
import { useOnboardingStore } from "@/stores/onboarding";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";
import { Button, Field } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type { OnboardingRecord } from "@/types";

// ===== 步骤配置 =====

const STAGES = [
  { value: "freshman", label: "大一", desc: "刚入学，探索方向", testId: "status-freshman" },
  { value: "sophomore", label: "大二", desc: "开始聚焦目标", testId: "status-sophomore" },
  { value: "junior", label: "大三", desc: "关键准备期", testId: "status-student" },
  { value: "senior", label: "大四", desc: "冲刺与决策", testId: "status-senior" },
  { value: "graduated", label: "已毕业", desc: "在职或待业", testId: "status-graduated" },
] as const;

const DIRECTIONS = [
  { value: "postgrad", label: "考研", icon: GraduationCap, color: "text-blue-600 bg-blue-50 border-blue-200", testId: "goal-kaoyan" },
  { value: "civil_service", label: "考公", icon: Landmark, color: "text-emerald-600 bg-emerald-50 border-emerald-200", testId: "goal-civil" },
  { value: "employment", label: "就业", icon: Briefcase, color: "text-orange-600 bg-orange-50 border-orange-200", testId: "goal-career" },
  { value: "abroad", label: "出国", icon: Plane, color: "text-purple-600 bg-purple-50 border-purple-200", testId: "goal-abroad" },
  { value: "phd", label: "读博", icon: Brain, color: "text-rose-600 bg-rose-50 border-rose-200", testId: "goal-phd" },
  { value: "startup", label: "创业", icon: Rocket, color: "text-amber-600 bg-amber-50 border-amber-200", testId: "goal-startup" },
  { value: "gap_year", label: "间隔年", icon: Coffee, color: "text-cyan-600 bg-cyan-50 border-cyan-200", testId: "goal-gap-year" },
] as const;

const INDUSTRIES = [
  "互联网/IT", "金融/投资", "教育/科研", "医疗/健康", "制造业",
  "能源/环保", "媒体/内容", "咨询/法律", "政府/公共事业", "消费/零售",
  "房地产/建筑", "物流/交通", "其他",
] as const;

const SKILL_DIMS = [
  { key: "technical", label: "技术能力", icon: Target, desc: "专业技能、工具掌握" },
  { key: "communication", label: "沟通能力", icon: Users, desc: "表达、协作、人际" },
  { key: "leadership", label: "领导能力", icon: Rocket, desc: "带领团队、决策" },
  { key: "creativity", label: "创新能力", icon: Lightbulb, desc: "发散思考、创造" },
] as const;

const TOTAL_STEPS = 4;

type Step = 0 | 1 | 2 | 3 | 4;

// ===== 主页面 =====

export default function OnboardingPage() {
  const router = useRouter();
  const toast = useToast();
  const markCompleted = useOnboardingStore((s) => s.markCompleted);
  const markSkipped = useOnboardingStore((s) => s.markSkipped);

  const [step, setStep] = useState<Step>(0);
  const [submitting, setSubmitting] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<OnboardingRecord | null>(null);

  // 表单状态
  const [stage, setStage] = useState<string>("");
  const [direction, setDirection] = useState<string>("");
  const [industry, setIndustry] = useState<string>("");
  const [skills, setSkills] = useState<Record<string, number>>({
    technical: 3,
    communication: 3,
    leadership: 3,
    creativity: 3,
  });

  const canProceed = useCallback((): boolean => {
    if (step === 0) return !!stage;
    if (step === 1) return !!direction;
    if (step === 2) return true; // industry 可选
    if (step === 3) return true; // skills 已有默认值
    return false;
  }, [step, stage, direction]);

  const handleNext = async () => {
    if (step < 3) {
      setStep((s) => (s + 1) as Step);
      return;
    }
    // step === 3：提交保存
    setSubmitting(true);
    try {
      await onboardingApi.save({
        current_stage: stage,
        target_direction: direction,
        target_industry: industry || null,
        self_assessment: { skills },
      });
      setStep(4);
    } catch {
      toast.error("保存失败，请重试");
    } finally {
      setSubmitting(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const record = await onboardingApi.generate();
      setResult(record);
      markCompleted(record);
      toast.success("AI 诊断完成！");
    } catch {
      toast.error("AI 诊断暂时不可用，可稍后在个人中心重试");
    } finally {
      setGenerating(false);
    }
  };

  const handleSkip = async () => {
    try {
      await onboardingApi.skip();
      markSkipped();
      router.replace("/dashboard");
    } catch {
      router.replace("/dashboard");
    }
  };

  const handleFinish = () => {
    router.replace("/dashboard");
  };

  // ===== 结果页 =====
  if (result) {
    return (
      <ResultView record={result} onFinish={handleFinish} />
    );
  }

  // ===== 生成中 =====
  if (step === 4) {
    return (
      <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
        <div className="card text-center space-y-5 py-10">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50">
            <Sparkles className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
          </div>
          <div>
            <h1 className="page-title mb-2">生成 AI 诊断</h1>
            <p className="text-sm text-ink-500 leading-relaxed">
              基于你的当前阶段、目标方向与自我评估，AI 将为你生成
              <br />
              个性化诊断报告与推荐路径
            </p>
          </div>

          <div className="rounded-lg bg-paper-50 border border-paper-200 p-4 text-left space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-ink-500">当前阶段</span>
              <span className="font-medium text-ink-800">{STAGES.find((s) => s.value === stage)?.label}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-ink-500">目标方向</span>
              <span className="font-medium text-ink-800">{DIRECTIONS.find((d) => d.value === direction)?.label}</span>
            </div>
            {industry && (
              <div className="flex justify-between text-sm">
                <span className="text-ink-500">目标行业</span>
                <span className="font-medium text-ink-800">{industry}</span>
              </div>
            )}
            <div className="border-t border-paper-200 pt-2 mt-2">
              <p className="text-xs text-ink-400 mb-2">自我评估</p>
              <div className="grid grid-cols-2 gap-2">
                {SKILL_DIMS.map((dim) => (
                  <div key={dim.key} className="flex justify-between text-xs">
                    <span className="text-ink-500">{dim.label}</span>
                    <span className="font-medium text-ink-700">{skills[dim.key]}/5</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {generating ? (
            <LoadingState text="AI 正在分析你的情况…" />
          ) : (
            <div className="space-y-3">
              <Button onClick={handleGenerate} size="md" className="w-full" data-testid="onboarding-generate-button">
                <Sparkles className="h-4 w-4" />
                生成 AI 诊断报告
              </Button>
              <Button variant="ghost" size="sm" onClick={handleFinish} className="w-full" data-testid="onboarding-finish-button">
                稍后再生成，先去个人看板
              </Button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ===== 步骤页 =====
  const progress = ((step + 1) / TOTAL_STEPS) * 100;

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* 顶部 */}
      <div className="text-center space-y-3">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50">
          <Compass className="h-7 w-7 text-brand-600" strokeWidth={1.8} />
        </div>
        <div>
          <h1 className="page-title">5 分钟职业诊断</h1>
          <p className="text-sm text-ink-400 mt-1">
            帮助 AI 更好地理解你，提供个性化建议
          </p>
        </div>
      </div>

      {/* 进度条 */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs">
          <span className="text-ink-500">步骤 {step + 1} / {TOTAL_STEPS}</span>
          <span className="text-ink-400">{Math.round(progress)}% 完成</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-paper-200">
          <div
            className="h-full rounded-full bg-brand-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* 步骤内容 */}
      {step === 0 && (
        <StepStage value={stage} onChange={setStage} />
      )}
      {step === 1 && (
        <StepDirection value={direction} onChange={setDirection} />
      )}
      {step === 2 && (
        <StepIndustry value={industry} onChange={setIndustry} />
      )}
      {step === 3 && (
        <StepSkills value={skills} onChange={setSkills} />
      )}

      {/* 底部操作 */}
      <div className="card flex items-center justify-between gap-3">
        <div>
          {step > 0 ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setStep((s) => (s - 1) as Step)}
              disabled={submitting}
            >
              <ArrowLeft className="h-4 w-4" />
              上一步
            </Button>
          ) : (
            <Button variant="ghost" size="sm" onClick={handleSkip} data-testid="onboarding-skip-button">
              跳过
            </Button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-ink-400">
            {canProceed() ? "可以继续了" : "请完成当前步骤"}
          </span>
          <Button
            onClick={handleNext}
            disabled={!canProceed() || submitting}
            loading={submitting}
            data-testid="onboarding-next-button"
          >
            {step === 3 ? "保存并生成" : "下一步"}
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// ======================================================================
// Step 1: 当前阶段
// ======================================================================

function StepStage({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-display text-lg font-semibold text-ink-800">你目前在哪个阶段？</h2>
        <p className="text-sm text-ink-500 mt-1">这有助于 AI 给出符合你时间线的建议</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {STAGES.map((s) => {
          const active = value === s.value;
          return (
            <button
              key={s.value}
              data-testid={s.testId}
              onClick={() => onChange(s.value)}
              className={cn(
                "flex items-center gap-3 rounded-xl border p-4 text-left transition-all",
                active
                  ? "border-brand-500 bg-brand-50 shadow-sm"
                  : "border-paper-300 bg-white hover:bg-paper-50 hover:border-paper-400",
              )}
            >
              <span
                className={cn(
                  "flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold transition-colors",
                  active ? "bg-brand-500 text-white" : "bg-paper-200 text-ink-400",
                )}
              >
                {active ? <Check className="h-4 w-4" /> : s.label[0]}
              </span>
              <div className="flex-1 min-w-0">
                <p className={cn("font-display font-semibold", active ? "text-brand-700" : "text-ink-800")}>
                  {s.label}
                </p>
                <p className="text-xs text-ink-500 mt-0.5">{s.desc}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ======================================================================
// Step 2: 目标方向
// ======================================================================

function StepDirection({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-display text-lg font-semibold text-ink-800">你的目标方向是？</h2>
        <p className="text-sm text-ink-500 mt-1">选择最接近你当前规划的方向</p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {DIRECTIONS.map((d) => {
          const active = value === d.value;
          const Icon = d.icon;
          return (
            <button
              key={d.value}
              data-testid={d.testId}
              onClick={() => onChange(d.value)}
              className={cn(
                "flex flex-col items-center gap-2 rounded-xl border p-4 transition-all",
                active
                  ? "border-brand-500 bg-brand-50 shadow-sm"
                  : "border-paper-300 bg-white hover:bg-paper-50 hover:border-paper-400",
              )}
            >
              <span
                className={cn(
                  "flex h-11 w-11 items-center justify-center rounded-xl transition-colors",
                  active ? "bg-brand-500 text-white" : cn(d.color, "border"),
                )}
              >
                <Icon className="h-5 w-5" strokeWidth={1.8} />
              </span>
              <span
                className={cn(
                  "font-display font-semibold text-sm",
                  active ? "text-brand-700" : "text-ink-700",
                )}
              >
                {d.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ======================================================================
// Step 3: 目标行业（可选）
// ======================================================================

function StepIndustry({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-display text-lg font-semibold text-ink-800">目标行业（可选）</h2>
        <p className="text-sm text-ink-500 mt-1">选择你感兴趣的行业，跳过则表示暂未确定</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {INDUSTRIES.map((ind) => {
          const active = value === ind;
          return (
            <button
              key={ind}
              onClick={() => onChange(active ? "" : ind)}
              className={cn(
                "rounded-full border px-3.5 py-1.5 text-sm font-medium transition-all",
                active
                  ? "border-brand-500 bg-brand-50 text-brand-700"
                  : "border-paper-300 bg-white text-ink-600 hover:bg-paper-50",
              )}
            >
              {ind}
            </button>
          );
        })}
      </div>
      {value && (
        <div className="rounded-lg bg-brand-50 border border-brand-200 p-3 text-sm text-brand-700">
          已选择：<span className="font-semibold">{value}</span>
        </div>
      )}
    </div>
  );
}

// ======================================================================
// Step 4: 自我评估（4 维度评分）
// ======================================================================

function StepSkills({
  value,
  onChange,
}: {
  value: Record<string, number>;
  onChange: (v: Record<string, number>) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-display text-lg font-semibold text-ink-800">自我评估</h2>
        <p className="text-sm text-ink-500 mt-1">拖动滑块对四项能力进行自评（1=很弱，5=很强）</p>
      </div>
      <div className="space-y-4">
        {SKILL_DIMS.map((dim) => {
          const Icon = dim.icon;
          const score = value[dim.key] ?? 3;
          return (
            <div key={dim.key} className="card space-y-2">
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50">
                  <Icon className="h-4 w-4 text-brand-600" strokeWidth={1.8} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="font-display font-semibold text-ink-800">{dim.label}</p>
                    <span className="text-sm font-semibold text-brand-600">{score}/5</span>
                  </div>
                  <p className="text-xs text-ink-400 mt-0.5">{dim.desc}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 pt-1">
                <span className="text-xs text-ink-400">1</span>
                <input
                  type="range"
                  min={1}
                  max={5}
                  step={1}
                  value={score}
                  onChange={(e) => onChange({ ...value, [dim.key]: Number(e.target.value) })}
                  className="flex-1 accent-brand-500"
                />
                <span className="text-xs text-ink-400">5</span>
                <div className="flex gap-1 ml-2">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      onClick={() => onChange({ ...value, [dim.key]: n })}
                      className={cn(
                        "h-2 w-2 rounded-full transition-colors",
                        n <= score ? "bg-brand-500" : "bg-paper-200",
                      )}
                      aria-label={`评分 ${n}`}
                    />
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ======================================================================
// 结果视图
// ======================================================================

function ResultView({
  record,
  onFinish,
}: {
  record: OnboardingRecord;
  onFinish: () => void;
}) {
  const hasDiagnosis = !!record.ai_diagnosis;
  const recommendedPath = record.recommended_path ?? [];
  const keyInsights = record.key_insights ?? [];

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* 头部 */}
      <div className="text-center space-y-3">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50">
          <Check className="h-7 w-7 text-emerald-600" strokeWidth={2.2} />
        </div>
        <div>
          <h1 className="page-title">诊断完成</h1>
          <p className="text-sm text-ink-400 mt-1">
            AI 已基于你的输入生成个性化诊断报告
          </p>
        </div>
      </div>

      {/* AI 诊断 */}
      {hasDiagnosis && (
        <div className="card space-y-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-brand-600" />
            <h2 className="font-display font-semibold text-ink-800">AI 诊断</h2>
          </div>
          <div className="rounded-lg bg-paper-50 border border-paper-200 p-4">
            <p className="text-sm text-ink-700 leading-relaxed whitespace-pre-line">
              {record.ai_diagnosis}
            </p>
          </div>
        </div>
      )}

      {/* 关键洞察 */}
      {keyInsights.length > 0 && (
        <div className="card space-y-3">
          <div className="flex items-center gap-2">
            <Lightbulb className="h-4 w-4 text-amber-500" />
            <h2 className="font-display font-semibold text-ink-800">关键洞察</h2>
          </div>
          <ul className="space-y-2">
            {keyInsights.map((insight, i) => (
              <li key={`insight-${i}`} className="flex items-start gap-2 text-sm text-ink-700">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-50 text-xs font-bold text-amber-600 mt-0.5">
                  {i + 1}
                </span>
                <span className="leading-relaxed">{insight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 推荐路径 */}
      {recommendedPath.length > 0 && (
        <div className="card space-y-3">
          <div className="flex items-center gap-2">
            <Compass className="h-4 w-4 text-brand-600" />
            <h2 className="font-display font-semibold text-ink-800">推荐路径</h2>
          </div>
          <ol className="space-y-3">
            {recommendedPath.map((p, i) => (
              <li key={`path-${i}`} className="flex items-start gap-3">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-500 text-white text-xs font-bold">
                  {i + 1}
                </span>
                <p className="text-sm text-ink-700 leading-relaxed pt-1">{p}</p>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* 无诊断提示 */}
      {!hasDiagnosis && (
        <div className="card flex items-start gap-3 border-amber-200 bg-amber-50">
          <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-sm text-ink-700">
            <p className="font-medium">AI 诊断未生成</p>
            <p className="text-ink-500 mt-1">可稍后在个人中心重新生成，或先去个人看板探索。</p>
          </div>
        </div>
      )}

      {/* 完成 */}
      <div className="flex justify-center pt-2">
        <Button onClick={onFinish} size="md">
          进入个人看板
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
