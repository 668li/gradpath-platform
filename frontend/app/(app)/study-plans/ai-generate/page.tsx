"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { aiStudyPlanApi, GeneratePlanRequest, GeneratePlanResponse } from "@/lib/api/ai-study-plan";
import { toast } from "sonner";
import { Sparkles, Save, ChevronDown, ChevronUp, Calendar, Clock, Target } from "lucide-react";

export default function AIGeneratePlanPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [plan, setPlan] = useState<GeneratePlanResponse | null>(null);
  const [expandedPhases, setExpandedPhases] = useState<Set<number>>(new Set([0]));
  const [formData, setFormData] = useState<GeneratePlanRequest>({
    target_school: "",
    target_major: "",
    current_score: 300,
    target_score: 380,
    weak_subjects: [],
    exam_date: "",
    study_hours_per_day: 8,
  });

  const subjects = ["数学", "英语", "政治", "专业课"];

  const toggleSubject = (subject: string) => {
    setFormData((prev) => ({
      ...prev,
      weak_subjects: prev.weak_subjects.includes(subject)
        ? prev.weak_subjects.filter((s) => s !== subject)
        : [...prev.weak_subjects, subject],
    }));
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.target_school || !formData.target_major || !formData.exam_date) {
      toast.error("请填写完整信息");
      return;
    }

    try {
      setGenerating(true);
      const result = await aiStudyPlanApi.generate(formData);
      setPlan(result);
      toast.success("学习计划生成成功！");
    } catch (error) {
      toast.error("生成失败，请稍后重试");
    } finally {
      setGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!plan) return;
    try {
      setLoading(true);
      await aiStudyPlanApi.save(formData, plan);
      toast.success("计划保存成功！");
      router.push("/study-plans");
    } catch (error) {
      toast.error("保存失败");
    } finally {
      setLoading(false);
    }
  };

  const togglePhase = (index: number) => {
    setExpandedPhases((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const getPhaseColor = (name: string) => {
    if (name.includes("基础")) return "bg-blue-500";
    if (name.includes("强化")) return "bg-orange-500";
    if (name.includes("冲刺")) return "bg-red-500";
    return "bg-gray-500";
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
          <Sparkles className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-ink-800">AI 智能学习计划</h1>
          <p className="text-sm text-ink-500">基于你的目标和现状，生成个性化备考方案</p>
        </div>
      </div>

      {/* Form */}
      {!plan && (
        <form onSubmit={handleGenerate} className="rounded-xl border border-ink-200 bg-white p-6 shadow-sm space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Target School */}
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-2">
                <Target className="w-4 h-4 inline mr-1" />
                目标院校
              </label>
              <input
                type="text"
                value={formData.target_school}
                onChange={(e) => setFormData({ ...formData, target_school: e.target.value })}
                placeholder="例如：清华大学"
                required
                className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/30"
              />
            </div>

            {/* Target Major */}
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-2">
                <Target className="w-4 h-4 inline mr-1" />
                目标专业
              </label>
              <input
                type="text"
                value={formData.target_major}
                onChange={(e) => setFormData({ ...formData, target_major: e.target.value })}
                placeholder="例如：计算机科学与技术"
                required
                className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/30"
              />
            </div>

            {/* Current Score */}
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-2">
                当前预估分数
              </label>
              <input
                type="number"
                value={formData.current_score}
                onChange={(e) => setFormData({ ...formData, current_score: parseInt(e.target.value) || 0 })}
                min={0}
                max={500}
                className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/30"
              />
            </div>

            {/* Target Score */}
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-2">
                目标分数
              </label>
              <input
                type="number"
                value={formData.target_score}
                onChange={(e) => setFormData({ ...formData, target_score: parseInt(e.target.value) || 0 })}
                min={0}
                max={500}
                className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/30"
              />
            </div>

            {/* Exam Date */}
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-2">
                <Calendar className="w-4 h-4 inline mr-1" />
                考试日期
              </label>
              <input
                type="date"
                value={formData.exam_date}
                onChange={(e) => setFormData({ ...formData, exam_date: e.target.value })}
                required
                className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/30"
              />
            </div>

            {/* Study Hours */}
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-2">
                <Clock className="w-4 h-4 inline mr-1" />
                每日学习时长（小时）
              </label>
              <input
                type="number"
                value={formData.study_hours_per_day}
                onChange={(e) => setFormData({ ...formData, study_hours_per_day: parseInt(e.target.value) || 8 })}
                min={1}
                max={16}
                className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/30"
              />
            </div>
          </div>

          {/* Weak Subjects */}
          <div>
            <label className="block text-sm font-medium text-ink-700 mb-2">
              薄弱科目（可多选）
            </label>
            <div className="flex flex-wrap gap-2">
              {subjects.map((subject) => (
                <button
                  key={subject}
                  type="button"
                  onClick={() => toggleSubject(subject)}
                  className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                    formData.weak_subjects.includes(subject)
                      ? "bg-purple-500 text-white border-purple-500"
                      : "bg-white text-ink-700 border-ink-200 hover:border-purple-300"
                  }`}
                >
                  {subject}
                </button>
              ))}
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={generating}
            className="w-full py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg font-medium hover:from-purple-600 hover:to-pink-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generating ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                正在生成学习计划...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <Sparkles className="w-5 h-5" />
                生成 AI 学习计划
              </span>
            )}
          </button>
        </form>
      )}

      {/* Generated Plan */}
      {plan && (
        <div className="space-y-6">
          {/* Summary Card */}
          <div className="rounded-xl border border-ink-200 bg-gradient-to-br from-purple-50 to-pink-50 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-ink-800">计划概览</h2>
              <button
                onClick={() => setPlan(null)}
                className="text-sm text-ink-500 hover:text-ink-700"
              >
                重新生成
              </button>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="bg-white rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-purple-600">{plan.total_days}</div>
                <div className="text-xs text-ink-500">备考天数</div>
              </div>
              <div className="bg-white rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-blue-600">{plan.phases.length}</div>
                <div className="text-xs text-ink-500">备考阶段</div>
              </div>
              <div className="bg-white rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-green-600">+{plan.target_score - plan.current_score}</div>
                <div className="text-xs text-ink-500">目标提分</div>
              </div>
              <div className="bg-white rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-orange-600">{plan.phases.reduce((acc, p) => acc + p.weekly_plan.length, 0)}</div>
                <div className="text-xs text-ink-500">总周数</div>
              </div>
            </div>

            <div className="bg-white rounded-lg p-4">
              <h3 className="font-medium text-ink-700 mb-2">AI 总结</h3>
              <pre className="text-sm text-ink-600 whitespace-pre-wrap font-sans">{plan.ai_summary}</pre>
            </div>
          </div>

          {/* Daily Schedule */}
          <div className="rounded-xl border border-ink-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-ink-800 mb-4">每日时间安排</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-yellow-50 rounded-lg">
                <div className="font-medium text-yellow-800 mb-1">上午</div>
                <div className="text-sm text-yellow-700">{plan.daily_schedule.morning}</div>
              </div>
              <div className="p-4 bg-blue-50 rounded-lg">
                <div className="font-medium text-blue-800 mb-1">下午</div>
                <div className="text-sm text-blue-700">{plan.daily_schedule.afternoon}</div>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg">
                <div className="font-medium text-purple-800 mb-1">晚上</div>
                <div className="text-sm text-purple-700">{plan.daily_schedule.evening}</div>
              </div>
            </div>
          </div>

          {/* Phases */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-ink-800">阶段规划</h2>
            {plan.phases.map((phase, phaseIndex) => (
              <div key={phaseIndex} className="rounded-xl border border-ink-200 bg-white shadow-sm overflow-hidden">
                <button
                  onClick={() => togglePhase(phaseIndex)}
                  className="w-full flex items-center justify-between p-4 hover:bg-ink-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${getPhaseColor(phase.name)}`} />
                    <div className="text-left">
                      <div className="font-medium text-ink-800">{phase.name}</div>
                      <div className="text-sm text-ink-500">{phase.duration_days} 天</div>
                    </div>
                  </div>
                  {expandedPhases.has(phaseIndex) ? (
                    <ChevronUp className="w-5 h-5 text-ink-400" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-ink-400" />
                  )}
                </button>

                {expandedPhases.has(phaseIndex) && (
                  <div className="border-t border-ink-100 p-4 space-y-4">
                    {/* Goals */}
                    <div>
                      <h4 className="text-sm font-medium text-ink-700 mb-2">阶段目标</h4>
                      <ul className="list-disc list-inside text-sm text-ink-600 space-y-1">
                        {phase.goals.map((goal, i) => (
                          <li key={`${goal}-${i}`}>{goal}</li>
                        ))}
                      </ul>
                    </div>

                    {/* Weekly Plans */}
                    <div>
                      <h4 className="text-sm font-medium text-ink-700 mb-3">周计划</h4>
                      <div className="space-y-3">
                        {phase.weekly_plan.map((week) => (
                          <div key={week.week} className="bg-ink-50 rounded-lg p-3">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium text-ink-700">第 {week.week} 周</span>
                              <span className="text-xs text-ink-500">{week.milestone}</span>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                              {week.subjects.map((subject, i) => (
                                <div key={`${subject.subject}-${i}`} className="bg-white rounded p-2 text-sm">
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="font-medium text-ink-700">{subject.subject}</span>
                                    <span className="text-xs text-purple-600">{subject.daily_hours}h/天</span>
                                  </div>
                                  <ul className="text-xs text-ink-500 space-y-0.5">
                                    {subject.tasks.slice(0, 2).map((task, j) => (
                                      <li key={j}>• {task}</li>
                                    ))}
                                  </ul>
                                </div>
                              ))}
                            </div>
                            <div className="mt-2 text-xs text-ink-500">
                              📝 周测：{week.weekly_test}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Tips */}
          <div className="rounded-xl border border-ink-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-ink-800 mb-4">备考建议</h2>
            <ul className="space-y-2">
              {plan.tips.map((tip, i) => (
                <li key={`${tip}-${i}`} className="flex items-start gap-2 text-sm text-ink-600">
                  <span className="text-green-500 mt-0.5">✓</span>
                  {tip}
                </li>
              ))}
            </ul>
          </div>

          {/* Save Button */}
          <div className="flex gap-4">
            <button
              onClick={handleSave}
              disabled={loading}
              className="flex-1 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-lg font-medium hover:from-green-600 hover:to-emerald-600 transition-all disabled:opacity-50"
            >
              {loading ? "保存中..." : "保存学习计划"}
            </button>
            <button
              onClick={() => setPlan(null)}
              className="px-6 py-3 border border-ink-200 text-ink-600 rounded-lg hover:bg-ink-50 transition-colors"
            >
              重新生成
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
