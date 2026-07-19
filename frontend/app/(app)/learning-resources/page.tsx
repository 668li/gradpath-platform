"use client";

import { useCallback, useEffect, useState } from "react";
import { learningResourceApi } from "@/lib/api";
import { LearningResource, LearningResourceCreate } from "@/types";
import { toast } from "sonner";
import { Plus, Trash2, ExternalLink, Star, Search } from "lucide-react";
import { EmptyState } from "@/components/ui/empty";
import { ListSkeleton } from "@/components/ui/skeleton";

const DIFFICULTY_LABELS: Record<string, string> = {
  beginner: "入门",
  intermediate: "进阶",
  advanced: "高级",
};

const DIFFICULTY_COLORS: Record<string, string> = {
  beginner: "bg-emerald-500/15 text-emerald-700",
  intermediate: "bg-amber-500/15 text-amber-700",
  advanced: "bg-red-500/15 text-red-700",
};

const RESOURCE_TYPE_LABELS: Record<string, string> = {
  video: "视频",
  article: "文章",
  book: "书籍",
  course: "课程",
};

const SUBJECTS = ["408", "数据结构", "计算机组成原理", "操作系统", "计算机网络", "数学", "英语", "政治"];

export default function LearningResourcesPage() {
  const [resources, setResources] = useState<LearningResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [filterSubject, setFilterSubject] = useState<string>("all");
  const [filterDifficulty, setFilterDifficulty] = useState<string>("all");
  const [searchText, setSearchText] = useState<string>("");
  const [formData, setFormData] = useState<LearningResourceCreate>({
    title: "",
    url: "",
    resource_type: "video",
    subject: "",
    difficulty: "beginner",
    description: "",
    tags: [],
    rating: 0,
    is_free: true,
  });

  useEffect(() => {
    loadResources();
  }, [filterSubject, filterDifficulty]);

  const loadResources = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (filterSubject !== "all") params.subject = filterSubject;
      if (filterDifficulty !== "all") params.difficulty = filterDifficulty;
      const data = await learningResourceApi.list(params);
      setResources(Array.isArray(data) ? data : (data as any).items || []);
    } catch {
      toast.error("加载学习资源失败");
    } finally {
      setLoading(false);
    }
  }, [filterSubject, filterDifficulty]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await learningResourceApi.create(formData);
      toast.success("创建成功");
      setShowCreateForm(false);
      setFormData({
        title: "",
        url: "",
        resource_type: "video",
        subject: "",
        difficulty: "beginner",
        description: "",
        tags: [],
        rating: 0,
        is_free: true,
      });
      loadResources();
    } catch {
      toast.error("创建失败");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除这个资源吗？")) return;
    try {
      await learningResourceApi.delete(id);
      toast.success("删除成功");
      loadResources();
    } catch {
      toast.error("删除失败");
    }
  };

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <ListSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink-800">学习资源</h1>
          <p className="text-sm text-ink-500 mt-1">考研备考资料汇总</p>
        </div>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="flex items-center gap-2 px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
          添加资源
        </button>
      </div>

      {/* 筛选器 */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-400" />
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="搜索资源名称..."
            className="w-full rounded-lg border border-ink-200 bg-white pl-9 pr-3 py-2 text-sm text-ink-800 placeholder:text-ink-400 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
          />
        </div>
        <select
          value={filterSubject}
          onChange={(e) => setFilterSubject(e.target.value)}
          className="px-3 py-2 text-sm border border-ink-200 rounded-lg bg-white text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
        >
          <option value="all">全部科目</option>
          {SUBJECTS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select
          value={filterDifficulty}
          onChange={(e) => setFilterDifficulty(e.target.value)}
          className="px-3 py-2 text-sm border border-ink-200 rounded-lg bg-white text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
        >
          <option value="all">全部难度</option>
          <option value="beginner">入门</option>
          <option value="intermediate">进阶</option>
          <option value="advanced">高级</option>
        </select>
      </div>

      {/* 创建表单 */}
      {showCreateForm && (
        <div className="rounded-xl border border-ink-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-ink-800 mb-4">添加学习资源</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">资源标题</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="例如：王道考研 408 全套视频"
                required
                className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/30"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">资源链接</label>
              <input
                type="url"
                value={formData.url || ""}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                placeholder="https://..."
                className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/30"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-ink-700 mb-1">资源类型</label>
                <select
                  value={formData.resource_type}
                  onChange={(e) => setFormData({ ...formData, resource_type: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/30"
                >
                  <option value="video">视频</option>
                  <option value="article">文章</option>
                  <option value="book">书籍</option>
                  <option value="course">课程</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-700 mb-1">难度</label>
                <select
                  value={formData.difficulty}
                  onChange={(e) => setFormData({ ...formData, difficulty: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/30"
                >
                  <option value="beginner">入门</option>
                  <option value="intermediate">进阶</option>
                  <option value="advanced">高级</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">科目</label>
              <input
                type="text"
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                placeholder="例如：408、数据结构"
                required
                className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/30"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">描述</label>
              <input
                type="text"
                value={formData.description || ""}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="资源简介..."
                className="w-full px-3 py-2 text-sm border border-ink-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/30"
              />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors">
                添加
              </button>
              <button type="button" onClick={() => setShowCreateForm(false)} className="px-4 py-2 border border-ink-200 text-ink-600 rounded-lg hover:bg-ink-50 transition-colors">
                取消
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 资源列表 */}
      {resources.length === 0 ? (
        <EmptyState
          title="还没有学习资源"
          description="添加你备考过程中发现的优质学习资源，方便随时查阅"
          action={
            <button
              onClick={() => setShowCreateForm(true)}
              className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors"
            >
              <Plus className="w-4 h-4 inline mr-1" />
              添加第一个资源
            </button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {resources
            .filter((r) => !searchText || r.title.toLowerCase().includes(searchText.toLowerCase()) || r.description?.toLowerCase().includes(searchText.toLowerCase()))
            .map((resource) => (
            <div key={resource.id} className="rounded-xl border border-ink-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <h3 className="text-lg font-semibold text-ink-800 leading-tight">{resource.title}</h3>
                <button
                  onClick={() => handleDelete(resource.id)}
                  className="p-1 text-ink-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <div className="flex flex-wrap items-center gap-2 mb-3">
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${DIFFICULTY_COLORS[resource.difficulty] || "bg-ink-100 text-ink-600"}`}>
                  {DIFFICULTY_LABELS[resource.difficulty] || resource.difficulty}
                </span>
                <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-500/15 text-blue-700">
                  {resource.subject}
                </span>
                {resource.is_free && (
                  <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-emerald-500/15 text-emerald-700">
                    免费
                  </span>
                )}
                {resource.resource_type && (
                  <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-ink-100 text-ink-600">
                    {RESOURCE_TYPE_LABELS[resource.resource_type] || resource.resource_type}
                  </span>
                )}
              </div>

              {resource.description && (
                <p className="text-sm text-ink-500 mb-3 line-clamp-2">{resource.description}</p>
              )}

              <div className="flex items-center justify-between text-sm text-ink-400">
                <div className="flex items-center gap-1">
                  <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                  <span>{resource.rating}/5</span>
                </div>
                <span>{resource.view_count} 次浏览</span>
              </div>

              {resource.url && (
                <button
                  onClick={() => window.open(resource.url || undefined, "_blank")}
                  className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 text-sm border border-ink-200 text-ink-600 rounded-lg hover:bg-ink-50 transition-colors"
                >
                  <ExternalLink className="w-4 h-4" />
                  访问资源
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
