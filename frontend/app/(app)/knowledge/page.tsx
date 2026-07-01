"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Plus,
  Search,
  Pencil,
  Trash2,
} from "lucide-react";
import { knowledgeApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Pagination } from "@/components/ui/pagination";
import { Badge, Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";
import type { KnowledgeArticle } from "@/types";

const CATEGORIES = [
  { value: "", label: "全部分类" },
  { value: "行业指南", label: "行业指南" },
  { value: "岗位要求", label: "岗位要求" },
  { value: "技能图谱", label: "技能图谱" },
  { value: "面试攻略", label: "面试攻略" },
  { value: "薪资参考", label: "薪资参考" },
  { value: "升学路径", label: "升学路径" },
];

const CATEGORY_COLORS: Record<string, "blue" | "green" | "amber" | "purple" | "red" | "slate"> = {
  行业指南: "blue",
  岗位要求: "green",
  技能图谱: "amber",
  面试攻略: "purple",
  薪资参考: "red",
  升学路径: "slate",
};

const PAGE_SIZE = 20;

export default function KnowledgeListPage() {
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  const [articles, setArticles] = useState<KnowledgeArticle[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  // 权限检查
  useEffect(() => {
    if (!user) {
      fetchUser().then(() => setAuthChecked(true));
    } else {
      setAuthChecked(true);
    }
  }, [user, fetchUser]);

  useEffect(() => {
    if (authChecked && user && !user.is_admin) {
      router.replace("/dashboard");
    }
  }, [authChecked, user, router]);

  const loadArticles = useCallback(async () => {
    setLoading(true);
    try {
      const res = await knowledgeApi.list({
        category: category || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setArticles(res.items);
      setTotal(res.total);
    } catch {
      toast.push("加载知识库失败", "error");
    } finally {
      setLoading(false);
    }
  }, [category, page, toast]);

  useEffect(() => {
    if (user?.is_admin) {
      loadArticles();
    }
  }, [loadArticles, user]);

  // 分类变化时重置到第一页
  const handleCategoryChange = (v: string) => {
    setCategory(v);
    setPage(1);
  };

  const handleDelete = async (id: string, title: string) => {
    if (!confirm(`确认删除「${title}」？此操作不可撤销。`)) return;
    setDeleting(id);
    try {
      await knowledgeApi.delete(id);
      toast.push("已删除", "success");
      // 如果当前页只剩一条且不是第一页，回到上一页
      if (articles.length === 1 && page > 1) {
        setPage(page - 1);
      } else {
        loadArticles();
      }
    } catch {
      toast.push("删除失败", "error");
    } finally {
      setDeleting(null);
    }
  };

  // 前端搜索过滤
  const filteredArticles = search.trim()
    ? articles.filter((a) =>
        a.title.toLowerCase().includes(search.trim().toLowerCase()),
      )
    : articles;

  if (!authChecked || (authChecked && user && !user.is_admin)) {
    return <LoadingState />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">知识库管理</h1>
          <p className="text-sm text-slate-500 mt-1">
            管理职业知识条目，供 AI 管家对话检索使用
          </p>
        </div>
        <Link href="/knowledge/new">
          <Button>
            <Plus className="h-4 w-4" /> 新建文章
          </Button>
        </Link>
      </div>

      {/* 工具栏 */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={category}
          onChange={(e) => handleCategoryChange(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索标题…"
            className="w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
          />
        </div>
      </div>

      {/* 列表 */}
      {loading ? (
        <LoadingState />
      ) : filteredArticles.length === 0 ? (
        <EmptyState
          title={search || category ? "未找到匹配的文章" : "知识库为空"}
          description={
            search || category
              ? "尝试调整筛选条件或搜索关键词"
              : "新建第一篇知识文章，为 AI 管家提供检索素材"
          }
          action={
            !search && !category ? (
              <Link href="/knowledge/new">
                <Button>
                  <Plus className="h-4 w-4" /> 新建文章
                </Button>
              </Link>
            ) : undefined
          }
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">标题</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">分类</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">标签</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">状态</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">更新时间</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {filteredArticles.map((article) => (
                  <tr key={article.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-4 py-3">
                      <Link
                        href={`/knowledge/${article.id}/edit`}
                        className="font-medium text-slate-700 hover:text-brand-600"
                      >
                        {article.title}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <Badge color={CATEGORY_COLORS[article.category] || "slate"}>
                        {article.category}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {article.tags.slice(0, 3).map((tag, i) => (
                          <span
                            key={i}
                            className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500"
                          >
                            {tag}
                          </span>
                        ))}
                        {article.tags.length > 3 && (
                          <span className="text-[10px] text-slate-400">
                            +{article.tags.length - 3}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {article.is_published ? (
                        <Badge color="green">已发布</Badge>
                      ) : (
                        <Badge color="slate">草稿</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {formatDate(article.updated_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <Link href={`/knowledge/${article.id}/edit`}>
                          <button
                            className="rounded-md p-1.5 text-slate-400 hover:bg-brand-50 hover:text-brand-600 transition-colors"
                            aria-label="编辑"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                        </Link>
                        <button
                          onClick={() => handleDelete(article.id, article.title)}
                          disabled={deleting === article.id}
                          className="rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 transition-colors disabled:opacity-50"
                          aria-label="删除"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}
