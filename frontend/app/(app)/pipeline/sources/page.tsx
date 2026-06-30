"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Settings } from "lucide-react";
import { pipelineApi } from "@/lib/api";
import { Button, Input } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import type { DataSourceResponse } from "@/types";

export default function SourcesPage() {
  const toast = useToast();
  const [sources, setSources] = useState<DataSourceResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<DataSourceResponse | null>(null);

  // 表单
  const [name, setName] = useState("");
  const [apiUrl, setApiUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [isActive, setIsActive] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      setSources(await pipelineApi.sources());
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const resetForm = () => {
    setName("");
    setApiUrl("");
    setApiKey("");
    setIsActive(true);
    setEditing(null);
  };

  const handleSave = async () => {
    if (!name.trim()) {
      toast.push("请输入名称", "error");
      return;
    }
    try {
      const body = {
        name: name.trim(),
        api_url: apiUrl.trim() || null,
        api_key: apiKey.trim() || null,
        is_active: isActive,
      };
      if (editing) {
        await pipelineApi.updateSource(editing.id, body);
        toast.push("已更新", "success");
      } else {
        await pipelineApi.createSource({ ...body, source_type: "api" });
        toast.push("已创建", "success");
      }
      resetForm();
      setShowForm(false);
      load();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "保存失败", "error");
    }
  };

  const handleEdit = (s: DataSourceResponse) => {
    setEditing(s);
    setName(s.name);
    setApiUrl(s.api_url ?? "");
    setApiKey(s.api_key ?? "");
    setIsActive(s.is_active);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await pipelineApi.deleteSource(id);
      toast.push("已删除", "success");
      load();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "删除失败", "error");
    }
  };

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">数据源配置</h1>
          <p className="text-sm text-slate-500 mt-1">管理外部 API 数据源</p>
        </div>
        <Button
          onClick={() => {
            resetForm();
            setShowForm(!showForm);
          }}
        >
          <Plus className="h-4 w-4" /> {showForm ? "取消" : "新增数据源"}
        </Button>
      </div>

      {showForm && (
        <div className="card space-y-4">
          <h2 className="font-semibold text-slate-800">
            {editing ? "编辑数据源" : "新建数据源"}
          </h2>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">名称</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="如：教育部就业统计"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">API URL</label>
            <Input
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="https://api.example.com/data"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">API Key</label>
            <Input
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Bearer token"
            />
          </div>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm text-slate-600">启用</span>
          </label>
          <Button onClick={handleSave}>{editing ? "更新" : "创建"}</Button>
        </div>
      )}

      <div className="space-y-3">
        {sources.length === 0 && !showForm ? (
          <EmptyState title="暂无数据源" description="点击「新增数据源」添加外部 API 配置" />
        ) : (
          sources.map((s) => (
            <div key={s.id} className="card flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-slate-800">{s.name}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      s.is_active
                        ? "bg-green-50 text-green-600"
                        : "bg-slate-100 text-slate-400"
                    }`}
                  >
                    {s.is_active ? "启用" : "禁用"}
                  </span>
                </div>
                {s.api_url && <p className="mt-0.5 text-xs text-slate-400">{s.api_url}</p>}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleEdit(s)}
                  className="p-2 rounded hover:bg-slate-100"
                  title="编辑"
                >
                  <Settings className="h-4 w-4 text-slate-400" />
                </button>
                <button
                  onClick={() => handleDelete(s.id)}
                  className="p-2 rounded hover:bg-red-50"
                  title="删除"
                >
                  <Trash2 className="h-4 w-4 text-red-400" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
