"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Eye, Pencil, Save } from "lucide-react";
import { knowledgeApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Markdown } from "@/components/ui/markdown";
import { Button, Field, Input, Select } from "@/components/ui/form-controls";
import { FieldError } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { knowledgeSchema } from "@/lib/validations";
import type { KnowledgeArticle } from "@/types";

const CATEGORIES = [
  { value: "行业指南", label: "行业指南" },
  { value: "岗位要求", label: "岗位要求" },
  { value: "技能图谱", label: "技能图谱" },
  { value: "面试攻略", label: "面试攻略" },
  { value: "薪资参考", label: "薪资参考" },
  { value: "升学路径", label: "升学路径" },
];

interface Props {
  article?: KnowledgeArticle | null;
  loading?: boolean;
}

export function KnowledgeEditor({ article, loading }: Props) {
  const router = useRouter();
  const toast = useToast();

  const [category, setCategory] = useState(article?.category ?? "");
  const [title, setTitle] = useState(article?.title ?? "");
  const [content, setContent] = useState(article?.content ?? "");
  const [tagsInput, setTagsInput] = useState(
    article?.tags?.join(", ") ?? "",
  );
  const [source, setSource] = useState(article?.source ?? "");
  const [isPublished, setIsPublished] = useState(article?.is_published ?? true);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [mobileView, setMobileView] = useState<"edit" | "preview">("edit");

  const isEdit = !!article;

  const handleSave = async () => {
    const tags = tagsInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const data = {
      category,
      title,
      content,
      tags,
      source: source || null,
      is_published: isPublished,
    };

    const parsed = knowledgeSchema.safeParse(data);
    if (!parsed.success) {
      const fieldErrors: Record<string, string> = {};
      for (const err of parsed.error.issues) {
        if (err.path[0] && !fieldErrors[err.path[0] as string]) {
          fieldErrors[err.path[0] as string] = err.message;
        }
      }
      setErrors(fieldErrors);
      return;
    }

    setErrors({});
    setSaving(true);
    try {
      if (isEdit && article) {
        await knowledgeApi.update(article.id, data);
        toast.push("文章已更新", "success");
      } else {
        await knowledgeApi.create(data);
        toast.push("文章已创建", "success");
      }
      router.push("/knowledge");
    } catch {
      toast.push(isEdit ? "更新失败" : "创建失败", "error");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-slate-400">
        <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-brand-500" />
        <span className="ml-2 text-sm">加载中…</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 顶部导航 */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => router.push("/knowledge")}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700"
        >
          <ArrowLeft className="h-4 w-4" />
          返回列表
        </button>
        <h1 className="text-lg font-semibold text-slate-800">
          {isEdit ? "编辑文章" : "新建文章"}
        </h1>
        <Button onClick={handleSave} loading={saving} size="sm">
          <Save className="h-4 w-4" />
          保存
        </Button>
      </div>

      {/* 元数据表单 */}
      <div className="card grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="分类" required>
          <Select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            aria-invalid={!!errors.category}
          >
            <option value="">请选择分类</option>
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </Select>
          <FieldError message={errors.category} />
        </Field>

        <Field label="标题" required>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="文章标题"
            maxLength={200}
            aria-invalid={!!errors.title}
          />
          <FieldError message={errors.title} />
        </Field>

        <Field label="标签" hint="逗号分隔，如：后端, Java, 大厂">
          <Input
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            placeholder="标签1, 标签2, 标签3"
          />
        </Field>

        <Field label="来源">
          <Input
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="数据来源（可选）"
            maxLength={200}
          />
        </Field>

        <div className="flex items-center gap-3">
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={isPublished}
              onChange={(e) => setIsPublished(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 accent-brand-600"
            />
            <span className="text-sm text-slate-700">发布</span>
          </label>
          <span className="text-xs text-slate-400">
            未发布的文章不会被 AI 管家检索
          </span>
        </div>
      </div>

      {/* 移动端切换按钮 */}
      <div className="flex gap-2 lg:hidden">
        <button
          onClick={() => setMobileView("edit")}
          className={cn(
            "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
            mobileView === "edit"
              ? "bg-brand-600 text-white"
              : "bg-slate-100 text-slate-600",
          )}
        >
          <Pencil className="h-3.5 w-3.5" />
          编辑
        </button>
        <button
          onClick={() => setMobileView("preview")}
          className={cn(
            "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
            mobileView === "preview"
              ? "bg-brand-600 text-white"
              : "bg-slate-100 text-slate-600",
          )}
        >
          <Eye className="h-3.5 w-3.5" />
          预览
        </button>
      </div>

      {/* Markdown 编辑器 + 预览 */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* 编辑区 */}
        <div className={cn(mobileView === "preview" && "hidden lg:block")}>
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-sm font-medium text-slate-700">内容</span>
            <span className="text-xs text-slate-400">{content.length} 字</span>
          </div>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="支持 Markdown 格式…"
            className="min-h-[400px] w-full resize-y rounded-lg border border-slate-300 bg-white px-4 py-3 font-mono text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
            aria-invalid={!!errors.content}
          />
          <FieldError message={errors.content} />
        </div>

        {/* 预览区 */}
        <div className={cn(mobileView === "edit" && "hidden lg:block")}>
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-sm font-medium text-slate-700">预览</span>
          </div>
          <div className="min-h-[400px] overflow-y-auto rounded-lg border border-slate-200 bg-white px-4 py-3">
            {content.trim() ? (
              <Markdown content={content} />
            ) : (
              <p className="text-sm text-slate-400">开始输入内容后这里会显示预览…</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
