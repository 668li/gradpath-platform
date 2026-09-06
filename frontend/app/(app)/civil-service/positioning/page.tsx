"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Target, ArrowLeft, Loader2, GraduationCap } from "lucide-react";
import { civilServiceIntelApi, careerProfileApi } from "@/lib/api";
import { Button, Field, Input, Select, Textarea } from "@/components/ui/form-controls";
import { LoadingState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import type { CivilServicePositioningCreateRequest } from "@/types";

const EDUCATION_LEVELS = [
  { value: "bachelor", label: "本科" },
  { value: "master", label: "硕士" },
  { value: "phd", label: "博士" },
  { value: "high_school", label: "高中/中专" },
  { value: "other", label: "其他" },
];

const SCHOOL_TIERS = [
  { value: "985", label: "985" },
  { value: "211", label: "211（非985）" },
  { value: "双非", label: "双非" },
  { value: "海外", label: "海外高校" },
  { value: "其他", label: "其他" },
];

const TARGET_TYPES = [
  { value: "central", label: "国考（中央机关）" },
  { value: "provincial", label: "省考" },
  { value: "xuandiao", label: "选调生" },
  { value: "institution", label: "事业单位" },
  { value: "", label: "都可以" },
];

function PositioningFormPage() {
  const router = useRouter();
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<CivilServicePositioningCreateRequest>({
    education_level: "bachelor",
    school_tier: "",
    major: "",
    is_party_member: false,
    student_leader: false,
    has_honors: false,
    is_fresh_graduate: true,
    target_region: "",
    target_type: "",
    family_background: "",
    other_info: "",
  });

  // 用职业画像预填，减少重复输入
  useEffect(() => {
    careerProfileApi
      .get()
      .then((p) => {
        if (!p) return;
        setForm((f) => ({
          ...f,
          education_level: p.education_level || f.education_level,
          school_tier: p.school_tier || f.school_tier,
          major: p.major || f.major,
        }));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const set = <K extends keyof CivilServicePositioningCreateRequest>(
    key: K,
    value: CivilServicePositioningCreateRequest[K],
  ) => setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await civilServiceIntelApi.createPositioning(form);
      toast.push("定位评估完成，查看你的冲稳保岗位", "success");
      router.push("/civil-service?tab=positioning");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "评估失败，请稍后再试", "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingState />;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <Link
          href="/civil-service?tab=positioning"
          className="inline-flex items-center gap-1 text-sm text-ink-500 hover:text-brand-600"
        >
          <ArrowLeft className="h-4 w-4" /> 返回考公情报
        </Link>
        <div className="mt-2 flex items-center gap-2">
          <Target className="h-6 w-6 text-brand-600" />
          <h1 className="page-title">考公定位评估</h1>
        </div>
        <p className="mt-1 text-sm text-ink-500">
          填写你的基本条件，系统按真实职位数据与进面线评估竞争力，生成冲刺/目标/保底三档岗位建议。
        </p>
      </div>

      <div className="card space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="学历">
            <Select value={form.education_level} onChange={(e) => set("education_level", e.target.value)}>
              {EDUCATION_LEVELS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </Select>
          </Field>
          <Field label="学校层次" hint="影响选调与部分岗位报名资格">
            <Select value={form.school_tier || ""} onChange={(e) => set("school_tier", e.target.value)}>
              <option value="">请选择</option>
              {SCHOOL_TIERS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </Select>
          </Field>
          <Field label="专业">
            <Input value={form.major || ""} onChange={(e) => set("major", e.target.value)} placeholder="如：法学、计算机科学与技术" />
          </Field>
          <Field label="意向地区">
            <Input value={form.target_region || ""} onChange={(e) => set("target_region", e.target.value)} placeholder="如：广东、杭州（可留空）" />
          </Field>
          <Field label="目标类型">
            <Select value={form.target_type || ""} onChange={(e) => set("target_type", e.target.value)}>
              {TARGET_TYPES.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </Select>
          </Field>
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-ink-700">
            <input type="checkbox" checked={!!form.is_fresh_graduate} onChange={(e) => set("is_fresh_graduate", e.target.checked)} className="h-4 w-4 accent-brand-600" />
            应届毕业生
          </label>
          <label className="flex items-center gap-2 text-sm text-ink-700">
            <input type="checkbox" checked={!!form.is_party_member} onChange={(e) => set("is_party_member", e.target.checked)} className="h-4 w-4 accent-brand-600" />
            中共党员（含预备党员）
          </label>
          <label className="flex items-center gap-2 text-sm text-ink-700">
            <input type="checkbox" checked={!!form.student_leader} onChange={(e) => set("student_leader", e.target.checked)} className="h-4 w-4 accent-brand-600" />
            担任过主要学生干部
          </label>
          <label className="flex items-center gap-2 text-sm text-ink-700">
            <input type="checkbox" checked={!!form.has_honors} onChange={(e) => set("has_honors", e.target.checked)} className="h-4 w-4 accent-brand-600" />
            获得校级以上荣誉
          </label>
        </div>

        <Field label="补充信息" hint="如基层项目经历、户籍、证书等，帮助更准定位">
          <Textarea value={form.other_info || ""} onChange={(e) => set("other_info", e.target.value)} className="min-h-[80px]" placeholder="选填" />
        </Field>

        <Button onClick={handleSubmit} loading={submitting} className="w-full">
          <GraduationCap className="h-4 w-4" /> 开始评估
          {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
        </Button>
      </div>
    </div>
  );
}

export default function CivilServicePositioningPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <PositioningFormPage />
    </Suspense>
  );
}
