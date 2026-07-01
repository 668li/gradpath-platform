"use client";

import { useEffect, useMemo, useRef } from "react";
import { hierarchy, tree, type HierarchyPointNode } from "d3-hierarchy";
import { select } from "d3-selection";
import { zoom, zoomIdentity, type ZoomBehavior } from "d3-zoom";
import { Plus, Minus, RotateCcw } from "lucide-react";
import { EmptyState } from "@/components/ui/empty";
import type { SkillResponse } from "@/types";

interface SkillTreeGraphProps {
  skills: SkillResponse[];
  onNodeClick: (skill: SkillResponse) => void;
}

/** 预定义分类配色（按出现顺序循环取色） */
const CATEGORY_PALETTE = [
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
  "#f97316",
];

// 节点与间距尺寸
const NODE_WIDTH = 156;
const NODE_HEIGHT = 46;
const H_SPACING = 250; // 深度方向（水平）间距
const V_SPACING = 66; // 兄弟方向（垂直）间距
const MIN_HEIGHT = 500;

const VIRTUAL_ROOT_ID = "__gradpath_virtual_root__";

/** 把顶层技能数组包裹为一个虚拟根节点，供 d3-hierarchy 构建单棵树 */
function buildVirtualRoot(skills: SkillResponse[]): SkillResponse {
  return {
    id: VIRTUAL_ROOT_ID,
    user_id: "",
    name: "",
    category: "",
    level: 0,
    parent_id: null,
    acquired_date: null,
    notes: null,
    created_at: "",
    updated_at: "",
    children: skills,
  };
}

/** 估算文本渲染宽度（CJK 计 13px，其余计 7px） */
function approxTextWidth(text: string): number {
  let w = 0;
  for (const ch of text) {
    w += /[\u4e00-\u9fff\u3000-\u30ff\uff00-\uffef]/.test(ch) ? 13 : 7;
  }
  return w;
}

/** 按可用宽度截断文本，超出部分以省略号结尾 */
function truncateLabel(text: string, maxWidth: number): string {
  if (approxTextWidth(text) <= maxWidth) return text;
  let w = 0;
  let out = "";
  for (const ch of text) {
    const cw = /[\u4e00-\u9fff\u3000-\u30ff\uff00-\uffef]/.test(ch) ? 13 : 7;
    if (w + cw > maxWidth - 10) break;
    w += cw;
    out += ch;
  }
  return `${out}…`;
}

interface LayoutBounds {
  contentW: number;
  contentH: number;
  minNodeY: number;
  minNodeX: number;
  maxNodeX: number;
}

interface LayoutResult {
  nodes: HierarchyPointNode<SkillResponse>[];
  links: {
    source: HierarchyPointNode<SkillResponse>;
    target: HierarchyPointNode<SkillResponse>;
  }[];
  bounds: LayoutBounds;
  categoryColor: Map<string, string>;
  height: number;
}

