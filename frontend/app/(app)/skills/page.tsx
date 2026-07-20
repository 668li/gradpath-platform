"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Plus, Pencil, Trash2, Network, List, ChevronRight } from "lucide-react";
import { skillsApi } from "@/lib/api";
import { formatDate, levelStars, cn } from "@/lib/utils";
import { Modal } from "@/components/ui/modal";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Badge, Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { SkillRadar } from "@/components/charts";
import { SkillForm } from "@/components/skill-form";
import type { SkillResponse, SkillStats } from "@/types";

// 优化：D3.js 树状图依赖 DOM，仅在客户端渲染，按需加载减少首屏 JS 体积
const SkillTreeGraph = dynamic(
  () => import("@/components/skill-tree-graph").then((m) => m.SkillTreeGraph),
  {
    ssr: false,
    loading: () => <LoadingState />,
  },
);

const LEVEL_COLOR: Record<number, "slate" | "blue" | "purple"> = {
  1: "slate",
  2: "blue",
  3: "blue",
  4: "purple",
  5: "purple",
};

function SkillNodeItem({
  node,
  depth,
  onEdit,
  onDelete,
}: {
  node: SkillResponse;
  depth: number;
  onEdit: (s: SkillResponse) => void;
  onDelete: (s: SkillResponse) => void;
}) {
  return (
    <div>
      <div
        className="flex items-center gap-2 rounded-lg px-2 py-2 hover:bg-slate-50 group"
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
      >
        {node.children?.length > 0 ? (
          <ChevronRight className="h-4 w-4 text-slate-300 shrink-0" />
        ) : (
          <span className="w-4 shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-slate-800">{node.name}</span>
            <Badge color={LEVEL_COLOR[node.level] ?? "slate"}>
              Lv.{node.level}
            </Badge>
            {node.acquired_date && (
              <span className="text-xs text-slate-400">
                {formatDate(node.acquired_date)}
              </span>
            )}
          </div>
          {node.notes && (
            <p className="text-xs text-slate-400 mt-0.5 truncate">{node.notes}</p>
          )}
          <span className="text-amber-500 tracking-wide text-xs">
            {levelStars(node.level)}
          </span>
        </div>
        <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => onEdit(node)}
            className="p-1.5 rounded-md text-slate-400 hover:bg-slate-100 hover:text-brand-600"
            aria-label="编辑"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => onDelete(node)}
            className="p-1.5 rounded-md text-slate-400 hover:bg-red-50 hover:text-red-600"
            aria-label="删除"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
      {node.children?.map((child) => (
        <SkillNodeItem
          key={child.id}
          node={child}
          depth={depth + 1}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}

export default function SkillsPage() {
  const toast = useToast();
  const [tree, setTree] = useState<SkillResponse[]>([]);
  const [stats, setStats] = useState<SkillStats>({});
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<SkillResponse | null>(null);
  const [viewMode, setViewMode] = useState<"tree" | "list">("tree");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [treeResult, statsResult] = await Promise.allSettled([skillsApi.tree(), skillsApi.stats()]);
      if (treeResult.status === "fulfilled") {
        setTree(treeResult.value);
      }
      if (statsResult.status === "fulfilled") {
        setStats(statsResult.value);
      }
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    setModalOpen(true);
  };

  const openEdit = (s: SkillResponse) => {
    setEditing(s);
    setModalOpen(true);
  };

  const handleSaved = () => {
    setModalOpen(false);
    setEditing(null);
    load();
  };

  const handleDelete = async (s: SkillResponse) => {
    if (
      !window.confirm(
        `确认删除技能「${s.name}」？${s.children?.length ? "其子技能也将被删除。" : ""}`,
      )
    )
      return;
    try {
      await skillsApi.remove(s.id);
      toast.push("删除成功", "success");
      load();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "删除失败", "error");
    }
  };

  // 按顶层节点的 category 分组
  const grouped = tree.reduce<Record<string, SkillResponse[]>>((acc, node) => {
    const cat = node.category || "未分类";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(node);
    return acc;
  }, {});

  const radarData = Object.entries(stats).map(([category, count]) => ({
    category,
    count,
  }));

  const totalCount = tree.reduce(
    (sum, n) => sum + 1 + countDescendants(n),
    0,
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">技能树</h1>
          <p className="text-sm text-slate-500 mt-1">
            构建你的个人技能图谱，共 {totalCount} 个技能节点
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5">
            <button
              type="button"
              onClick={() => setViewMode("tree")}
              className={cn(
                "inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                viewMode === "tree"
                  ? "bg-brand-600 text-white"
                  : "text-slate-600 hover:bg-slate-100",
              )}
            >
              <Network className="h-3.5 w-3.5" /> 树形图
            </button>
            <button
              type="button"
              onClick={() => setViewMode("list")}
              className={cn(
                "inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                viewMode === "list"
                  ? "bg-brand-600 text-white"
                  : "text-slate-600 hover:bg-slate-100",
              )}
            >
              <List className="h-3.5 w-3.5" /> 列表
            </button>
          </div>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" /> 新建技能
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 技能分组列表 */}
        <div className="lg:col-span-2 space-y-4">
          {loading ? (
            <div className="space-y-4 animate-pulse">
              {[1,2,3].map(i => (
                <div key={`skel-${i}`} className="card p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="h-4 w-4 rounded bg-slate-200" />
                    <div className="h-4 w-20 bg-slate-200 rounded" />
                    <div className="h-5 w-10 bg-slate-200 rounded-full" />
                  </div>
                  {[1,2].map(j => (
                    <div key={j} className="flex items-center gap-2 py-2">
                      <div className="h-3 w-3 bg-slate-100 rounded" />
                      <div className="h-3 bg-slate-200 rounded flex-1" />
                      <div className="h-3 w-16 bg-slate-100 rounded" />
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ) : tree.length === 0 ? (
            <EmptyState
              title="还没有技能"
              description="添加你的第一项技能，构建个人技能树"
              action={
                <Button onClick={openCreate}>
                  <Plus className="h-4 w-4" /> 创建技能
                </Button>
              }
            />
          ) : viewMode === "tree" ? (
            <div className="card p-4">
              <SkillTreeGraph skills={tree} onNodeClick={openEdit} />
            </div>
          ) : (
            Object.entries(grouped).map(([cat, nodes]) => (
              <div key={cat} className="card">
                <div className="flex items-center gap-2 mb-2">
                  <Network className="h-4 w-4 text-brand-500" />
                  <h2 className="font-semibold text-slate-800">{cat}</h2>
                  <Badge color="blue">{countCategoryNodes(nodes)}</Badge>
                </div>
                <div className="divide-y divide-slate-50">
                  {nodes.map((node) => (
                    <SkillNodeItem
                      key={node.id}
                      node={node}
                      depth={0}
                      onEdit={openEdit}
                      onDelete={handleDelete}
                    />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* 雷达图 */}
        <div className="card h-fit lg:sticky lg:top-6">
          <h2 className="font-semibold text-slate-800 mb-2">技能分类雷达</h2>
          {radarData.length === 0 ? (
            <EmptyState title="暂无数据" description="添加技能后将显示雷达图" />
          ) : (
            <SkillRadar data={radarData} />
          )}
        </div>
      </div>

      <Modal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditing(null);
        }}
        title={editing ? "编辑技能" : "新建技能"}
        className="max-w-xl"
      >
        <SkillForm
          initial={editing}
          tree={tree}
          onSaved={handleSaved}
          onCancel={() => {
            setModalOpen(false);
            setEditing(null);
          }}
        />
      </Modal>
    </div>
  );
}

function countDescendants(node: SkillResponse): number {
  return (node.children ?? []).reduce(
    (sum, c) => sum + 1 + countDescendants(c),
    0,
  );
}

function countCategoryNodes(nodes: SkillResponse[]): number {
  return nodes.reduce((sum, n) => sum + 1 + countDescendants(n), 0);
}
