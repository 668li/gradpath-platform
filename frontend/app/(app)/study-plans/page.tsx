"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { studyPlanApi } from "@/lib/api";
import { StudyPlan, StudyPlanCreate } from "@/types";
import { toast } from "sonner";
import { Plus, Trash2, Edit2, Sparkles } from "lucide-react";

export default function StudyPlansPage() {
  const [plans, setPlans] = useState<StudyPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState<StudyPlanCreate>({
    title: "",
    start_date: "",
    end_date: "",
    subjects: [],
    progress: 0,
  });

  useEffect(() => {
    loadPlans();
  }, []);

  const loadPlans = async () => {
    try {
      setLoading(true);
      const data = await studyPlanApi.list();
      setPlans(data);
    } catch {
      toast.error("加载学习计划失败");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await studyPlanApi.create(formData);
      toast.success("创建成功");
      setShowCreateForm(false);
      setFormData({ title: "", start_date: "", end_date: "", subjects: [], progress: 0 });
      loadPlans();
    } catch {
      toast.error("创建失败");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除这个学习计划吗？")) return;
    try {
      await studyPlanApi.delete(id);
      toast.success("删除成功");
      loadPlans();
    } catch {
      toast.error("删除失败");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink-800">学习计划</h1>
          <p className="text-sm text-ink-500 mt-1">规划你的备考进度</p>
        </div>
        <div className="flex gap-3">
          <Link
            href="/study-plans/ai-generate"
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 transition-all"
          >
            <Sparkles className="w-4 h-4" />
            AI 生成计划
          </Link>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="flex items-center gap-2 px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors"
          >
            <Plus className="w-4 h-4" />
            新建计划
          </button>
        </div>
      </div>

      {/* 创建表单 */}
      {showCreateForm && (
        <div className="rounded-xl border border-ink-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-ink-800 mb-4">创建学习计划</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">计划标题</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="例如：408 计算机综合复习计划"
                required
                className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/30"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-ink-700 mb-1">开始日期</label>
                <input
                  type="date"
                  value={formData.start_date || ""}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/30"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-700 mb-1">结束日期</label>
                <input
                  type="date"
                  value={formData.end_date || ""}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/30"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors">
                创建
              </button>
              <button type="button" onClick={() => setShowCreateForm(false)} className="px-4 py-2 border border-ink-200 text-ink-600 rounded-lg hover:bg-ink-50 transition-colors">
                取消
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 计划列表 */}
      {plans.length === 0 ? (
        <div className="rounded-xl border border-ink-200 bg-white p-12 text-center">
          <p className="text-ink-500 mb-4">还没有学习计划</p>
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors"
          >
            创建第一个计划
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {plans.map((plan) => (
            <div key={plan.id} className="rounded-xl border border-ink-200 bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-ink-800">{plan.title}</h3>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {plan.start_date && (
                      <span className="px-2 py-0.5 text-xs font-medium rounded-full border border-ink-200 text-ink-600">
                        {plan.start_date}
                      </span>
                    )}
                    {plan.end_date && (
                      <span className="px-2 py-0.5 text-xs font-medium rounded-full border border-ink-200 text-ink-600">
                        {plan.end_date}
                      </span>
                    )}
                    {plan.completed && (
                      <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-brand-500/15 text-brand-700">
                        已完成
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => toast.info("编辑功能开发中")}
                    className="p-2 border border-ink-200 text-ink-600 rounded-lg hover:bg-ink-50 transition-colors"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(plan.id)}
                    className="p-2 border border-ink-200 text-ink-600 rounded-lg hover:bg-red-50 hover:text-red-500 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {plan.subjects && plan.subjects.length > 0 && (
                <div className="mb-4">
                  <span className="text-sm text-ink-500">学习科目</span>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {plan.subjects.map((subject, idx) => (
                      <span key={`${subject}-${idx}`} className="px-2 py-0.5 text-xs font-medium rounded-full bg-ink-100 text-ink-700">
                        {subject}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-ink-600">进度</span>
                  <span className="text-sm font-medium text-ink-800">{plan.progress}%</span>
                </div>
                <div className="w-full h-2 bg-ink-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-500 transition-all"
                    style={{ width: `${plan.progress}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
