"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Star, Send } from "lucide-react";
import { mentorApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";
import { Button, Input, Textarea, Field } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";
import type { MentorResponse, MentorReviewCreate } from "@/types";

const RATING_DIMENSIONS = [
  { key: "rating_academic", label: "学术水平", desc: "论文产出、项目质量、学术影响力" },
  { key: "rating_guidance", label: "指导风格", desc: "指导频率、指导细致程度、学术引导" },
  { key: "rating_relationship", label: "师生关系", desc: "相处氛围、尊重程度、沟通顺畅度" },
  { key: "rating_funding", label: "科研经费", desc: "实验设备、项目资源、劳务补贴" },
  { key: "rating_workload", label: "工作强度", desc: "1=轻松自由，5=996高压" },
  { key: "rating_career", label: "毕业前景", desc: "就业去向、升学支持、校友资源" },
] as const;

export default function SubmitReviewPage() {
  const params = useParams();
  const router = useRouter();
  const toast = useToast();
  const mentorId = params.id as string;
  const user = useAuthStore((s) => s.user);

  const [mentor, setMentor] = useState<MentorResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [ratings, setRatings] = useState<Record<string, number>>({
    rating_academic: 0,
    rating_guidance: 0,
    rating_relationship: 0,
    rating_funding: 0,
    rating_workload: 0,
    rating_career: 0,
  });
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [prosText, setProsText] = useState("");
  const [consText, setConsText] = useState("");
  const [isAnonymous, setIsAnonymous] = useState(true);
  const [reviewerIdentity, setReviewerIdentity] = useState("");

  const loadMentor = useCallback(async () => {
    try {
      const data = await mentorApi.getDetail(mentorId);
      setMentor(data);
    } catch {
      toast.push("加载导师信息失败", "error");
    } finally {
      setLoading(false);
    }
  }, [mentorId, toast]);

  useEffect(() => {
    loadMentor();
  }, [loadMentor]);

  const handleRatingChange = (key: string, value: number) => {
    setRatings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    // Validation
    const emptyRatings = RATING_DIMENSIONS.filter((d) => ratings[d.key] === 0);
    if (emptyRatings.length > 0) {
      toast.push(`请完成所有评分：${emptyRatings.map((d) => d.label).join("、")}`, "error");
      return;
    }
    if (!title.trim()) {
      toast.push("请填写评价标题", "error");
      return;
    }
    if (!content.trim() || content.trim().length < 10) {
      toast.push("评价内容至少 10 个字", "error");
      return;
    }

    setSubmitting(true);
    try {
      const pros = prosText
        .split(/[,，、]/)
        .map((s) => s.trim())
        .filter(Boolean);
      const cons = consText
        .split(/[,，、]/)
        .map((s) => s.trim())
        .filter(Boolean);

      const payload: MentorReviewCreate = {
        is_anonymous: isAnonymous,
        rating_academic: ratings.rating_academic,
        rating_guidance: ratings.rating_guidance,
        rating_relationship: ratings.rating_relationship,
        rating_funding: ratings.rating_funding,
        rating_workload: ratings.rating_workload,
        rating_career: ratings.rating_career,
        title: title.trim(),
        content: content.trim(),
        pros,
        cons,
        reviewer_identity: reviewerIdentity.trim() || undefined,
      };

      await mentorApi.submitReview(mentorId, payload);
      toast.push("评价提交成功，审核通过后将展示", "success");
      router.push(`/kaoyan/mentors/${mentorId}`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "提交失败";
      toast.push(msg, "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-3xl px-4 py-6 md:px-6 md:py-8">
          <LoadingState text="加载导师信息..." />
        </div>
      </div>
    );
  }

  if (!mentor) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-3xl px-4 py-6 md:px-6 md:py-8">
          <div className="rounded-xl border border-paper-200 bg-white p-8 text-center">
            <p className="text-ink-500">导师信息不存在</p>
            <Button onClick={() => router.push("/kaoyan/mentors")} className="mt-4">
              返回列表
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-3xl px-4 py-6 md:px-6 md:py-8">
        {/* Back */}
        <button
          onClick={() => router.back()}
          className="mb-4 flex items-center gap-2 text-sm text-ink-500 hover:text-ink-700"
        >
          <ArrowLeft className="h-4 w-4" />
          返回导师详情
        </button>

        {/* Header */}
        <div className="mb-6 rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
          <h1 className="text-xl font-bold text-ink-900">评价导师</h1>
          <p className="mt-1 text-sm text-ink-500">
            {mentor.name} · {mentor.university} · {mentor.department}
          </p>
          <div className="mt-3 rounded-lg bg-amber-50 border border-amber-200 p-3">
            <p className="text-xs text-amber-700">
              请基于真实经历客观评价。评价提交后需经审核，审核通过后将公开展示。
              恶意评价将被拒绝。
            </p>
          </div>
        </div>

        {/* Ratings */}
        <div className="mb-6 rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold text-ink-800">六维评分</h2>
          <div className="space-y-4">
            {RATING_DIMENSIONS.map((dim) => (
              <div key={dim.key}>
                <div className="mb-1.5 flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-ink-700">{dim.label}</span>
                    <p className="text-xs text-ink-400">{dim.desc}</p>
                  </div>
                  <span className="text-sm font-semibold text-brand-600">
                    {ratings[dim.key] > 0 ? ratings[dim.key] : "-"}
                  </span>
                </div>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((score) => (
                    <button
                      key={score}
                      onClick={() => handleRatingChange(dim.key, score)}
                      className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-lg border transition-all",
                        ratings[dim.key] >= score
                          ? "border-brand-500 bg-brand-500 text-white"
                          : "border-paper-200 bg-white text-ink-400 hover:border-brand-300 hover:text-brand-500",
                      )}
                    >
                      <Star className="h-4 w-4" strokeWidth={2} />
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Text Review */}
        <div className="mb-6 rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold text-ink-800">文字评价</h2>
          <div className="space-y-4">
            <Field label="评价标题" required>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="一句话概括你的评价"
                maxLength={100}
              />
            </Field>
            <Field label="详细评价" required>
              <Textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="分享你的真实经历：指导风格、实验室氛围、科研压力、毕业去向等..."
                rows={6}
                maxLength={2000}
              />
              <p className="mt-1 text-xs text-ink-400">{content.length} / 2000</p>
            </Field>
            <Field label="优点（用逗号分隔）">
              <Input
                value={prosText}
                onChange={(e) => setProsText(e.target.value)}
                placeholder="如：学术能力强，指导细致，经费充足"
              />
            </Field>
            <Field label="缺点（用逗号分隔）">
              <Input
                value={consText}
                onChange={(e) => setConsText(e.target.value)}
                placeholder="如：工作强度大，沟通较少"
              />
            </Field>
          </div>
        </div>

        {/* Identity */}
        <div className="mb-6 rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold text-ink-800">身份信息</h2>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isAnonymous}
                  onChange={(e) => setIsAnonymous(e.target.checked)}
                  className="h-4 w-4 rounded border-paper-300 text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-ink-700">匿名评价</span>
              </label>
            </div>
            {!isAnonymous && (
              <Field label="你的身份">
                <Input
                  value={reviewerIdentity}
                  onChange={(e) => setReviewerIdentity(e.target.value)}
                  placeholder="如：2023级硕士生"
                />
              </Field>
            )}
            {isAnonymous && (
              <Field label="匿名身份标识（可选）">
                <Input
                  value={reviewerIdentity}
                  onChange={(e) => setReviewerIdentity(e.target.value)}
                  placeholder="如：2023级硕士、已毕业学生"
                />
                <p className="mt-1 text-xs text-ink-400">
                  不会暴露你的真实身份，仅展示你填写的标识
                </p>
              </Field>
            )}
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => router.back()}>
            取消
          </Button>
          <Button onClick={handleSubmit} loading={submitting}>
            <Send className="h-4 w-4" />
            提交评价
          </Button>
        </div>
      </div>
    </div>
  );
}