/** 收集所有出现过的分类（保持首次出现顺序） */
function collectCategories(skills: SkillResponse[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  const walk = (nodes: SkillResponse[]) => {
    nodes.forEach((n) => {
      const c = n.category || "未分类";
      if (!seen.has(c)) {
        seen.add(c);
        out.push(c);
      }
      if (n.children?.length) walk(n.children);
    });
  };
  walk(skills);
  return out;
}

/** 用 d3-hierarchy 计算水平树布局 */
function buildLayout(skills: SkillResponse[]): LayoutResult | null {
  if (skills.length === 0) return null;

  const rootData = buildVirtualRoot(skills);
  const root = hierarchy(rootData, (d) => d.children);
  const treeLayout = tree<SkillResponse>()
    .nodeSize([V_SPACING, H_SPACING])
    .separation((a, b) => (a.parent === b.parent ? 1 : 1.3));
  const laidOut = treeLayout(root);

  // 过滤掉虚拟根节点
  const nodes = laidOut
    .descendants()
    .filter((n) => n.data.id !== VIRTUAL_ROOT_ID);
  const links = laidOut
    .links()
    .filter((l) => l.source.data.id !== VIRTUAL_ROOT_ID);

  // 分类配色
  const categories = collectCategories(skills);
  const categoryColor = new Map<string, string>();
  categories.forEach((c, i) => {
    categoryColor.set(c, CATEGORY_PALETTE[i % CATEGORY_PALETTE.length]);
  });

  // 计算内容包围盒（坐标：水平=node.y，垂直=node.x）
  let minNodeY = Infinity;
  let maxNodeY = -Infinity;
  let minNodeX = Infinity;
  let maxNodeX = -Infinity;
  nodes.forEach((n) => {
    minNodeY = Math.min(minNodeY, n.y);
    maxNodeY = Math.max(maxNodeY, n.y);
    minNodeX = Math.min(minNodeX, n.x);
    maxNodeX = Math.max(maxNodeX, n.x);
  });

  const contentW = maxNodeY - minNodeY + NODE_WIDTH;
  const contentH = maxNodeX - minNodeX + NODE_HEIGHT;
  const height = Math.max(MIN_HEIGHT, contentH + 80);

  return {
    nodes,
    links,
    bounds: { contentW, contentH, minNodeY, minNodeX, maxNodeX },
    categoryColor,
    height,
  };
}

/** 生成水平方向的贝塞尔连接路径 */
function linkPath(
  source: HierarchyPointNode<SkillResponse>,
  target: HierarchyPointNode<SkillResponse>,
): string {
  const sx = source.y;
  const sy = source.x;
  const tx = target.y;
  const ty = target.x;
  const mx = (sx + tx) / 2;
  return `M${sx},${sy} C${mx},${sy} ${mx},${ty} ${tx},${ty}`;
}

interface ZoomHandle {
  behavior: ZoomBehavior<SVGSVGElement, unknown>;
  fit: () => void;
}

export function SkillTreeGraph({ skills, onNodeClick }: SkillTreeGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const zoomRef = useRef<ZoomHandle | null>(null);

  const layout = useMemo(() => buildLayout(skills), [skills]);

  // 绑定 d3-zoom：拖拽平移、滚轮缩放，并设置初始适配视图
  useEffect(() => {
    if (!svgRef.current || !gRef.current || !layout) return;

    const svgEl = svgRef.current;
    const gEl = gRef.current;
    const svgSel = select(svgEl);
    const gSel = select(gEl);

    const behavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 3])
      .on("zoom", (event) => {
        gSel.attr("transform", event.transform.toString());
      });

    const fit = () => {
      const svgWidth = svgEl.clientWidth || 800;
      const svgHeight = svgEl.clientHeight || layout.height;
      const { contentW, minNodeY, minNodeX, maxNodeX } = layout.bounds;
      // 水平方向适配视口宽度
      const s = Math.min(1, Math.max(0.3, (svgWidth - 80) / contentW));
      // 让最左节点左边缘距视口左边 40px
      const tx = 40 - (minNodeY - NODE_WIDTH / 2) * s;
      // 垂直方向居中
      const midNodeX = (minNodeX + maxNodeX) / 2;
      let ty = svgHeight / 2 - midNodeX * s;
      // 避免内容顶部溢出
      const topEdge = ty + (minNodeX - NODE_HEIGHT / 2) * s;
      if (topEdge < 20) ty += 20 - topEdge;
      svgSel.call(behavior.transform, zoomIdentity.translate(tx, ty).scale(s));
    };

    svgSel.call(behavior);
    fit();

    zoomRef.current = { behavior, fit };

    return () => {
      svgSel.on(".zoom", null);
    };
  }, [layout]);

  const handleZoomIn = () => {
    if (!svgRef.current || !zoomRef.current) return;
    select(svgRef.current).call(zoomRef.current.behavior.scaleBy, 1.3);
  };

  const handleZoomOut = () => {
    if (!svgRef.current || !zoomRef.current) return;
    select(svgRef.current).call(zoomRef.current.behavior.scaleBy, 1 / 1.3);
  };

  const handleReset = () => {
    zoomRef.current?.fit();
  };

  // 空数据兜底
  if (!layout) {
    return (
      <EmptyState
        title="还没有技能"
        description="添加技能后将在这里展示技能树图谱"
      />
    );
  }

  const { nodes, links, categoryColor, height } = layout;

  return (
    <div className="relative w-full">
      {/* 缩放控制 */}
      <div className="absolute right-3 top-3 z-10 flex flex-col gap-1.5 rounded-lg border border-slate-200 bg-white/90 p-1.5 shadow-sm backdrop-blur">
        <button
          type="button"
          onClick={handleZoomIn}
          className="flex h-8 w-8 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100 hover:text-brand-600"
          aria-label="放大"
          title="放大"
        >
          <Plus className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={handleZoomOut}
          className="flex h-8 w-8 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100 hover:text-brand-600"
          aria-label="缩小"
          title="缩小"
        >
          <Minus className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={handleReset}
          className="flex h-8 w-8 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100 hover:text-brand-600"
          aria-label="重置视图"
          title="重置视图"
        >
          <RotateCcw className="h-4 w-4" />
        </button>
      </div>

      {/* 分类图例 */}
      <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-1">
        {Array.from(categoryColor.entries()).map(([cat, color]) => (
          <span key={cat} className="inline-flex items-center gap-1 text-xs text-slate-500">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: color }}
            />
            {cat}
          </span>
        ))}
      </div>

      <svg
        ref={svgRef}
        width="100%"
        height={height}
        className="block touch-none select-none rounded-xl border border-slate-200 bg-slate-50/40"
        style={{ minHeight: MIN_HEIGHT }}
      >
        {/* 透明背景层，确保空白区域也可拖拽平移 */}
        <rect
          x={0}
          y={0}
          width="100%"
          height="100%"
          fill="transparent"
          pointerEvents="all"
        />
        <g ref={gRef}>
          {/* 连接线 */}
          {links.map((link, i) => (
            <path
              key={`link-${i}`}
              d={linkPath(link.source, link.target)}
              fill="none"
              stroke="#cbd5e1"
              strokeWidth={1.5}
            />
          ))}
          {/* 节点 */}
          {nodes.map((node) => {
            const color =
              categoryColor.get(node.data.category || "未分类") ??
              CATEGORY_PALETTE[0];
            const name = truncateLabel(node.data.name, NODE_WIDTH - 24);
            return (
              <g
                key={node.data.id}
                transform={`translate(${node.y},${node.x})`}
                className="cursor-pointer"
                onClick={() => onNodeClick(node.data)}
              >
                <rect
                  x={-NODE_WIDTH / 2}
                  y={-NODE_HEIGHT / 2}
                  width={NODE_WIDTH}
                  height={NODE_HEIGHT}
                  rx={9}
                  ry={9}
                  fill={color}
                  fillOpacity={0.12}
                  stroke={color}
                  strokeWidth={1.5}
                />
                <text
                  x={-NODE_WIDTH / 2 + 12}
                  y={-3}
                  fontSize={13}
                  fontWeight={600}
                  fill="#1e293b"
                  dominantBaseline="middle"
                >
                  {name}
                </text>
                <text
                  x={-NODE_WIDTH / 2 + 12}
                  y={13}
                  fontSize={11}
                  fontWeight={500}
                  fill={color}
                  dominantBaseline="middle"
                >
                  {`Lv.${node.data.level}`}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
      <p className="mt-2 text-xs text-slate-400">
        拖拽平移 · 滚轮缩放 · 点击节点编辑
      </p>
    </div>
  );
}
