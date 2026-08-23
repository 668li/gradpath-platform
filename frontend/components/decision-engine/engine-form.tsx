"use client";

// frontend/components/decision-engine/engine-form.tsx
// 三路决策引擎输入表单 — 学生档案（专业/地区/学校层次/毕业年份）

import { useState } from "react";
import { Compass, Play } from "lucide-react";
import { Button, Field, Input, Select } from "@/components/ui/form-controls";
import type { DecisionEngineInput } from "@/types/path-comparison";

const SCHOOL_TIERS = [
  { value: "", label: "不限" },
  { value: "985", label: "985" },
  { value: "211", label: "211" },
  { value: "双一流", label: "双一流" },
  { value: "普通", label: "普通本科" },
];

const GRADUATION_YEARS = [2026, 2027, 2028, 2029];

interface EngineFormProps {
  loading: boolean;
  onSubmit: (input: DecisionEngineInput) => void;
  initial?: Partial<DecisionEngineInput>;
}

export function EngineForm({ loading, onSubmit, initial }: EngineFormProps) {
  const [major, setMajor] = useState(initial?.major ?? "");
  const [region, setRegion] = useState(initial?.region ?? "");
  const [schoolTier, setSchoolTier] = useState(initial?.school_tier ?? "");
  const [graduationYear, setGraduationYear] = useState(
    initial?.graduation_year?.toString() ?? "",
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!major.trim()) return;
    onSubmit({
      major: major.trim(),
      region: region.trim() || undefined,
      school_tier: schoolTier || undefined,
      graduation_year: graduationYear ? Number(graduationYear) : undefined,
    });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm"
    >
      <div className="mb-4 flex items-center gap-2">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-white">
          <Compass className="h-4 w-4" />
        </span>
        <div>
          <h2 className="text-base font-semibold text-ink-900">我的档案</h2>
          <p className="text-xs text-ink-500">
            输入你的基本情况，引擎会用现有数据实时对比考研 / 考公 / 就业三条路
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Field label="专业" required hint="如：计算机 / 机械工程 / 会计学">
          <Input
            value={major}
            onChange={(e) => setMajor(e.target.value)}
            placeholder="输入专业关键词"
            disabled={loading}
          />
        </Field>
        <Field label="地区" hint="如：广东 / 深圳（考公路按省份匹配）">
          <Input
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            placeholder="选填"
            disabled={loading}
          />
        </Field>
        <Field label="学校层次" hint="用于考研难度与就业参考">
          <Select
            value={schoolTier}
            onChange={(e) => setSchoolTier(e.target.value)}
            disabled={loading}
          >
            {SCHOOL_TIERS.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </Select>
        </Field>
        <Field label="毕业年份" hint="考公按应届筛选参考">
          <Select
            value={graduationYear}
            onChange={(e) => setGraduationYear(e.target.value)}
            disabled={loading}
          >
            <option value="">默认 2026</option>
            {GRADUATION_YEARS.map((y) => (
              <option key={y} value={y}>{y} 届</option>
            ))}
          </Select>
        </Field>
      </div>

      <div className="mt-4 flex items-center justify-between">
        <p className="text-xs text-ink-400">
          每个数字都可展开查看来源；数据覆盖有限时如实标注，不编造
        </p>
        <Button type="submit" loading={loading} disabled={!major.trim()}>
          <Play className="h-4 w-4" />
          {loading ? "对比中…" : "生成三路对比"}
        </Button>
      </div>
    </form>
  );
}
