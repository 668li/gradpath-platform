"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Plus, Trash2, ShieldCheck, Send } from "lucide-react";
import { failureCaseApi } from "@/lib/api";
import {
  type FailureCasePathType,
  type FailureCaseStage,
} from "@/types/failure-case";
import {
  Button,
  Field,
  Input,
  Select,
  Textarea,
  FieldError,
} from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";

const AUTHOR_ROLES = [
  { value: "在校生", label: "在校生" },
  { value: "毕业生", label: "毕业生" },
  { value: "工作3年内", label: "工作3年内" },
  { value: "工作3年以上", label: "工作3年以上" },
];

const PATH_OPTIONS: { value: FailureCasePathType; label: string }[] = [
  { value: "kaoyan", label: "考研" },
  { value: "civil_service", label: "考公" },
  { value: "employment", label: "求职" },
  { value: "study_abroad", label: "留学" },
];

const STAGE_OPTIONS: { value: FailureCaseStage; label: string }[] = [
  { value: "preparation", label: "备考阶段" },
  { value: "interview", label: "面试/复试阶段" },
  { value: "final_year1", label: "毕业第一年" },
  { value: "year2_plus", label: "毕业两年+" },
];

export default function NewFailureCasePage() {
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  const [authChecked, setAuthChecked] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Form state
  const [authorRole, setAuthorRole] = useState("");
  const [pathType, setPathType] = useState<FailureCasePathType>("kaoyan");
  const [stage, setStage] = useState<FailureCaseStage>("preparation");
  const [title, setTitle] = useState("");
  const [story, setStory] = useState("");
  const [lessons, setLessons] = useState<string[]>(["", "", ""]);
  const [regrets, setRegrets] = useState<string[]>(["", ""]);
  const [whatWouldIDo, setWhatWouldIDo] = useState("");

  useEffect(() => {
    if (!user) {
      fetchUser().then((u) => {
        setAuthChecked(true);
        if (!u) router.replace("/login");
      });
    } else {
      setAuthChecked(true);
    }
  }, [user, fetchUser, router]);

  const updateLesson = (idx: number, value: string) => {
    setLessons((prev) => prev.map((l, i) => (i === idx ? value : l)));
  };
  const addLesson = () => {
    if (lessons.length < 5) setLessons((prev) => [...prev, ""]);
  };
  const removeLesson = (idx: number) => {
    if (lessons.length > 1) {
      setLessons((prev) => prev.filter((_, i) => i !== idx));
    }
  };

  const updateRegret = (idx: number, value: string) => {
    setRegrets((prev) => prev.map((r, i) => (i === idx ? value : r)));
  };
  const addRegret = () => {
    if (regrets.length < 3) setRegrets((prev) => [...prev, ""]);
  };
  const removeRegret = (idx: number) => {
    if (regrets.length > 1) {
      setRegrets((prev) => prev.filter((_, i) => i !== idx));
    }
  };

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    if (!authorRole) e.authorRole = "请选择你的身份";
    if (!title.trim()) e.title = "请输入标题";
    if (title.length > 200) e.title = "标题不能超过 200 字";
    if (!story.trim()) e.story = "请分享你的故事";
    if (story.length < 100) e.story = "故事太短，请至少写 100 字";
    if (story.length > 20000) e.story = "故事不能超过 20000 字";
    const validLessons = lessons.filter((l) => l.trim());
    if (validLessons.length < 3) e.lessons = "请至少提炼 3 条教训";
    const validRegrets = regrets.filter((r) => r.trim());
    if (validRegrets.length < 2) e.regrets = "请至少写 2 条后悔的事";
    if (!whatWouldIDo.trim()) e.whatWouldIDo = "请填写\u201c如果重来\u201d的建议";
    if (whatWouldIDo.length > 10000) e.whatWouldIDo = "建议不能超过 10000 字";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    try {
      const payload = {
        author_role: authorRole,
        path_type: pathType,
        stage: stage,
        title: title.trim(),
        story: story.trim(),
        lessons: lessons.filter((l) => l.trim()),
        regrets: regrets.filter((r) => r.trim()),
        what_would_i_do: whatWouldIDo.trim(),
      };
      await failureCaseApi.create(payload);
      toast.success("分享成功！案例将在审核后公开。");
      router.push("/failure-cases");
    } catch {
      toast.error("提交失败，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  };

  if (!authChecked) {
    return (
      <div className="min-h-screen bg-paper-50 flex items-center justify-center">
        <span className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-paper-300 border-t-brand-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Back link */}
        <Link
          href="/failure-cases"
          className="inline-flex items-center gap-1.5 text-sm text-ink-400 hover:text-ink-700 transition-colors mb-6"
        >
          <ArrowLeft className="h-4 w-4" />
          返回案例库
        </Link>

        {/* Header */}
        <div className="mb-6">
          <h1 className="font-display text-2xl font-bold text-ink-800 mb-2">
            分享我的失败经历
          </h1>
          <p className="text-sm text-ink-500 leading-relaxed">
            你的分享将帮助后来人避开同样的坑。真实、具体、有反思——这才是有价值的失败叙事。
          </p>
        </div>

        {/* Anonymity Notice */}
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-brand-200 bg-brand-50 px-4 py-3">
          <ShieldCheck className="h-5 w-5 flex-shrink-0 text-brand-600 mt-0.5" strokeWidth={1.8} />
          <div>
            <p className="text-sm font-medium text-brand-800">匿名保护</p>
            <p className="text-xs text-brand-700 mt-1 leading-relaxed">
              你的分享将以匿名方式存储，不会关联你的账户信息。系统只记录你选择的身份标签（如"在校生"），
              不记录任何可识别你身份的信息。
            </p>
          </div>
        </div>

        {/* Form */}
        <div className="space-y-6 rounded-xl border border-paper-300 bg-white p-6">
          {/* Author Role */}
          <Field label="你的身份" required>
            <Select
              value={authorRole}
              onChange={(e) => setAuthorRole(e.target.value)}
            >
              <option value="">请选择…</option>
              {AUTHOR_ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </Select>
            <FieldError message={errors.authorRole} />
          </Field>

          {/* Path + Stage */}
          <div className="grid grid-cols-2 gap-4">
            <Field label="路径" required>
              <Select
                value={pathType}
                onChange={(e) =>
                  setPathType(e.target.value as FailureCasePathType)
                }
              >
                {PATH_OPTIONS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="阶段" required>
              <Select
                value={stage}
                onChange={(e) =>
                  setStage(e.target.value as FailureCaseStage)
                }
              >
                {STAGE_OPTIONS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          {/* Title */}
          <Field label="标题" required hint="一句话概括你的失败经历">
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={`例：考研计算机初试差3分，我用一年时间换了一个\u201c如果当初\u201d`}
              maxLength={200}
            />
            <FieldError message={errors.title} />
          </Field>

          {/* Story */}
          <Field
            label="我的故事"
            required
            hint="第一人称叙事，800-2000 字。请写清楚：发生了什么、为什么失败、具体细节。"
          >
            <Textarea
              value={story}
              onChange={(e) => setStory(e.target.value)}
              placeholder="我是XX专业，今年考XX学校……"
              className="min-h-[240px]"
              maxLength={20000}
            />
            <div className="flex items-center justify-between mt-1">
              <FieldError message={errors.story} />
              <span className="text-xs text-ink-400">{story.length} / 20000</span>
            </div>
          </Field>

          {/* Lessons */}
          <Field
            label="教训提炼"
            required
            hint="3-5 条具体教训，每条一个核心观点"
          >
            <div className="space-y-2">
              {lessons.map((lesson, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <span className="mt-2 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-700">
                    {idx + 1}
                  </span>
                  <Input
                    value={lesson}
                    onChange={(e) => updateLesson(idx, e.target.value)}
                    placeholder={`教训 ${idx + 1}`}
                  />
                  {lessons.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeLesson(idx)}
                      className="mt-1.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-ink-400 hover:bg-red-50 hover:text-red-500 transition-colors"
                      aria-label="删除"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            {lessons.length < 5 && (
              <button
                type="button"
                onClick={addLesson}
                className="mt-2 inline-flex items-center gap-1 text-sm text-brand-600 hover:text-brand-700 font-medium"
              >
                <Plus className="h-4 w-4" />
                添加教训
              </button>
            )}
            <FieldError message={errors.lessons} />
          </Field>

          {/* Regrets */}
          <Field label="后悔的事" required hint="2-3 条，写下你最遗憾的决定">
            <div className="space-y-2">
              {regrets.map((regret, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <span className="mt-2 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-red-100 text-xs font-bold text-red-700">
                    {idx + 1}
                  </span>
                  <Input
                    value={regret}
                    onChange={(e) => updateRegret(idx, e.target.value)}
                    placeholder={`后悔的事 ${idx + 1}`}
                  />
                  {regrets.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeRegret(idx)}
                      className="mt-1.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-ink-400 hover:bg-red-50 hover:text-red-500 transition-colors"
                      aria-label="删除"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            {regrets.length < 3 && (
              <button
                type="button"
                onClick={addRegret}
                className="mt-2 inline-flex items-center gap-1 text-sm text-brand-600 hover:text-brand-700 font-medium"
              >
                <Plus className="h-4 w-4" />
                添加后悔的事
              </button>
            )}
            <FieldError message={errors.regrets} />
          </Field>

          {/* What would I do */}
          <Field
            label="如果重来我会这样做"
            required
            hint="给后来人的具体建议，100-500 字"
          >
            <Textarea
              value={whatWouldIDo}
              onChange={(e) => setWhatWouldIDo(e.target.value)}
              placeholder="如果重来，我会……"
              className="min-h-[120px]"
              maxLength={10000}
            />
            <FieldError message={errors.whatWouldIDo} />
          </Field>

          {/* Submit */}
          <div className="flex items-center justify-end gap-3 pt-2 border-t border-paper-200">
            <Link href="/failure-cases">
              <Button variant="ghost" type="button">
                取消
              </Button>
            </Link>
            <Button onClick={handleSubmit} loading={submitting}>
              <Send className="h-4 w-4" />
              提交分享
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
