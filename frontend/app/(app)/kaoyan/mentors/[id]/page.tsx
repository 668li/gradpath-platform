"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Star,
  BookOpen,
  Mail,
  Phone,
  ExternalLink,
  TrendingUp,
  Award,
  Users,
  ThumbsUp,
} from "lucide-react";
import { mentorApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";
import { Badge, Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type { MentorResponse, MentorReviewResponse } from "@/types";

export default function MentorDetailPage() {
  const params = useParams();
  const router = useRouter();
  const toast = useToast();
  const mentorId = params.id as string;

  const [mentor, setMentor] = useState<MentorResponse | null>(null);
  const [reviews, setReviews] = useState<MentorReviewResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewsPage, setReviewsPage] = useState(1);
  const [reviewsTotal, setReviewsTotal] = useState(0);

  const loadMentor = useCallback(async () => {
    try {
      const data = await mentorApi.getDetail(mentorId);
      setMentor(data);
    } catch {
      toast.push("加载导师信息失败", "error");
    }
  }, [mentorId, toast]);

  const loadReviews = useCallback(async () => {
    try {
      const res = await mentorApi.getReviews(mentorId, reviewsPage, 10);
      setReviews(res.items);
      setReviewsTotal(res.total);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [mentorId, reviewsPage]);

  useEffect(() => {
    loadMentor();
    loadReviews();
  }, [loadMentor, loadReviews]);

  const handleLikeReview = async (reviewId: string) => {
    try {
      await mentorApi.likeReview(mentorId, reviewId);
      toast.push("点赞成功", "success");
      loadReviews();
    } catch {
      toast.push("点赞失败", "error");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
          <LoadingState text="加载导师详情..." />
        </div>
      </div>
    );
  }

  if (!mentor) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
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

  // 修复 P1 bug: 后端字段可能为 null，预先解构出非空值，避免 .toFixed()/.map() 崩溃
  const avgRating = mentor.avg_rating ?? 0;
  const researchDirs = mentor.research_directions || [];
  const enrollmentDirs = mentor.enrollment_directions || [];
  const tags = mentor.tags || [];

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
        {/* Back Button */}
        <button
          onClick={() => router.back()}
          className="mb-4 flex items-center gap-2 text-sm text-ink-500 hover:text-ink-700"
        >
          <ArrowLeft className="h-4 w-4" />
          返回列表
        </button>

        {/* Mentor Info Card */}
        <div className="mb-6 rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
          {/* Header */}
          <div className="mb-4 flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="mb-2 flex items-center gap-3">
                <h1 className="text-xl sm:text-2xl font-bold text-ink-900">{mentor.name}</h1>
                <Badge color="purple">{mentor.title}</Badge>
                {mentor.is_verified && (
                  <Badge color="green">已认证</Badge>
                )}
              </div>
              <div className="flex items-center gap-2 text-sm text-ink-600">
                <BookOpen className="h-4 w-4 text-ink-400" />
                <span>{mentor.university}</span>
                <span className="text-ink-300">·</span>
                <span>{mentor.department}</span>
              </div>
            </div>
            <div className="text-right">
              <div className="flex items-center gap-2">
                <Star className="h-6 w-6 fill-amber-400 text-amber-400" />
                <span className="text-3xl font-bold text-ink-900">
                  {avgRating.toFixed(1)}
                </span>
              </div>
              <p className="text-sm text-ink-500">{mentor.review_count} 条评价</p>
            </div>
          </div>

          {/* Research Directions */}
          {researchDirs.length > 0 && (
            <div className="mb-4">
              <h3 className="mb-2 text-sm font-semibold text-ink-700">研究方向</h3>
              <div className="flex flex-wrap gap-2">
                {researchDirs.map((dir, i) => (
                  <Badge key={`${dir}-${i}`} color="slate">
                    {dir}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Academic Stats */}
          <div className="mb-4 grid grid-cols-2 gap-4 border-t border-paper-100 pt-4 sm:grid-cols-4">
            <div className="text-center">
              <p className="text-xs text-ink-400">论文数</p>
              <p className="text-lg font-bold text-ink-700">{mentor.paper_count}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-ink-400">项目数</p>
              <p className="text-lg font-bold text-ink-700">{mentor.project_count}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-ink-400">引用数</p>
              <p className="text-lg font-bold text-ink-700">{mentor.citation_count}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-ink-400">H-Index</p>
              <p className="text-lg font-bold text-ink-700">{mentor.h_index ?? "-"}</p>
            </div>
          </div>

          {/* Enrollment Info */}
          <div className="mb-4 border-t border-paper-100 pt-4">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-ink-400" />
              <h3 className="text-sm font-semibold text-ink-700">招生信息</h3>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-ink-500">招生状态：</span>
                <span
                  className={cn(
                    "font-medium",
                    mentor.enrollment_status === "accepting"
                      ? "text-green-600"
                      : mentor.enrollment_status === "not_accepting"
                        ? "text-red-600"
                        : "text-ink-600",
                  )}
                >
                  {mentor.enrollment_status === "accepting"
                    ? "正在招生"
                    : mentor.enrollment_status === "not_accepting"
                      ? "暂停招生"
                      : "招生状态未知"}
                </span>
              </div>
              {enrollmentDirs.length > 0 && (
                <div className="flex items-start gap-2">
                  <span className="text-ink-500 shrink-0">招生方向：</span>
                  <div className="flex flex-wrap gap-1">
                    {enrollmentDirs.map((dir, i) => (
                      <Badge key={`${dir}-${i}`} color="blue">
                        {dir}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Contact Info */}
          {(mentor.contact_email || mentor.contact_phone) && (
            <div className="border-t border-paper-100 pt-4">
              <h3 className="mb-2 text-sm font-semibold text-ink-700">联系方式</h3>
              <div className="space-y-2 text-sm">
                {mentor.contact_email && (
                  <div className="flex items-center gap-2">
                    <Mail className="h-4 w-4 text-ink-400" />
                    <a
                      href={`mailto:${mentor.contact_email}`}
                      className="text-brand-600 hover:underline"
                    >
                      {mentor.contact_email}
                    </a>
                  </div>
                )}
                {mentor.contact_phone && (
                  <div className="flex items-center gap-2">
                    <Phone className="h-4 w-4 text-ink-400" />
                    <span className="text-ink-700">{mentor.contact_phone}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Academic Links */}
          {(mentor.academic_homepage || mentor.google_scholar_url || mentor.cnki_url) && (
            <div className="mt-4 border-t border-paper-100 pt-4">
              <h3 className="mb-2 text-sm font-semibold text-ink-700">学术主页</h3>
              <div className="flex flex-wrap gap-3">
                {mentor.academic_homepage && (
                  <a
                    href={mentor.academic_homepage}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm text-brand-600 hover:underline"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    导师主页
                  </a>
                )}
                {mentor.google_scholar_url && (
                  <a
                    href={mentor.google_scholar_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm text-brand-600 hover:underline"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    Google Scholar
                  </a>
                )}
                {mentor.cnki_url && (
                  <a
                    href={mentor.cnki_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm text-brand-600 hover:underline"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    知网主页
                  </a>
                )}
              </div>
            </div>
          )}

          {/* Tags */}
          {tags.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2 border-t border-paper-100 pt-4">
              {tags.map((tag, i) => (
                <span
                  key={`${tag}-${i}`}
                  className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Rating Breakdown */}
        <div className="mb-6 rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-bold text-ink-900">评分详情</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <RatingBar label="学术水平" value={mentor.rating_academic} />
            <RatingBar label="指导风格" value={mentor.rating_guidance} />
            <RatingBar label="师生关系" value={mentor.rating_relationship} />
            <RatingBar label="科研经费" value={mentor.rating_funding} />
            <RatingBar label="工作强度" value={mentor.rating_workload} />
            <RatingBar label="毕业前景" value={mentor.rating_career} />
          </div>
        </div>

        {/* Reviews */}
        <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-ink-900">学生评价</h2>
            <Button
              size="sm"
              onClick={() => router.push(`/kaoyan/mentors/${mentorId}/review`)}
            >
              写评价
            </Button>
          </div>

          {reviews.length === 0 ? (
            <div className="py-8 text-center text-ink-500">暂无评价</div>
          ) : (
            <div className="space-y-4">
              {reviews.map((review) => (
                <ReviewCard
                  key={review.id}
                  review={review}
                  onLike={() => handleLikeReview(review.id)}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {reviewsTotal > 10 && (
            <div className="mt-6 flex justify-center gap-2">
              <button
                onClick={() => setReviewsPage((p) => Math.max(1, p - 1))}
                disabled={reviewsPage === 1}
                className="rounded-lg border border-paper-200 bg-white px-4 py-2 text-sm font-medium text-ink-700 hover:bg-paper-100 disabled:opacity-50"
              >
                上一页
              </button>
              <span className="flex items-center px-4 text-sm text-ink-500">
                第 {reviewsPage} 页 / 共 {Math.ceil(reviewsTotal / 10)} 页
              </span>
              <button
                onClick={() =>
                  setReviewsPage((p) => Math.min(Math.ceil(reviewsTotal / 10), p + 1))
                }
                disabled={reviewsPage >= Math.ceil(reviewsTotal / 10)}
                className="rounded-lg border border-paper-200 bg-white px-4 py-2 text-sm font-medium text-ink-700 hover:bg-paper-100 disabled:opacity-50"
              >
                下一页
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RatingBar({ label, value }: { label: string; value: number }) {
  const percentage = (value / 5) * 100;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm text-ink-600">{label}</span>
        <span className="text-sm font-semibold text-ink-700">{value.toFixed(1)}</span>
      </div>
      <div className="h-2 rounded-full bg-paper-100">
        <div
          className="h-full rounded-full bg-brand-500 transition-all"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

function ReviewCard({
  review,
  onLike,
}: {
  review: MentorReviewResponse;
  onLike: () => void;
}) {
  // 修复 P1 bug: review 字段可能为 null
  const overallRating = review.overall_rating ?? 0;
  const pros = review.pros || [];
  const cons = review.cons || [];
  const ratingColor =
    overallRating >= 4.5
      ? "text-green-600"
      : overallRating >= 4
        ? "text-blue-600"
        : overallRating >= 3.5
          ? "text-amber-600"
          : "text-ink-600";

  return (
    <div className="rounded-lg border border-paper-100 bg-paper-50 p-4">
      {/* Header */}
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span className="font-semibold text-ink-900">{review.title}</span>
            <div className="flex items-center gap-1">
              <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
              <span className={cn("text-sm font-semibold", ratingColor)}>
                {overallRating.toFixed(1)}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-ink-500">
            <span>{review.is_anonymous ? "匿名用户" : "实名用户"}</span>
            {review.reviewer_identity && (
              <>
                <span className="text-ink-300">·</span>
                <span>{review.reviewer_identity}</span>
              </>
            )}
            {review.is_verified && (
              <>
                <span className="text-ink-300">·</span>
                <span className="flex items-center gap-1 text-green-600">
                  <Award className="h-3 w-3" />
                  已验证
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <p className="mb-3 text-sm text-ink-700 whitespace-pre-line">{review.content}</p>

      {/* Pros & Cons */}
      {(pros.length > 0 || cons.length > 0) && (
        <div className="mb-3 grid gap-2 sm:grid-cols-2">
          {pros.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-semibold text-green-600">优点</p>
              <div className="flex flex-wrap gap-1">
                {pros.map((pro, i) => (
                  <span
                    key={`${pro}-${i}`}
                    className="rounded bg-green-50 px-2 py-0.5 text-xs text-green-700"
                  >
                    {pro}
                  </span>
                ))}
              </div>
            </div>
          )}
          {cons.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-semibold text-red-600">缺点</p>
              <div className="flex flex-wrap gap-1">
                {cons.map((con, i) => (
                  <span
                    key={`${con}-${i}`}
                    className="rounded bg-red-50 px-2 py-0.5 text-xs text-red-700"
                  >
                    {con}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between border-t border-paper-100 pt-3">
        <div className="flex items-center gap-4 text-xs text-ink-500">
          <span>{new Date(review.submitted_at).toLocaleDateString("zh-CN")}</span>
          <div className="flex items-center gap-1">
            <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
            <span>学术 {review.rating_academic}</span>
          </div>
          <div className="flex items-center gap-1">
            <Users className="h-3 w-3 text-blue-500" />
            <span>指导 {review.rating_guidance}</span>
          </div>
        </div>
        <button
          onClick={onLike}
          className="flex items-center gap-1 text-xs text-ink-500 hover:text-brand-600"
        >
          <ThumbsUp className="h-3.5 w-3.5" />
          <span>{review.like_count}</span>
        </button>
      </div>
    </div>
  );
}
