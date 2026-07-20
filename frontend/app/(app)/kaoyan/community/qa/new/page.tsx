"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Save } from "lucide-react";
import { kaoyanCommunityApi } from "@/lib/api";
import { Button, Field, Input, Textarea } from "@/components/ui/form-controls";
import { FieldError } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";

export default function NewQuestionPage() {
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  const [authChecked, setAuthChecked] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tagsInput, setTagsInput] = useState("");
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
    if (!title.trim()) fieldErrors.title = "请输入问题标题";
    if (!content.trim()) fieldErrors.content = "请输入问题详情";
    if (Object.keys(fieldErrors).length > 0) {
      setErrors(fieldErrors);
      return;
    }

    setErrors({});
    setSubmitting(true);
    try {
      const question = await kaoyanCommunityApi.qa.create({
        title: title.trim(),
        content: content.trim(),
        tags,
      });
      toast.push("问题已提交，审核通过后将展示", "success");
      router.push(`/kaoyan/community/qa/${question.id}`);
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
          <h1 className="text-lg font-semibold text-ink-900">提问题</h1>
          <Button onClick={handleSubmit} loading={submitting} size="sm">
            <Save className="h-4 w-4" />
            发布
          </Button>
        </div>

        <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm space-y-5">
          <Field label="问题标题" required>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="一句话描述你的问题"
              maxLength={200}
              aria-invalid={!!errors.title}
            />
            <FieldError message={errors.title} />
          </Field>

          <Field label="标签" hint="逗号分隔，如：数学, 择校, 复试">
            <Input
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              placeholder="标签1, 标签2"
            />
          </Field>

          <Field label="问题详情" required>
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="详细描述你的问题，背景信息越全越容易获得高质量回答…"
              className="min-h-[300px]"
              aria-invalid={!!errors.content}
            />
            <FieldError message={errors.content} />
          </Field>
        </div>
      </div>
    </div>
  );
}
