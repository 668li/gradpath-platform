"use client";

import { Fragment, useMemo, useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  BookOpen,
  ExternalLink,
  Target,
  Info,
  ArrowRight,
  LayoutGrid,
  Radar as RadarIcon,
  Sparkles,
  Lightbulb,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge, Select } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useApi } from "@/lib/api";
import { getMockSkillMap } from "@/lib/mock/skill-map-mock";
import { TARGET_ROLES, type SkillGap, type SkillGapStatus, type SkillMap } from "@/types/skills";

// ===== 状态配置 =====
interface StatusConfig {
  label: string;
  badgeColor: "green" | "amber" | "red";
  borderColor: string;
  icon: typeof CheckCircle2;
  iconColor: string;
  dotColor: string;
}

const STATUS_CONFIG: Record<SkillGapStatus, StatusConfig> = {
  mastered: {
    label: "已掌握",
    badgeColor: "green",
    borderColor: "border-brand-300",
    icon: CheckCircle2,
    iconColor: "text-brand-600",
    dotColor: "bg-brand-500",
  },
  needs_improvement: {
    label: "需提升",
    badgeColor: "amber",
    borderColor: "border-amber-300",
    icon: AlertTriangle,
    iconColor: "text-amber-500",
    dotColor: "bg-amber-500",
  },
  needs_new: {
    label: "需新增",
    badgeColor: "red",
    borderColor: "border-red-300",
    icon: XCircle,
    iconColor: "text-red-500",
    dotColor: "bg-red-500",
  },
};

type TabKey = "all" | SkillGapStatus;

const TABS: { key: TabKey; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "mastered", label: "已掌握" },
  { key: "needs_improvement", label: "需提升" },
  { key: "needs_new", label: "需新增" },
];

// ===== 技能迁移映射（增强1：灵感来源 LinkedIn Career Explorer）=====
// 每个目标岗位预设 8 个核心技能，标注迁移来源与迁移难度
type TransferDifficulty = "low" | "medium" | "high";

const DIFFICULTY_LABEL: Record<TransferDifficulty, string> = {
  low: "低",
  medium: "中",
  high: "高",
};

const DIFFICULTY_COLOR: Record<TransferDifficulty, "green" | "amber" | "red"> = {
  low: "green",
  medium: "amber",
  high: "red",
};

