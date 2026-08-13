"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Plus,
  Search,
  Eye,
  Pencil,
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
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  const [articles, setArticles] = useState<KnowledgeArticle[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [authChecked, setAuthChecked] = useState(false);
  const [selectedArticle, setSelectedArticle] = useState<KnowledgeArticle | null>(null);

  useEffect(() => {
    if (!user) {
      fetchUser().then(() => setAuthChecked(true));
    } else {
      setAuthChecked(true);
    }
  }, [user, fetchUser]);

  // 防抖搜索：输入停止 400ms 后触发服务端搜索
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchQuery(search.trim());
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [search]);

  const loadArticles = useCallback(async () => {
    setLoading(true);
    try {
      const res = await knowledgeApi.list({
        category: category || undefined,
        q: searchQuery || undefined,
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
  }, [category, searchQuery, page, toast]);

  useEffect(() => {
    if (authChecked && user) {
      loadArticles();
    }
  }, [loadArticles, user, authChecked]);

  const handleCategoryChange = (v: string) => {
    setCategory(v);
    setPage(1);
  };

  if (!authChecked || !user) {
    return <LoadingState />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">知识库</h1>
          <p className="text-sm text-ink-500 mt-1">
            职业知识条目，供 AI 管家对话检索参考
          </p>
        </div>
        {user.is_admin && (
          <Link href="/knowledge/new">
            <Button>
              <Plus className="h-4 w-4" /> 新建文章
            </Button>
          </Link>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select
          value={category}
          onChange={(e) => handleCategoryChange(e.target.value)}
          className="rounded-lg border border-ink-300 bg-white px-3 py-2 text-sm text-ink-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -tranink-y-1/2 text-ink-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索标题…"
            className="w-full rounded-lg border border-ink-300 bg-white pl-9 pr-3 py-2 text-sm text-ink-700 placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
          />
        </div>
      </div>

      {loading ? (
        <LoadingState />
      ) : articles.length === 0 ? (
        <EmptyState
          title={searchQuery || category ? "未找到匹配的文章" : "知识库为空"}
          description={
            searchQuery || category
              ? "尝试调整筛选条件或搜索关键词"
              : "暂无知识文章"
          }
        />
      ) : (
        <>
          <div className="grid gap-4">
            {articles.map((article) => (
              <div
                key={article.id}
                className="rounded-xl border border-ink-200 bg-white p-5 hover:shadow-sm transition-shadow"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge color={CATEGORY_COLORS[article.category] || "slate"}>
                        {article.category}
                      </Badge>
                      {article.is_published ? (
                        <Badge color="green">已发布</Badge>
                      ) : (
                        <Badge color="slate">草稿</Badge>
                      )}
                    </div>
                    <h3
                      className="font-medium text-ink-800 hover:text-brand-600 cursor-pointer text-lg"
                      onClick={() => setSelectedArticle(article)}
                    >
                      {article.title}
                    </h3>
                    {article.content && (
                      <p className="text-sm text-ink-500 mt-1 line-clamp-2">
                        {article.content.replace(/[#*`>\[\]]/g, '').slice(0, 100)}...
                      </p>
                    )}
                    <div className="flex flex-wrap gap-1 mt-3">
                      {article.tags.slice(0, 5).map((tag, i) => (
                        <span
                          key={`${tag}-${i}`}
                          className="rounded bg-ink-100 px-2 py-0.5 text-xs text-ink-500"
                        >
                          {tag}
                        </span>
                      ))}
                      {article.tags.length > 5 && (
                        <span className="text-xs text-ink-400">
                          +{article.tags.length - 5}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-ink-400 mt-3">
                      更新于 {formatDate(article.updated_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => setSelectedArticle(article)}
                      className="rounded-md p-2 text-ink-400 hover:bg-brand-50 hover:text-brand-600 transition-colors"
                      aria-label="查看"
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                    {user.is_admin && (
                      <Link href={`/knowledge/${article.id}/edit`}>
                        <button
                          className="rounded-md p-2 text-ink-400 hover:bg-brand-50 hover:text-brand-600 transition-colors"
                          aria-label="编辑"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            onPageChange={setPage}
          />
        </>
      )}

      {selectedArticle && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedArticle(null)}>
          <div
            className="bg-white rounded-2xl max-w-3xl w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-ink-100">
              <div className="flex items-center gap-2 mb-3">
                <Badge color={CATEGORY_COLORS[selectedArticle.category] || "slate"}>
                  {selectedArticle.category}
                </Badge>
              </div>
              <h2 className="text-xl font-semibold text-ink-800">
                {selectedArticle.title}
              </h2>
            </div>
            <div className="p-6">
              <div className="prose prose-sm max-w-none text-ink-700 whitespace-pre-wrap">
                {selectedArticle.content}
              </div>
              {selectedArticle.tags.length > 0 && (
                <div className="mt-6 pt-4 border-t border-ink-100">
                  <div className="flex flex-wrap gap-1">
                    {selectedArticle.tags.map((tag, i) => (
                      <span
                        key={`${tag}-${i}`}
                        className="rounded bg-ink-100 px-2 py-0.5 text-xs text-ink-500"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="p-4 border-t border-ink-100 flex justify-end">
              <Button variant="secondary" onClick={() => setSelectedArticle(null)}>
                关闭
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
