"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { UserCircle, GraduationCap, Target, Star, Save, Download, FileText, FileSpreadsheet, ClipboardList, Library, Award, Bell, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { careerProfileApi, exportV2Api, useApi, useInvalidate } from "@/lib/api";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button, Field, Input, Select, Textarea } from "@/components/ui/form-controls";
import { FieldError } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type { CareerProfile, CareerProfileCreate } from "@/types";

const EDUCATION_LEVELS = [
  { value: "", label: "请选择" },
  { value: "high_school", label: "高中" },
  { value: "bachelor", label: "本科" },
  { value: "master", label: "硕士" },
  { value: "phd", label: "博士" },
  { value: "other", label: "其他" },
];

const SCHOOL_TIERS = [
  { value: "", label: "请选择" },
  { value: "985", label: "985" },
  { value: "211", label: "211" },
  { value: "双非", label: "双非" },
  { value: "海外", label: "海外" },
  { value: "其他", label: "其他" },
];

const SKILL_LABELS: { key: keyof Pick<CareerProfile, "technical_skill" | "communication_skill" | "leadership_skill" | "creativity_skill">; label: string }[] = [
  { key: "technical_skill", label: "技术能力" },
  { key: "communication_skill", label: "沟通能力" },
  { key: "leadership_skill", label: "领导力" },
  { key: "creativity_skill", label: "创造力" },
];

type ProfileTab = "profile" | "decisions" | "learning-resources" | "achievements" | "notifications" | "search";

const profileTabs: { id: ProfileTab; label: string; icon: typeof UserCircle; href: string; color: string }[] = [
  { id: "profile", label: "职业画像", icon: UserCircle, href: "/profile", color: "text-brand-500" },
  { id: "decisions", label: "决策记录", icon: ClipboardList, href: "/decisions", color: "text-blue-500" },
  { id: "learning-resources", label: "学习资源", icon: Library, href: "/learning-resources", color: "text-green-500" },
  { id: "achievements", label: "成就徽章", icon: Award, href: "/achievements", color: "text-amber-500" },
  { id: "notifications", label: "通知", icon: Bell, href: "/notifications", color: "text-red-500" },
  { id: "search", label: "搜索", icon: Search, href: "/search", color: "text-purple-500" },
];

export default function ProfilePage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <ProfilePageContent />
    </Suspense>
  );
}

function ProfilePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = (searchParams.get("tab") as ProfileTab) || "profile";
  const toast = useToast();
  const invalidate = useInvalidate();

  // SWR 拉取画像
  const { data: profile, error: profileError, isLoading: loading } = useApi<CareerProfile | null>(
    "/api/career-profile",
  );

  // 表单状态
  const [saving, setSaving] = useState(false);
  const [educationLevel, setEducationLevel] = useState("");
  const [major, setMajor] = useState("");
  const [schoolName, setSchoolName] = useState("");
  const [schoolTier, setSchoolTier] = useState("");
  const [graduationYear, setGraduationYear] = useState("");
  const [targetDirection, setTargetDirection] = useState("");
  const [targetIndustry, setTargetIndustry] = useState("");
  const [technicalSkill, setTechnicalSkill] = useState(3);
  const [communicationSkill, setCommunicationSkill] = useState(3);
  const [leadershipSkill, setLeadershipSkill] = useState(3);
  const [creativitySkill, setCreativitySkill] = useState(3);
  const [selfIntroduction, setSelfIntroduction] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [exporting, setExporting] = useState<"profile" | "csv" | "json" | null>(null);

  // SWR 数据加载后同步表单字段
  useEffect(() => {
    if (profile) {
      setEducationLevel(profile.education_level ?? "");
      setMajor(profile.major ?? "");
      setSchoolName(profile.school_name ?? "");
      setSchoolTier(profile.school_tier ?? "");
      setGraduationYear(profile.graduation_year?.toString() ?? "");
      setTargetDirection(profile.target_direction ?? "");
      setTargetIndustry(profile.target_industry ?? "");
      // 修复 P2 bug: skill 字段可能为 null，导致 range 输入失控
      setTechnicalSkill(profile.technical_skill ?? 3);
      setCommunicationSkill(profile.communication_skill ?? 3);
      setLeadershipSkill(profile.leadership_skill ?? 3);
      setCreativitySkill(profile.creativity_skill ?? 3);
      setSelfIntroduction(profile.self_introduction ?? "");
    }
  }, [profile]);

  useEffect(() => {
    if (profileError) toast.push("加载画像失败", "error");
  }, [profileError, toast]);

  const handleSave = async () => {
    const data: CareerProfileCreate = {
      education_level: educationLevel || null,
      major: major || null,
      school_name: schoolName || null,
      school_tier: schoolTier || null,
      graduation_year: graduationYear ? parseInt(graduationYear) : null,
      target_direction: targetDirection || null,
      target_industry: targetIndustry || null,
      technical_skill: technicalSkill,
      communication_skill: communicationSkill,
      leadership_skill: leadershipSkill,
      creativity_skill: creativitySkill,
      self_introduction: selfIntroduction || null,
    };

    setSaving(true);
    setErrors({});
    try {
      if (profile) {
        await careerProfileApi.update(data);
        toast.push("画像已更新", "success");
      } else {
        await careerProfileApi.create(data);
        toast.push("画像已创建", "success");
      }
      // 让 SWR 重新拉取最新画像
      await invalidate("/api/career-profile");
    } catch {
      toast.push("保存失败", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleExportProfile = async () => {
    setExporting("profile");
    try {
      await exportV2Api.profileReport();
      toast.push("个人报告导出成功", "success");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "导出失败", "error");
    } finally {
      setExporting(null);
    }
  };

  const handleExportData = async (format: "csv" | "json") => {
    setExporting(format);
    try {
      await exportV2Api.dataExport(format);
      toast.push(`${format === "csv" ? "CSV" : "JSON"} 数据导出成功`, "success");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "导出失败", "error");
    } finally {
      setExporting(null);
    }
  };

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-6 max-w-3xl animate-fade-in">
      {/* Tab 切换 */}
      <div className="flex gap-2 border-b border-paper-200 max-w-3xl">
        {profileTabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => {
                if (tab.id === "profile") {
                  router.push("/profile");
                } else {
                  router.push(tab.href);
                }
              }}
              className={cn(
                "flex items-center gap-2 px-4 py-3 font-medium transition-all border-b-2 text-sm",
                activeTab === tab.id
                  ? `${tab.color} border-current`
                  : "text-ink-400 border-transparent hover:text-ink-600"
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {activeTab !== "profile" && (
        <div className="flex items-center justify-center py-20 text-ink-400">
          <p>页面加载中…</p>
        </div>
      )}

      {activeTab === "profile" && (
      <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="page-title">职业画像</h1>
        <p className="text-sm text-ink-400 mt-1.5">
          完善你的教育背景、目标方向和自我评估，AI 管家将据此提供个性化建议
        </p>
      </div>

      {/* 教育背景 */}
      <div className="card space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <GraduationCap className="h-5 w-5 text-brand-600" />
          <h2 className="font-display font-semibold text-ink-800">教育背景</h2>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="学历">
            <Select
              value={educationLevel}
              onChange={(e) => setEducationLevel(e.target.value)}
            >
              {EDUCATION_LEVELS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </Select>
          </Field>
          <Field label="专业">
            <Input
              value={major}
              onChange={(e) => setMajor(e.target.value)}
              placeholder="如：计算机科学与技术"
            />
          </Field>
          <Field label="学校名称">
            <Input
              value={schoolName}
              onChange={(e) => setSchoolName(e.target.value)}
              placeholder="如：清华大学"
            />
          </Field>
          <Field label="学校层次">
            <Select
              value={schoolTier}
              onChange={(e) => setSchoolTier(e.target.value)}
            >
              {SCHOOL_TIERS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </Select>
          </Field>
          <Field label="毕业年份">
            <Input
              type="number"
              value={graduationYear}
              onChange={(e) => setGraduationYear(e.target.value)}
              placeholder="如：2027"
              min="2000"
              max="2099"
            />
          </Field>
        </div>
      </div>

      {/* 目标方向 */}
      <div className="card space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <Target className="h-5 w-5 text-brand-600" />
          <h2 className="font-display font-semibold text-ink-800">目标方向</h2>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="目标方向" hint="如：大厂后端开发、产品经理、考研">
            <Input
              value={targetDirection}
              onChange={(e) => setTargetDirection(e.target.value)}
              placeholder="你想去的方向"
            />
          </Field>
          <Field label="目标行业" hint="如：互联网、金融科技、AI">
            <Input
              value={targetIndustry}
              onChange={(e) => setTargetIndustry(e.target.value)}
              placeholder="你感兴趣的行业"
            />
          </Field>
        </div>
      </div>

      {/* 自我评估 */}
      <div className="card space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <Star className="h-5 w-5 text-brand-600" />
          <h2 className="font-display font-semibold text-ink-800">自我评估</h2>
        </div>
        <p className="text-xs text-ink-400">拖动滑块评估你的能力水平（1-5 分）</p>
        <div className="space-y-3">
          {SKILL_LABELS.map(({ key, label }) => {
            const value = key === "technical_skill" ? technicalSkill
              : key === "communication_skill" ? communicationSkill
              : key === "leadership_skill" ? leadershipSkill
              : creativitySkill;
            const setter = key === "technical_skill" ? setTechnicalSkill
              : key === "communication_skill" ? setCommunicationSkill
              : key === "leadership_skill" ? setLeadershipSkill
              : setCreativitySkill;
            return (
              <SkillSlider key={key} label={label} value={value} onChange={setter} />
            );
          })}
        </div>
      </div>

      {/* 自我介绍 */}
      <div className="card space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <UserCircle className="h-5 w-5 text-brand-600" />
          <h2 className="font-display font-semibold text-ink-800">自我介绍</h2>
        </div>
        <Textarea
          value={selfIntroduction}
          onChange={(e) => setSelfIntroduction(e.target.value)}
          placeholder="简单介绍你的背景、经历和目标，帮助 AI 更好地理解你…"
          className="min-h-[120px]"
        />
      </div>

      {/* 保存按钮 */}
      <div className="flex justify-end gap-3">
        <Button onClick={handleSave} loading={saving} size="md">
          <Save className="h-4 w-4" />
          {profile ? "保存修改" : "创建画像"}
        </Button>
      </div>

      {/* 导出 */}
      <div className="card space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <Download className="h-5 w-5 text-brand-600" />
          <h2 className="font-display font-semibold text-ink-800">数据导出</h2>
        </div>
        <p className="text-xs text-ink-400">导出你的个人数据和报告</p>
        <div className="flex flex-wrap gap-3">
          <Button
            onClick={handleExportProfile}
            loading={exporting === "profile"}
            size="md"
            variant="secondary"
          >
            <FileText className="h-4 w-4" />
            导出个人报告（PDF）
          </Button>
          <Button
            onClick={() => handleExportData("csv")}
            loading={exporting === "csv"}
            size="md"
            variant="secondary"
          >
            <FileSpreadsheet className="h-4 w-4" />
            导出数据（CSV）
          </Button>
          <Button
            onClick={() => handleExportData("json")}
            loading={exporting === "json"}
            size="md"
            variant="secondary"
          >
            <FileSpreadsheet className="h-4 w-4" />
            导出数据（JSON）
          </Button>
        </div>
      </div>
      </div>
      )}
    </div>
  );
}

function SkillSlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-medium text-ink-700">{label}</span>
        <span className={cn(
          "flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold",
          value >= 4 ? "bg-brand-100 text-brand-700" : "bg-paper-200 text-ink-500",
        )}>
          {value}
        </span>
      </div>
      <input
        type="range"
        min={1}
        max={5}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="w-full h-2 bg-paper-200 rounded-full appearance-none cursor-pointer accent-brand-600"
      />
      <div className="flex justify-between mt-0.5 text-[10px] text-ink-300">
        <span>初学</span>
        <span>入门</span>
        <span>熟悉</span>
        <span>熟练</span>
        <span>精通</span>
      </div>
    </div>
  );
}