const SKILL_TRANSFER_MAP: Record<string, Record<string, { from: string; difficulty: TransferDifficulty }>> = {
  "前端工程师": {
    "React": { from: "HTML/CSS", difficulty: "low" },
    "TypeScript": { from: "JavaScript", difficulty: "low" },
    "Node.js": { from: "JavaScript", difficulty: "medium" },
    "Webpack": { from: "JavaScript", difficulty: "medium" },
    "Vue": { from: "HTML/CSS", difficulty: "medium" },
    "性能优化": { from: "JavaScript", difficulty: "high" },
    "微前端": { from: "React", difficulty: "high" },
    "可视化(D3/Echarts)": { from: "JavaScript", difficulty: "medium" },
  },
  "后端工程师": {
    "Java": { from: "Python", difficulty: "medium" },
    "Go": { from: "Python", difficulty: "medium" },
    "MySQL": { from: "SQL", difficulty: "low" },
    "Redis": { from: "MySQL", difficulty: "medium" },
    "Kafka": { from: "MySQL", difficulty: "high" },
    "Docker": { from: "Linux", difficulty: "medium" },
    "Kubernetes": { from: "Docker", difficulty: "high" },
    "分布式系统": { from: "MySQL", difficulty: "high" },
  },
  "全栈工程师": {
    "React": { from: "HTML/CSS", difficulty: "low" },
    "Node.js": { from: "JavaScript", difficulty: "medium" },
    "TypeScript": { from: "JavaScript", difficulty: "low" },
    "MySQL": { from: "SQL", difficulty: "low" },
    "Docker": { from: "Linux", difficulty: "medium" },
    "DevOps/CI": { from: "Docker", difficulty: "medium" },
    "GraphQL": { from: "React", difficulty: "medium" },
    "AWS/云服务": { from: "Docker", difficulty: "high" },
  },
  "数据分析师": {
    "Python": { from: "Excel", difficulty: "low" },
    "SQL": { from: "Excel", difficulty: "low" },
    "统计学": { from: "数学", difficulty: "medium" },
    "Pandas/NumPy": { from: "Python", difficulty: "low" },
    "数据可视化": { from: "Excel", difficulty: "medium" },
    "机器学习": { from: "Python", difficulty: "high" },
    "Tableau/PowerBI": { from: "Excel", difficulty: "medium" },
    "A/B 测试": { from: "统计学", difficulty: "medium" },
  },
  "产品经理": {
    "用户调研": { from: "沟通协作", difficulty: "low" },
    "需求分析": { from: "逻辑思维", difficulty: "low" },
    "原型设计": { from: "Axure/Figma", difficulty: "low" },
    "数据分析": { from: "Excel", difficulty: "medium" },
    "竞品分析": { from: "逻辑思维", difficulty: "low" },
    "PRD撰写": { from: "逻辑思维", difficulty: "medium" },
    "A/B 测试": { from: "数据分析", difficulty: "medium" },
    "增长黑客": { from: "数据分析", difficulty: "high" },
  },
  "UI设计师": {
    "Figma": { from: "Photoshop", difficulty: "low" },
    "Sketch": { from: "Photoshop", difficulty: "low" },
    "色彩理论": { from: "审美能力", difficulty: "medium" },
    "排版设计": { from: "审美能力", difficulty: "medium" },
    "交互设计": { from: "逻辑思维", difficulty: "medium" },
    "动效设计": { from: "Figma", difficulty: "high" },
    "设计系统": { from: "Figma", difficulty: "high" },
    "3D 建模": { from: "Photoshop", difficulty: "high" },
  },
  "考研方向": {
    "英语阅读": { from: "英语基础", difficulty: "medium" },
    "英语写作": { from: "英语阅读", difficulty: "medium" },
    "政治理论": { from: "时政热点", difficulty: "medium" },
    "数学一": { from: "数学", difficulty: "high" },
    "专业课": { from: "学科基础", difficulty: "medium" },
    "文献阅读": { from: "英语阅读", difficulty: "medium" },
    "复试表达": { from: "沟通协作", difficulty: "low" },
    "英语听力": { from: "英语阅读", difficulty: "medium" },
  },
  "公务员方向": {
    "行测-言语": { from: "阅读理解", difficulty: "low" },
    "行测-数量": { from: "数学", difficulty: "high" },
    "行测-判断": { from: "逻辑思维", difficulty: "medium" },
    "行测-资料": { from: "Excel", difficulty: "low" },
    "申论": { from: "文字表达", difficulty: "medium" },
    "时政热点": { from: "通识积累", difficulty: "medium" },
    "面试表达": { from: "沟通协作", difficulty: "low" },
    "政策理解": { from: "时政热点", difficulty: "medium" },
  },
};

// ===== 能力矩阵数据（增强3：灵感来源 stride-so/matrix）=====
interface CompetencyMatrixData {
  levels: string[];
  categories: { name: string; skills: string[] }[];
  requirements: Record<string, string>;
}

const COMPETENCY_MATRIX: CompetencyMatrixData = {
  levels: ["初级", "中级", "高级", "专家"],
  categories: [
    { name: "技术技能", skills: ["编程基础", "框架使用", "系统设计", "性能优化", "架构能力"] },
    { name: "可迁移技能", skills: ["沟通表达", "团队协作", "项目管理", "逻辑思维", "学习能力"] },
  ],
  requirements: {
    "初级-编程基础": "掌握基本语法，能独立完成简单功能",
    "中级-编程基础": "熟悉最佳实践，能 review 他人代码",
    "高级-编程基础": "精通语言特性，能解决疑难问题",
    "专家-编程基础": "能设计语言特性，主导技术演进",
    "初级-框架使用": "能按文档使用框架完成功能",
    "中级-框架使用": "理解框架原理，能定制扩展",
    "高级-框架使用": "能主导框架选型与最佳实践",
    "专家-框架使用": "能贡献框架生态或自研框架",
    "初级-系统设计": "能设计单模块功能流程",
    "中级-系统设计": "能设计中等复杂度的子系统",
    "高级-系统设计": "能设计高可用分布式系统",
    "专家-系统设计": "能定义系统架构演进路线",
    "初级-性能优化": "能识别明显的性能问题",
    "中级-性能优化": "能使用工具定位瓶颈并优化",
    "高级-性能优化": "能构建性能保障体系",
    "专家-性能优化": "能预判并预防性能风险",
    "初级-架构能力": "理解常见架构模式含义",
    "中级-架构能力": "能在项目中合理应用架构模式",
    "高级-架构能力": "能主导大型项目架构设计",
    "专家-架构能力": "能定义企业级架构标准与规范",
    "初级-沟通表达": "能清晰表达自己的想法",
    "中级-沟通表达": "能跨团队协调沟通",
    "高级-沟通表达": "能主导技术布道与对外演讲",
    "专家-沟通表达": "能影响行业认知与共识",
    "初级-团队协作": "能配合团队完成任务",
    "中级-团队协作": "能带新人，推动协作流程",
    "高级-团队协作": "能管理跨职能团队",
    "专家-团队协作": "能塑造团队文化与组织效能",
    "初级-项目管理": "能拆解并跟进自己的任务",
    "中级-项目管理": "能管理小型项目全流程",
    "高级-项目管理": "能管理复杂多线项目与风险",
    "专家-项目管理": "能建立项目管理体系与标准",
    "初级-逻辑思维": "能结构化分析简单问题",
    "中级-逻辑思维": "能用框架拆解复杂问题",
    "高级-逻辑思维": "能跨领域迁移方法论",
    "专家-逻辑思维": "能构建新的分析与决策框架",
    "初级-学习能力": "能按教程自学新技能",
    "中级-学习能力": "能高效提炼知识体系",
    "高级-学习能力": "能快速跨界并产出成果",
    "专家-学习能力": "能持续引领前沿并赋能他人",
  },
};

