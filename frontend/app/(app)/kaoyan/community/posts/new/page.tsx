"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Save } from "lucide-react";
import { kaoyanCommunityApi } from "@/lib/api";
import { Button, Field, Input, Select, Textarea } from "@/components/ui/form-controls";
import { FieldError } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";

const CATEGORIES = [
  { value: "general", label: "综合" },
  { value: "初试", label: "初试" },
  { value: "复试", label: "复试" },
  { value: "调剂", label: "调剂" },
  { value: "择校", label: "择校" },
  { value: "复习", label: "复习" },
];

export default function NewExperiencePostPage() {
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  const [authChecked, setAuthChecked] = useState(false);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("general");
  const [tagsInput, setTagsInput] = useState("");
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

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

  const handleSubmit = async () => {
    const tags = tagsInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const fieldErrors: Record<string, string> = {};
    if (!title.trim()) fieldErrors.title = "请输入标题";
    if (!content.trim()) fieldErrors.content = "请输入正文内容";
    if (Object.keys(fieldErrors).length > 0) {
      setErrors(fieldErrors);
      return;
    }

    setErrors({});
    setSubmitting(true);
    try {
      const post = await kaoyanCommunityApi.experiencePosts.create({
        title: title.trim(),
        summary: summary.trim() || null,
        content: content.trim(),
        tags,
        category,
        is_anonymous: isAnonymous,
      });
      toast.push("经验贴已提交，审核通过后将展示", "success");
      router.push(`/kaoyan/community/posts/${post.id}`);
    } catch {
      toast.push("发布失败，请稍后重试", "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (!authChecked) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-ink-400">
        <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-paper-300 border-t-brand-500" />
        <span className="ml-2 text-sm">加载中…</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1.5 text-sm text-ink-500 hover:text-ink-700"
          >
            <ArrowLeft className="h-4 w-4" />
            返回
          </button>
          <h1 className="text-lg font-semibold text-ink-900">写经验贴</h1>
          <Button onClick={handleSubmit} loading={submitting} size="sm">
            <Save className="h-4 w-4" />
            发布
          </Button>
        </div>

        <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm space-y-5">
          <Field label="标题" required>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="一句话概括你的经验"
              maxLength={200}
              aria-invalid={!!errors.title}
            />
            <FieldError message={errors.title} />
          </Field>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="分类">
              <Select value={category} onChange={(e) => setCategory(e.target.value)}>
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </Select>
            </Field>

            <Field label="标签" hint="逗号分隔，如：408, 双非逆袭, 数学一">
              <Input
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="标签1, 标签2"
              />
            </Field>
          </div>

          <Field label="摘要" hint="可选，用于列表展示">
            <Input
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="简要介绍经验内容"
              maxLength={500}
            />
          </Field>

          <Field label="正文" required>
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="详细分享你的考研经验、时间线、避坑心得…"
              className="min-h-[300px]"
              aria-invalid={!!errors.content}
            />
            <FieldError message={errors.content} />
          </Field>

          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={isAnonymous}
              onChange={(e) => setIsAnonymous(e.target.checked)}
              className="h-4 w-4 rounded border-paper-300 accent-brand-600"
            />
            <span className="text-sm text-ink-700">匿名发布</span>
          </label>
        </div>
      </div>
    </div>
  );
}
