"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ThumbsUp,
  Eye,
  MessageSquare,
  Clock,
  CheckCircle2,
  Award,
} from "lucide-react";
import { kaoyanCommunityApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";
import { Badge, Button, Textarea } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";
import type { QAResponse, QAAnswerResponse } from "@/types";

export default function QADetailPage() {
  const params = useParams();
  const router = useRouter();
  const toast = useToast();
  const questionId = params.id as string;
  const user = useAuthStore((s) => s.user);

  const [question, setQuestion] = useState<QAResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [answerContent, setAnswerContent] = useState("");
  const [submittingAnswer, setSubmittingAnswer] = useState(false);

  const loadQuestion = useCallback(async () => {
    try {
      const data = await kaoyanCommunityApi.qa.get(questionId);
      setQuestion(data);
    } catch {
      toast.push("加载问题失败", "error");
    } finally {
      setLoading(false);
    }
  }, [questionId, toast]);

  useEffect(() => {
    loadQuestion();
  }, [loadQuestion]);

  const handleSubmitAnswer = async () => {
    if (!user) {
      toast.push("请先登录", "error");
      return;
    }
    if (!answerContent.trim()) {
      toast.push("请输入回答内容", "error");
      return;
    }
    setSubmittingAnswer(true);
    try {
      await kaoyanCommunityApi.qa.createAnswer(questionId, {
        content: answerContent.trim(),
      });
      toast.push("回答已提交，审核通过后将展示", "success");
      setAnswerContent("");
      loadQuestion();
    } catch {
      toast.push("回答提交失败", "error");
    } finally {
      setSubmittingAnswer(false);
    }
  };

  const handleLikeAnswer = async (answerId: string) => {
    if (!user) {
      toast.push("请先登录", "error");
      return;
    }
    try {
      const res = await kaoyanCommunityApi.qa.likeAnswer(answerId);
      setQuestion((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          answers: prev.answers.map((a) =>
            a.id === answerId ? { ...a, like_count: res.like_count } : a
          ),
        };
      });
      toast.push("点赞成功", "success");
    } catch {
      toast.push("点赞失败", "error");
    }
  };

  const handleAcceptAnswer = async (answerId: string) => {
    try {
      const updated = await kaoyanCommunityApi.qa.acceptAnswer(answerId);
      setQuestion(updated);
      toast.push("已采纳最佳回答", "success");
    } catch {
      toast.push("采纳失败", "error");
    }
  };

  const isQuestionOwner = user && question && user.id === question.user_id;

  if (loading) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
          <LoadingState text="加载问题详情..." />
        </div>
      </div>
    );
  }

  if (!question) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
          <div className="rounded-xl border border-paper-200 bg-white p-8 text-center">
            <p className="text-ink-500">问题不存在或已被删除</p>
            <Button onClick={() => router.push("/kaoyan/community")} className="mt-4">
              返回社区
            </Button>
          </div>
        </div>
      </div>
    );
  }

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

        {/* Question Card */}
        <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm mb-6">
          <div className="mb-4">
            <div className="flex items-start justify-between gap-3 mb-3">
              <h1 className="text-xl sm:text-2xl font-bold text-ink-900">{question.title}</h1>
              {question.is_resolved ? (
                <Badge color="green">已解决</Badge>
              ) : (
                <Badge color="blue">待回答</Badge>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-3 text-sm text-ink-500">
              <span>用户 {question.user_id.slice(-4)}</span>
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                {new Date(question.created_at).toLocaleDateString("zh-CN")}
              </span>
              <span className="flex items-center gap-1">
                <Eye className="h-3.5 w-3.5" />
                {question.view_count} 次浏览
              </span>
              <span className="flex items-center gap-1">
                <MessageSquare className="h-3.5 w-3.5" />
                {question.answer_count} 个回答
              </span>
            </div>
          </div>

          {/* Tags */}
          {question.tags.length > 0 && (
            <div className="mb-5 flex flex-wrap gap-2">
              {question.tags.map((tag, i) => (
                <span
                  key={`${tag}-${i}`}
                  className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Content */}
          <div className="text-ink-700 whitespace-pre-line">{question.content}</div>
        </div>

        {/* Answer Form */}
        <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm mb-6">
          <h3 className="text-lg font-semibold text-ink-900 mb-4">写回答</h3>
          <Textarea
            value={answerContent}
            onChange={(e) => setAnswerContent(e.target.value)}
            placeholder="分享你的见解和经验…"
            className="min-h-[120px] mb-3"
          />
          <div className="flex justify-end">
            <Button onClick={handleSubmitAnswer} loading={submittingAnswer}>
              提交回答
            </Button>
          </div>
        </div>

        {/* Answers */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-ink-900">
            全部回答 ({question.answer_count})
          </h3>
          {question.answers.length === 0 ? (
            <div className="rounded-xl border border-paper-200 bg-white p-8 text-center text-ink-500">
              暂无回答，来做第一个回答者吧
            </div>
          ) : (
            question.answers.map((answer) => (
              <AnswerCard
                key={answer.id}
                answer={answer}
                isBest={answer.id === question.best_answer_id}
                isQuestionOwner={!!isQuestionOwner}
                onLike={() => handleLikeAnswer(answer.id)}
                onAccept={() => handleAcceptAnswer(answer.id)}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function AnswerCard({
  answer,
  isBest,
  isQuestionOwner,
  onLike,
  onAccept,
}: {
  answer: QAAnswerResponse;
  isBest: boolean;
  isQuestionOwner: boolean;
  onLike: () => void;
  onAccept: () => void;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border bg-white p-5 shadow-sm",
        isBest ? "border-green-300 bg-green-50/30" : "border-paper-200"
      )}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-ink-500">
          <span>用户 {answer.user_id.slice(-4)}</span>
          <span className="text-ink-300">·</span>
          <span className="flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" />
            {new Date(answer.created_at).toLocaleDateString("zh-CN")}
          </span>
        </div>
        {isBest && (
          <Badge color="green">
            <Award className="h-3 w-3 mr-1" />
            最佳回答
          </Badge>
        )}
      </div>

      <div className="mb-4 text-ink-700 whitespace-pre-line">{answer.content}</div>

      <div className="flex items-center justify-between">
        <button
          onClick={onLike}
          className="flex items-center gap-1 text-sm text-ink-500 hover:text-brand-600"
        >
          <ThumbsUp className="h-4 w-4" />
          <span>{answer.like_count}</span>
        </button>
        {isQuestionOwner && !isBest && (
          <Button variant="ghost" size="sm" onClick={onAccept}>
            <CheckCircle2 className="h-4 w-4 mr-1.5" />
            采纳为最佳
          </Button>
        )}
      </div>
    </div>
  );
}