// ===== SVG 雷达图 =====
function SkillRadarChart({ skills }: { skills: SkillGap[] }) {
  // 取前 8 个技能作为雷达图维度
  const dimensions = useMemo(() => skills.slice(0, 8), [skills]);

  if (dimensions.length < 3) {
    return (
      <EmptyState
        title="维度不足"
        description="至少需要 3 项技能才能绘制雷达图"
        className="py-8"
      />
    );
  }

  const size = 320;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 110;
  const levels = 5; // 20, 40, 60, 80, 100
  const n = dimensions.length;

  // 计算多边形顶点坐标
  const pointAt = (index: number, value: number) => {
    // 从顶部开始,顺时针
    const angle = (Math.PI * 2 * index) / n - Math.PI / 2;
    const r = (value / 100) * radius;
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  };

  // 网格多边形点
  const gridPolygons = Array.from({ length: levels }, (_, levelIdx) => {
    const levelValue = ((levelIdx + 1) / levels) * 100;
    return dimensions
      .map((_, i) => {
        const p = pointAt(i, levelValue);
        return `${p.x},${p.y}`;
      })
      .join(" ");
  });

  // 轴线
  const axisLines = dimensions.map((_, i) => {
    const p = pointAt(i, 100);
    return { x1: cx, y1: cy, x2: p.x, y2: p.y };
  });

  // 当前水平多边形
  const currentPoints = dimensions
    .map((s, i) => {
      const p = pointAt(i, s.current_level);
      return `${p.x},${p.y}`;
    })
    .join(" ");

  // 目标要求多边形
  const targetPoints = dimensions
    .map((s, i) => {
      const p = pointAt(i, s.required_level);
      return `${p.x},${p.y}`;
    })
    .join(" ");

  // 标签位置（在顶点外侧）
  const labels = dimensions.map((s, i) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const labelR = radius + 22;
    const x = cx + labelR * Math.cos(angle);
    const y = cy + labelR * Math.sin(angle);
    return { x, y, name: s.skill_name, current: s.current_level, required: s.required_level };
  });

  return (
    <div className="w-full flex flex-col items-center">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        className="w-full max-w-[360px] h-auto"
        role="img"
        aria-label="能力地图雷达图：当前水平 vs 目标要求"
      >
        {/* 网格 */}
        {gridPolygons.map((points, idx) => (
          <polygon
            key={`grid-${idx}`}
            points={points}
            fill="none"
            stroke="var(--color-paper-300, #eae6da)"
            strokeWidth={1}
          />
        ))}

        {/* 轴线 */}
        {axisLines.map((line, i) => (
          <line
            key={`axis-${i}`}
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            stroke="var(--color-paper-300, #eae6da)"
            strokeWidth={1}
          />
        ))}

        {/* 目标要求多边形（红色虚线） */}
        <polygon
          points={targetPoints}
          fill="rgba(239, 68, 68, 0.05)"
          stroke="#ef4444"
          strokeWidth={1.5}
          strokeDasharray="4 3"
        />

        {/* 当前水平多边形（品牌色半透明） */}
        <polygon
          points={currentPoints}
          fill="rgba(13, 113, 89, 0.25)"
          stroke="#0d7159"
          strokeWidth={2}
        />

        {/* 当前水平顶点 */}
        {dimensions.map((s, i) => {
          const p = pointAt(i, s.current_level);
          return (
            <circle
              key={`cur-${i}`}
              cx={p.x}
              cy={p.y}
              r={3}
              fill="#0d7159"
              stroke="#fff"
              strokeWidth={1}
            />
          );
        })}

        {/* 标签 */}
        {labels.map((label, i) => {
          // 根据位置调整 text-anchor
          const dx = label.x - cx;
          let anchor: "start" | "middle" | "end" = "middle";
          if (Math.abs(dx) > 15) {
            anchor = dx > 0 ? "start" : "end";
          }
          return (
            <text
              key={`label-${i}`}
              x={label.x}
              y={label.y}
              textAnchor={anchor}
              dominantBaseline="middle"
              className="fill-ink-600"
              style={{ fontSize: 10, fontWeight: 500 }}
            >
              {label.name}
            </text>
          );
        })}
      </svg>

      {/* 图例 */}
      <div className="flex items-center gap-4 mt-2 text-xs text-ink-500">
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm bg-brand-600/25 border-2 border-brand-600" />
          <span>当前水平</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm border-2 border-dashed border-red-500" />
          <span>目标要求</span>
        </div>
      </div>
    </div>
  );
}

