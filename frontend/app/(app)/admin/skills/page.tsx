"use client";

import { useEffect, useState } from "react";
import { skillApi } from "@/lib/api";
import type { SkillInfo, SkillCategory } from "@/types";

const CATEGORY_LABELS: Record<SkillCategory, string> = {
  builder: "构建器",
  advisor: "顾问",
  generator: "生成器",
};

const CATEGORY_COLORS: Record<SkillCategory, string> = {
  builder: "bg-blue-500/15 text-blue-700 border-blue-500/30",
  advisor: "bg-amber-500/15 text-amber-700 border-amber-500/30",
  generator: "bg-emerald-500/15 text-emerald-700 border-emerald-500/30",
};

export default function SkillsPage() {
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<SkillCategory | "all">("all");

  useEffect(() => {
    skillApi
      .list()
      .then((res) => setSkills(res.items))
      .catch(() => setSkills([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered =
    filter === "all" ? skills : skills.filter((s) => s.category === filter);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
      <div className="animate-spin h-8 w-8 rounded-full border-2 border-brand-500 border-t-transparent" />
    </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-ink-800">Skill 工具箱</h1>
        <p className="text-sm text-ink-500 mt-1">
          6 个项目专用 Skill，覆盖 API 构建、前端页面、数据爬虫、社区内容、种子数据和考研顾问
        </p>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {(["all", "builder", "advisor", "generator"] as const).map((cat) => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              filter === cat
                ? "bg-brand-500 text-white"
                : "bg-ink-100 text-ink-600 hover:bg-ink-200"
            }`}
          >
            {cat === "all" ? "全部" : CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {/* Skill Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((skill) => (
          <div
            key={skill.name}
            className="rounded-xl border border-ink-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold text-ink-800">
                {skill.display_name}
              </h3>
              <span
                className={`px-2 py-0.5 text-xs font-medium rounded-full border ${CATEGORY_COLORS[skill.category]}`}
              >
                {CATEGORY_LABELS[skill.category]}
              </span>
            </div>
            <p className="text-sm text-ink-500 mb-4">{skill.description}</p>

            {/* 触发词 */}
            <div className="mb-3">
              <p className="text-xs font-medium text-ink-400 mb-1.5">触发词</p>
              <div className="flex flex-wrap gap-1.5">
                {skill.trigger_words.map((w) => (
                  <span
                    key={w}
                    className="px-2 py-0.5 text-xs bg-ink-100 text-ink-600 rounded"
                  >
                    {w}
                  </span>
                ))}
              </div>
            </div>

            {/* 能力 */}
            <div className="mb-3">
              <p className="text-xs font-medium text-ink-400 mb-1.5">核心能力</p>
              <ul className="space-y-1">
                {skill.capabilities.map((c, i) => (
                  <li
                    key={`${c}-${i}`}
                    className="text-xs text-ink-600 flex items-start gap-1.5"
                  >
                    <span className="text-emerald-500 mt-0.5">+</span>
                    {c}
                  </li>
                ))}
              </ul>
            </div>

            {/* 局限 */}
            <div className="mb-3">
              <p className="text-xs font-medium text-ink-400 mb-1.5">能力边界</p>
              <ul className="space-y-1">
                {skill.limitations.map((l, i) => (
                  <li
                    key={`${l}-${i}`}
                    className="text-xs text-ink-500 flex items-start gap-1.5"
                  >
                    <span className="text-amber-500 mt-0.5">!</span>
                    {l}
                  </li>
                ))}
              </ul>
            </div>

            {/* 使用场景 */}
            <div>
              <p className="text-xs font-medium text-ink-400 mb-1.5">使用场景</p>
              <ul className="space-y-1">
                {skill.use_cases.map((u, i) => (
                  <li
                    key={`${u}-${i}`}
                    className="text-xs text-ink-600 flex items-start gap-1.5"
                  >
                    <span className="text-blue-500 mt-0.5">*</span>
                    {u}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>

      {/* Stats */}
      <div className="bg-ink-50 rounded-lg p-4">
        <p className="text-sm text-ink-600">
          共 <span className="font-semibold text-ink-800">{skills.length}</span>{" "}
          个 Skill 已就绪 |{" "}
          {skills.filter((s) => s.category === "builder").length} 个构建器 |{" "}
          {skills.filter((s) => s.category === "advisor").length} 个顾问 |{" "}
          {skills.filter((s) => s.category === "generator").length} 个生成器
        </p>
      </div>
    </div>
  );
}