// ===== 技能卡片 =====
function SkillCard({ skill }: { skill: SkillGap }) {
  const config = STATUS_CONFIG[skill.status];
  const Icon = config.icon;
  const isNeedsNew = skill.status === "needs_new";

  return (
    <div
      className={cn(
        "rounded-lg border-2 bg-white p-4 shadow-card transition-shadow hover:shadow-card-hover",
        config.borderColor,
      )}
    >
      {/* 头部：技能名 + 状态 */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <Icon className={cn("h-4 w-4 shrink-0", config.iconColor)} />
            <h4 className="font-medium text-ink-800 truncate text-sm">
              {skill.skill_name}
            </h4>
          </div>
          <div className="flex items-center gap-1.5 mt-1">
            <Badge color={config.badgeColor}>{config.label}</Badge>
            <span className="text-xs text-ink-400">
              {skill.category === "hard" ? "硬技能" : "软技能"}
            </span>
          </div>
        </div>
      </div>

      {/* 水平数值：当前 / 要求 */}
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-xs text-ink-500">
          当前 <span className="font-semibold text-ink-800">{skill.current_level}</span>
          <span className="text-ink-300 mx-1">/</span>
          <span className="font-semibold text-ink-800">{skill.required_level}</span>
          <span className="text-ink-400 ml-1">要求</span>
        </span>
        {skill.gap > 0 && (
          <span className="text-xs text-red-500 font-medium">差距 {skill.gap}</span>
        )}
        {skill.gap <= 0 && (
          <span className="text-xs text-brand-600 font-medium">
            {skill.gap === 0 ? "达标" : `超出 ${-skill.gap}`}
          </span>
        )}
      </div>

      {/* 双轨进度条：目标(背景轨道) + 当前(前景) */}
      <div className="relative h-2.5 rounded-full bg-red-100 overflow-hidden">
        {/* 目标要求轨道 */}
        <div
          className="absolute inset-y-0 left-0 bg-red-200/60"
          style={{ width: `${skill.required_level}%` }}
        />
        {/* 当前水平 */}
        <div
          className={cn(
            "absolute inset-y-0 left-0 rounded-full transition-all",
            skill.status === "mastered" && "bg-brand-500",
            skill.status === "needs_improvement" && "bg-amber-500",
            skill.status === "needs_new" && "bg-red-500",
          )}
          style={{ width: `${Math.max(skill.current_level, isNeedsNew ? 0 : 2)}%` }}
        />
      </div>

      {/* 学习资源 / 开始学习按钮 */}
      {isNeedsNew && (
        <div className="mt-3 space-y-2">
          {skill.learning_resources && skill.learning_resources.length > 0 ? (
            <div className="space-y-1">
              {skill.learning_resources.slice(0, 2).map((res, idx) => (
                <a
                  key={idx}
                  href={res.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs text-brand-600 hover:text-brand-700 hover:underline"
                >
                  <BookOpen className="h-3 w-3 shrink-0" />
                  <span className="truncate">{res.title}</span>
                  <ExternalLink className="h-3 w-3 shrink-0" />
                </a>
              ))}
            </div>
          ) : (
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-md bg-red-50 px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-100 transition-colors"
            >
              <BookOpen className="h-3 w-3" />
              开始学习
            </button>
          )}
        </div>
      )}

      {/* 需提升的学习资源 */}
      {skill.status === "needs_improvement" && skill.learning_resources && skill.learning_resources.length > 0 && (
        <div className="mt-3 space-y-1">
          {skill.learning_resources.slice(0, 2).map((res, idx) => (
            <a
              key={idx}
              href={res.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs text-amber-600 hover:text-amber-700 hover:underline"
            >
              <BookOpen className="h-3 w-3 shrink-0" />
              <span className="truncate">{res.title}</span>
              <ExternalLink className="h-3 w-3 shrink-0" />
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

// ===== 统计卡片 =====
function StatCard({
  count,
  label,
  icon: Icon,
  iconBg,
  iconColor,
}: {
  count: number;
  label: string;
  icon: typeof CheckCircle2;
  iconBg: string;
  iconColor: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-paper-300 bg-white p-3">
      <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg", iconBg)}>
        <Icon className={cn("h-4 w-4", iconColor)} />
      </div>
      <div>
        <div className="text-xl font-semibold text-ink-800 leading-none">{count}</div>
        <div className="text-xs text-ink-400 mt-1">{label}</div>
      </div>
    </div>
  );
}

// ===== 技能迁移路径（增强1：灵感来源 LinkedIn Career Explorer）=====
interface TransferItem {
  targetSkill: string;
  from: string;
  difficulty: TransferDifficulty;
  status: SkillGapStatus;
}

function computeTransferPath(
  targetRole: string,
  userSkills: SkillGap[],
): TransferItem[] {
  const transferMap = SKILL_TRANSFER_MAP[targetRole] ?? {};
  const userSkillByName = new Map(userSkills.map((s) => [s.skill_name, s]));

  return Object.entries(transferMap).map(([targetSkill, { from, difficulty }]) => {
    const userSkill = userSkillByName.get(targetSkill);
    const fromSkill = userSkillByName.get(from);

    let status: SkillGapStatus;
    if (userSkill) {
      // 用户已有目标技能：已掌握或正在学习
      status = userSkill.status === "mastered" ? "mastered" : "needs_improvement";
    } else if (fromSkill) {
      // 用户有来源技能基础：可迁移但需提升
      status = fromSkill.current_level > 0 ? "needs_improvement" : "needs_new";
    } else {
      status = "needs_new";
    }

    return { targetSkill, from, difficulty, status };
  });
}

function TransferPathItem({ item }: { item: TransferItem }) {
  const statusConfig = STATUS_CONFIG[item.status];
  const Icon = statusConfig.icon;

  return (
    <div
      className={cn(
        "rounded-lg border bg-white p-3 transition-shadow hover:shadow-card-hover",
        statusConfig.borderColor,
      )}
    >
      <div className="flex items-center gap-1.5 mb-2">
        <Icon className={cn("h-3.5 w-3.5 shrink-0", statusConfig.iconColor)} />
        <span className="text-sm font-medium text-ink-800 truncate flex-1">
          {item.targetSkill}
        </span>
        <Badge color={DIFFICULTY_COLOR[item.difficulty]}>
          难度 {DIFFICULTY_LABEL[item.difficulty]}
        </Badge>
      </div>
      <div className="flex items-center gap-1.5 text-xs text-ink-500">
        <span className="truncate">{item.from}</span>
        <ArrowRight className="h-3 w-3 shrink-0 text-ink-300" />
        <span className="truncate font-medium text-ink-700">{item.targetSkill}</span>
      </div>
    </div>
  );
}

function SkillTransferView({
  targetRole,
  userSkills,
}: {
  targetRole: string;
  userSkills: SkillGap[];
}) {
  const transfers = useMemo(
    () => computeTransferPath(targetRole, userSkills),
    [targetRole, userSkills],
  );

  const mastered = transfers.filter((t) => t.status === "mastered");
  const needsImprovement = transfers.filter((t) => t.status === "needs_improvement");
  const needsNew = transfers.filter((t) => t.status === "needs_new");

  // 迁移建议：在"需提升"和"需新增"中挑难度最低的
  const suggestion = useMemo(() => {
    const candidates = [...needsImprovement, ...needsNew];
    const order: Record<TransferDifficulty, number> = { low: 0, medium: 1, high: 2 };
    return candidates.sort((a, b) => order[a.difficulty] - order[b.difficulty])[0];
  }, [needsImprovement, needsNew]);

  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-1">
        <Sparkles className="h-4 w-4 text-brand-600 shrink-0" />
        <h3 className="font-semibold text-ink-800 text-sm">
          技能迁移路径
        </h3>
        <span className="text-xs text-ink-400">→ {targetRole}</span>
      </div>
      <p className="text-xs text-ink-400 mb-4">
        从你现有的技能出发，迁移到目标岗位所需的核心技能
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 可迁移 */}
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-brand-600" />
            <span className="text-xs font-medium text-brand-700">
              可迁移（{mastered.length}）
            </span>
          </div>
          <div className="space-y-2">
            {mastered.length === 0 ? (
              <p className="text-xs text-ink-300 py-2">暂无</p>
            ) : (
              mastered.map((item) => (
                <TransferPathItem key={item.targetSkill} item={item} />
              ))
            )}
          </div>
        </div>

        {/* 需提升 */}
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
            <span className="text-xs font-medium text-amber-700">
              需提升（{needsImprovement.length}）
            </span>
          </div>
          <div className="space-y-2">
            {needsImprovement.length === 0 ? (
              <p className="text-xs text-ink-300 py-2">暂无</p>
            ) : (
              needsImprovement.map((item) => (
                <TransferPathItem key={item.targetSkill} item={item} />
              ))
            )}
          </div>
        </div>

        {/* 需新增 */}
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <XCircle className="h-3.5 w-3.5 text-red-500" />
            <span className="text-xs font-medium text-red-700">
              需新增（{needsNew.length}）
            </span>
          </div>
          <div className="space-y-2">
            {needsNew.length === 0 ? (
              <p className="text-xs text-ink-300 py-2">暂无</p>
            ) : (
              needsNew.map((item) => (
                <TransferPathItem key={item.targetSkill} item={item} />
              ))
            )}
          </div>
        </div>
      </div>

      {/* 迁移建议 */}
      {suggestion && (
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-brand-200 bg-brand-50/60 p-3">
          <Lightbulb className="h-4 w-4 text-brand-600 shrink-0 mt-0.5" />
          <p className="text-xs text-ink-700 leading-relaxed">
            从你现有的
            <span className="font-semibold text-brand-700 mx-1">
              「{suggestion.from}」
            </span>
            出发，建议先学习
            <span className="font-semibold text-brand-700 mx-1">
              「{suggestion.targetSkill}」
            </span>
            （迁移难度
            <span className="font-semibold mx-0.5">
              {DIFFICULTY_LABEL[suggestion.difficulty]}
            </span>
            ）
            {needsNew.length > 0 || needsImprovement.length > 1
              ? "，再逐步攻克其余缺口。"
              : "，即可覆盖目标岗位核心要求。"}
          </p>
        </div>
      )}
    </div>
  );
}

// ===== 能力矩阵视图（增强3：灵感来源 stride-so/matrix）=====
function CompetencyMatrixView({ currentLevel }: { currentLevel: number }) {
  const [selectedCell, setSelectedCell] = useState<{
    skill: string;
    levelIdx: number;
  } | null>(null);

  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-1">
        <LayoutGrid className="h-4 w-4 text-brand-600 shrink-0" />
        <h3 className="font-semibold text-ink-800 text-sm">能力矩阵</h3>
        <Badge color="blue">当前级别：{COMPETENCY_MATRIX.levels[currentLevel]}</Badge>
      </div>
      <p className="text-xs text-ink-400 mb-4">
        点击格子查看"从当前级别到下一级别需要什么"，蓝色边框标记你的当前级别
      </p>

      <div className="overflow-x-auto -mx-2 px-2">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-white text-left text-ink-500 font-medium p-2 min-w-[100px] border-b border-paper-300">
                能力
              </th>
              {COMPETENCY_MATRIX.levels.map((level, i) => (
                <th
                  key={level}
                  className={cn(
                    "p-2 text-center font-medium border-b border-paper-300 min-w-[160px]",
                    i === currentLevel ? "text-brand-700" : "text-ink-500",
                  )}
                >
                  {level}
                  {i === currentLevel && (
                    <span className="block text-[10px] text-brand-500 mt-0.5">← 你在这里</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {COMPETENCY_MATRIX.categories.map((cat) => (
              <Fragment key={cat.name}>
                <tr>
                  <td
                    colSpan={COMPETENCY_MATRIX.levels.length + 1}
                    className="bg-paper-50 text-left text-ink-700 font-semibold p-2 text-xs border-b border-paper-200"
                  >
                    {cat.name}
                  </td>
                </tr>
                {cat.skills.map((skill) => (
                  <tr key={skill} className="hover:bg-paper-50/50">
                    <td className="sticky left-0 z-10 bg-white text-left text-ink-700 font-medium p-2 border-b border-paper-100 whitespace-nowrap">
                      {skill}
                    </td>
                    {COMPETENCY_MATRIX.levels.map((level, i) => {
                      const key = `${level}-${skill}`;
                      const requirement = COMPETENCY_MATRIX.requirements[key] ?? "—";
                      const isSelected =
                        selectedCell?.skill === skill &&
                        selectedCell?.levelIdx === i;
                      const isCurrentLevel = i === currentLevel;

                      return (
                        <td
                          key={key}
                          onClick={() =>
                            setSelectedCell({ skill, levelIdx: i })
                          }
                          className={cn(
                            "p-2 text-left text-ink-600 border-b border-paper-100 cursor-pointer transition-colors align-top",
                            isSelected && "bg-brand-100 ring-2 ring-brand-400",
                            !isSelected && isCurrentLevel && "bg-brand-50/40",
                            !isSelected && !isCurrentLevel && "hover:bg-paper-50",
                          )}
                        >
                          {requirement}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* 选中格子的详情：从当前级别到下一级别 */}
      {selectedCell && (
        <div className="mt-4 rounded-lg border border-paper-300 bg-paper-50/60 p-3">
          <div className="flex items-center gap-2 mb-2">
            <ArrowRight className="h-3.5 w-3.5 text-brand-600" />
            <span className="text-sm font-medium text-ink-800">
              {selectedCell.skill} · {COMPETENCY_MATRIX.levels[selectedCell.levelIdx]}
            </span>
          </div>
          <p className="text-xs text-ink-600 leading-relaxed mb-2">
            <span className="text-ink-400">本级要求：</span>
            {COMPETENCY_MATRIX.requirements[
              `${COMPETENCY_MATRIX.levels[selectedCell.levelIdx]}-${selectedCell.skill}`
            ] ?? "—"}
          </p>
          {selectedCell.levelIdx < COMPETENCY_MATRIX.levels.length - 1 && (
            <p className="text-xs text-ink-600 leading-relaxed">
              <span className="text-brand-600 font-medium">下一级别：</span>
              {COMPETENCY_MATRIX.requirements[
                `${COMPETENCY_MATRIX.levels[selectedCell.levelIdx + 1]}-${selectedCell.skill}`
              ] ?? "—"}
            </p>
          )}
          {selectedCell.levelIdx === COMPETENCY_MATRIX.levels.length - 1 && (
            <p className="text-xs text-brand-600 font-medium">已达最高级别 🎉</p>
          )}
        </div>
      )}
    </div>
  );
}

// ===== 主组件 =====
export function SkillMapView() {
  const [targetRole, setTargetRole] = useState<string>(TARGET_ROLES[0]);
  const [activeTab, setActiveTab] = useState<TabKey>("all");
  // 增强3：子视图切换 —— 雷达视图 | 能力矩阵
  const [subView, setSubView] = useState<"radar" | "matrix">("radar");

  // SWR 拉取能力地图数据
  const url = `/api/skills/map?target_role=${encodeURIComponent(targetRole)}`;
  const { data, error, isLoading } = useApi<SkillMap>(url);

  // mock 假数据兜底仅在开发环境启用（守「数据必须真实」红线）；
  // 生产环境接口失败时直接显示错误态，绝不展示演示数据。
  const isDev = process.env.NODE_ENV === "development";
  const usingMock = isDev && !!error && !data;
  const skillMap = data ?? (isDev && error ? getMockSkillMap(targetRole) : null);

  if (isLoading) {
    return <LoadingState text="加载能力地图…" />;
  }

  if (!skillMap) {
    return error ? (
      <EmptyState
        title="能力地图加载失败"
        description="数据获取失败，请稍后重试或检查后端服务状态"
      />
    ) : (
      <EmptyState
        title="暂无能力地图数据"
        description="请先添加技能或选择目标岗位"
      />
    );
  }

  // 按 Tab 筛选
  const filteredSkills = activeTab === "all"
    ? skillMap.skills
    : skillMap.skills.filter((s) => s.status === activeTab);

  const overallMatch = skillMap.overall_match;

  // 增强3：根据整体匹配度推导用户当前能力级别（0=初级 ~ 3=专家）
  const currentLevel =
    overallMatch < 40 ? 0 : overallMatch < 70 ? 1 : overallMatch < 90 ? 2 : 3;

  return (
    <div className="space-y-5">
      {/* 顶部：目标岗位选择 + 整体匹配度 */}
      <div className="card p-5">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-3">
            <Target className="h-5 w-5 text-brand-600 shrink-0" />
            <div>
              <h2 className="font-display text-lg font-semibold text-ink-800">
                能力地图
              </h2>
              <p className="text-xs text-ink-400 mt-0.5">
                对比当前技能与目标岗位要求,识别差距
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {usingMock && (
              <Badge color="amber" className="flex items-center gap-1">
                <Info className="h-3 w-3" />
                演示数据
              </Badge>
            )}
            <div className="flex items-center gap-2">
              <label htmlFor="target-role-select" className="text-sm text-ink-500 whitespace-nowrap">
                目标岗位
              </label>
              <Select
                id="target-role-select"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                className="w-40"
              >
                {TARGET_ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        </div>

        {/* 整体匹配度进度条 */}
        <div className="mt-4">
          <div className="flex items-baseline justify-between mb-1.5">
            <span className="text-sm text-ink-500">整体匹配度</span>
            <span className="text-lg font-semibold text-ink-800">
              {overallMatch}
              <span className="text-sm text-ink-400 ml-0.5">%</span>
            </span>
          </div>
          <div className="h-2.5 rounded-full bg-paper-200 overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                overallMatch >= 70
                  ? "bg-brand-500"
                  : overallMatch >= 50
                    ? "bg-amber-500"
                    : "bg-red-500",
              )}
              style={{ width: `${overallMatch}%` }}
            />
          </div>
        </div>

        {/* 增强3：子视图切换 —— 雷达视图 | 能力矩阵 */}
        <div className="mt-4 flex items-center gap-1 border-b border-paper-200 pb-2">
          <button
            type="button"
            onClick={() => setSubView("radar")}
            className={cn(
              "inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              subView === "radar"
                ? "bg-brand-600 text-white"
                : "text-ink-500 hover:bg-paper-100",
            )}
          >
            <RadarIcon className="h-3.5 w-3.5" /> 雷达视图
          </button>
          <button
            type="button"
            onClick={() => setSubView("matrix")}
            className={cn(
              "inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              subView === "matrix"
                ? "bg-brand-600 text-white"
                : "text-ink-500 hover:bg-paper-100",
            )}
          >
            <LayoutGrid className="h-3.5 w-3.5" /> 能力矩阵
          </button>
        </div>
      </div>

      {/* 雷达视图（默认）：雷达图 + 统计卡片 + Tab 筛选 + 技能卡片 */}
      {subView === "radar" && (
        <>
          {/* 雷达图 + 统计卡片 */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
            <div className="card p-5 lg:col-span-3">
              <h3 className="font-semibold text-ink-800 mb-3 text-sm">
                当前水平 vs 目标要求
              </h3>
              <SkillRadarChart skills={skillMap.skills} />
            </div>

            <div className="lg:col-span-2 space-y-3">
              <StatCard
                count={skillMap.mastered_count}
                label="已掌握"
                icon={CheckCircle2}
                iconBg="bg-brand-100"
                iconColor="text-brand-600"
              />
              <StatCard
                count={skillMap.needs_improvement_count}
                label="需提升"
                icon={AlertTriangle}
                iconBg="bg-amber-100"
                iconColor="text-amber-500"
              />
              <StatCard
                count={skillMap.needs_new_count}
                label="需新增"
                icon={XCircle}
                iconBg="bg-red-100"
                iconColor="text-red-500"
              />
            </div>
          </div>

          {/* Tab 筛选 */}
          <div className="flex items-center gap-1 border-b border-paper-300">
            {TABS.map((tab) => {
              const count =
                tab.key === "all"
                  ? skillMap.skills.length
                  : skillMap.skills.filter((s) => s.status === tab.key).length;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveTab(tab.key)}
                  className={cn(
                    "relative px-4 py-2 text-sm font-medium transition-colors -mb-px border-b-2",
                    activeTab === tab.key
                      ? "border-brand-600 text-brand-700"
                      : "border-transparent text-ink-400 hover:text-ink-600",
                  )}
                >
                  {tab.label}
                  <span
                    className={cn(
                      "ml-1.5 inline-flex items-center justify-center rounded-full px-1.5 py-0.5 text-xs",
                      activeTab === tab.key
                        ? "bg-brand-100 text-brand-700"
                        : "bg-paper-200 text-ink-500",
                    )}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* 技能卡片网格 */}
          {filteredSkills.length === 0 ? (
            <EmptyState
              title="暂无技能"
              description={`当前 Tab 下没有技能`}
              className="py-8"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredSkills.map((skill) => (
                <SkillCard key={skill.skill_id} skill={skill} />
              ))}
            </div>
          )}
        </>
      )}

      {/* 能力矩阵视图（增强3） */}
      {subView === "matrix" && (
        <CompetencyMatrixView currentLevel={currentLevel} />
      )}

      {/* 技能迁移路径（增强1：始终展示在能力地图下方） */}
      <SkillTransferView targetRole={targetRole} userSkills={skillMap.skills} />
    </div>
  );
}
