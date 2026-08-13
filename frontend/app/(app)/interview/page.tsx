"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Send,
  Trash2,
  BarChart3,
  Briefcase,
  Star,
  Gauge,
  Radar as RadarIcon,
  PenLine,
  ListChecks,
  CheckCircle2,
  AlertCircle,
  Lightbulb,
  Sparkles,
} from "lucide-react";
import { interviewApi } from "@/lib/api";
import { Button, Input, Select, Textarea } from "@/components/ui/form-controls";
import { EmptyState } from "@/components/ui/empty";
import { ListSkeleton } from "@/components/ui/skeleton";
import { Pagination } from "@/components/ui/pagination";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";
import {
  INTERVIEW_DIMENSIONS,
  INTERVIEW_DIMENSION_LABEL,
  INTERVIEW_RESULTS,
  INTERVIEW_RESULT_LABEL,
} from "@/lib/constants";
import type {
  CompanyInfo,
  InterviewReport,
  InterviewStats,
  InterviewSubmit,
} from "@/types";

const YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025];

function encodeParam(value: string): string {
  return encodeURIComponent(btoa(unescape(encodeURIComponent(value))));
}

// ===== 增强 1: 8 维面试能力画像 =====
const ABILITY_DIMENSIONS = [
  "技术深度",
  "系统设计",
  "项目经验",
  "沟通表达",
  "逻辑思维",
  "学习能力",
  "团队协作",
  "抗压能力",
] as const;
type AbilityDim = (typeof ABILITY_DIMENSIONS)[number];
type AbilityScores = Record<AbilityDim, number>;

// 基于用户的面试记录计算 8 维分数 (0-10)
function computeAbilityScores(reports: InterviewReport[]): AbilityScores | null {
  if (!reports.length) return null;
  const base: AbilityScores = {
    技术深度: 4.5,
    系统设计: 4.5,
    项目经验: 4.5,
    沟通表达: 4.5,
    逻辑思维: 4.5,
    学习能力: 4.5,
    团队协作: 4.5,
    抗压能力: 4.5,
  };
  // 把面试时被考察过的维度映射到能力维度, 说明用户已经在这些方向有积累
  const dimMap: Record<string, AbilityDim[]> = {
    algorithm: ["技术深度", "逻辑思维"],
    system_design: ["系统设计", "逻辑思维"],
    project_depth: ["项目经验", "技术深度"],
    culture_fit: ["团队协作", "沟通表达"],
    communication: ["沟通表达"],
    domain: ["技术深度", "学习能力"],
    behavior: ["沟通表达", "团队协作"],
  };
  let difficultySum = 0;
  let difficultyCount = 0;
  let roundsSum = 0;
  let roundsCount = 0;
  let offerCount = 0;
  let rejectedCount = 0;
  reports.forEach((r) => {
    r.dimensions.forEach((d) => {
      const dims = dimMap[d];
      dims?.forEach((m) => {
        base[m] = Math.min(10, base[m] + 0.5);
      });
    });
    if (r.difficulty) {
      difficultySum += r.difficulty;
      difficultyCount++;
    }
    if (r.rounds) {
      roundsSum += r.rounds;
      roundsCount++;
    }
    if (r.result === "offer") offerCount++;
    if (r.result === "rejected") rejectedCount++;
  });
  const avgDiff = difficultyCount ? difficultySum / difficultyCount : 3;
  const avgRounds = roundsCount ? roundsSum / roundsCount : 3;
  // 抗压能力: 高难度 + 多轮 = 更强
  base["抗压能力"] = Math.min(10, 4 + (avgDiff - 2) * 1.0 + (avgRounds - 2) * 0.5);
  // 学习能力: 经历越多面试 = 越多复盘学习
  base["学习能力"] = Math.min(10, 4 + reports.length * 0.4);
  // 拿 offer 说明综合表现好
  if (offerCount) {
    (Object.keys(base) as AbilityDim[]).forEach((k) => {
      base[k] = Math.min(10, base[k] + offerCount * 0.25);
    });
  }
  // 失败次数多但仍在尝试 = 抗压能力强
  if (rejectedCount > offerCount) {
    base["抗压能力"] = Math.min(10, base["抗压能力"] + 0.4);
  }
  return base;
}

// SVG 雷达图(参考 components/skills/skill-map-view.tsx 的实现风格)
function AbilityRadar({ scores }: { scores: AbilityScores }) {
  const size = 340;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 110;
  const levels = 5; // 2/4/6/8/10
  const n = ABILITY_DIMENSIONS.length;

  const pointAt = (index: number, value: number) => {
    const angle = (Math.PI * 2 * index) / n - Math.PI / 2;
    const r = (value / 10) * radius;
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  };

  const gridPolygons = Array.from({ length: levels }, (_, i) => {
    const v = ((i + 1) / levels) * 10;
    return ABILITY_DIMENSIONS.map((_, idx) => {
      const p = pointAt(idx, v);
      return `${p.x},${p.y}`;
    }).join(" ");
  });

  const axisLines = ABILITY_DIMENSIONS.map((_, i) => {
    const p = pointAt(i, 10);
    return { x1: cx, y1: cy, x2: p.x, y2: p.y };
  });

  const dataPoints = ABILITY_DIMENSIONS.map((dim, i) => {
    const p = pointAt(i, scores[dim]);
    return `${p.x},${p.y}`;
  }).join(" ");

  const labels = ABILITY_DIMENSIONS.map((dim, i) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const labelR = radius + 24;
    return {
      x: cx + labelR * Math.cos(angle),
      y: cy + labelR * Math.sin(angle),
      name: dim,
      score: scores[dim],
    };
  });

  return (
    <div className="w-full flex flex-col items-center">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        className="w-full max-w-[360px] h-auto"
        role="img"
        aria-label="面试能力画像雷达图"
      >
        {gridPolygons.map((points, i) => (
          <polygon
            key={`grid-${i}`}
            points={points}
            fill="none"
            stroke="var(--color-paper-300, #eae6da)"
            strokeWidth={1}
          />
        ))}
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
        <polygon
          points={dataPoints}
          fill="rgba(13, 113, 89, 0.25)"
          stroke="#0d7159"
          strokeWidth={2}
        />
        {ABILITY_DIMENSIONS.map((dim, i) => {
          const p = pointAt(i, scores[dim]);
          return (
            <circle
              key={`pt-${i}`}
              cx={p.x}
              cy={p.y}
              r={3}
              fill="#0d7159"
              stroke="#fff"
              strokeWidth={1}
            />
          );
        })}
        {labels.map((l, i) => {
          const dx = l.x - cx;
          let anchor: "start" | "middle" | "end" = "middle";
          if (Math.abs(dx) > 15) anchor = dx > 0 ? "start" : "end";
          return (
            <text
              key={`label-${i}`}
              x={l.x}
              y={l.y}
              textAnchor={anchor}
              dominantBaseline="middle"
              className="fill-ink-600"
              style={{ fontSize: 10, fontWeight: 500 }}
            >
              {l.name} {l.score.toFixed(1)}
            </text>
          );
        })}
      </svg>
      <div className="flex items-center gap-4 mt-2 text-xs text-ink-500">
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm bg-brand-600/25 border-2 border-brand-600" />
          <span>我的能力</span>
        </div>
      </div>
    </div>
  );
}

// ===== 增强 4: 半圆仪表盘 =====
function ReadinessGauge({ score }: { score: number }) {
  const size = 220;
  const cx = size / 2;
  const cy = size - 30;
  const radius = 90;
  // 半圆从 180° (左) 经 90° (上) 到 0° (右), polar 角度遵循数学习惯
  const polar = (deg: number) => {
    const rad = (deg * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cy - radius * Math.sin(rad) };
  };
  const clamped = Math.min(100, Math.max(0, score));
  // score=0 → 180°(指向左), score=100 → 0°(指向右)
  const scoreDeg = 180 - (clamped / 100) * 180;
  const bgStart = polar(180);
  const bgEnd = polar(0);
  const bgArc = `M ${bgStart.x} ${bgStart.y} A ${radius} ${radius} 0 0 1 ${bgEnd.x} ${bgEnd.y}`;
  const pStart = polar(180);
  const pEnd = polar(scoreDeg);
  const progressArc = `M ${pStart.x} ${pStart.y} A ${radius} ${radius} 0 0 1 ${pEnd.x} ${pEnd.y}`;
  const needleEnd = polar(scoreDeg);
  const color =
    clamped >= 80 ? "#16a34a" : clamped >= 60 ? "#0d7159" : clamped >= 30 ? "#d97706" : "#dc2626";
  return (
    <div className="flex flex-col items-center">
      <svg
        viewBox={`0 0 ${size} ${size - 10}`}
        className="w-full max-w-[260px] h-auto"
        role="img"
        aria-label="面试准备度仪表盘"
      >
        <path
          d={bgArc}
          fill="none"
          stroke="var(--color-paper-200, #f5f3ec)"
          strokeWidth={12}
          strokeLinecap="round"
        />
        <path
          d={progressArc}
          fill="none"
          stroke={color}
          strokeWidth={12}
          strokeLinecap="round"
        />
        <line
          x1={cx}
          y1={cy}
          x2={needleEnd.x}
          y2={needleEnd.y}
          stroke="#1e293b"
          strokeWidth={2.5}
          strokeLinecap="round"
        />
        <circle cx={cx} cy={cy} r={5} fill="#1e293b" />
        <text
          x={cx}
          y={cy - 32}
          textAnchor="middle"
          style={{ fontSize: 26, fontWeight: 700, fill: color }}
        >
          {Math.round(clamped)}
        </text>
        <text
          x={cx}
          y={cy - 14}
          textAnchor="middle"
          style={{ fontSize: 10, fill: "var(--color-ink-400, #7a7468)" }}
        >
          / 100
        </text>
      </svg>
    </div>
  );
}

// ===== 增强 2: STAR 改写规则引擎 =====
interface StarResult {
  situation: string[];
  task: string[];
  action: string[];
  result: string[];
}

function splitSentences(text: string): string[] {
  return text
    .replace(/[\n\r]+/g, "；")
    .split(/[。；;！!？?]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function rewriteStar(input: string): StarResult {
  const sentences = splitSentences(input);
  const result: StarResult = { situation: [], task: [], action: [], result: [] };
  const sitKeywords = ["因为", "由于", "当时", "背景是", "面临", "场景", "问题是"];
  const taskKeywords = ["目标", "任务", "需要", "要求", "期望", "希望", "负责"];
  const actionKeywords = [
    "做了",
    "采用",
    "实现",
    "参与",
    "使用",
    "通过",
    "完成",
    "搭建",
    "设计",
    "重构",
    "优化",
    "开发",
    "调研",
    "推动",
    "组织",
    "编写",
    "引入",
  ];
  const resultKeywords = [
    "结果",
    "最终",
    "获得",
    "提升",
    "降低",
    "达成",
    "完成",
    "提高了",
    "降低了",
    "缩短了",
    "增加了",
    "节省了",
    "上线",
    "效果",
  ];
  sentences.forEach((s) => {
    const matchedSit = sitKeywords.some((k) => s.includes(k));
    const matchedTask = taskKeywords.some((k) => s.includes(k));
    const matchedResult = resultKeywords.some((k) => s.includes(k));
    const matchedAction = actionKeywords.some((k) => s.includes(k));
    if (matchedResult) result.result.push(s);
    else if (matchedSit) result.situation.push(s);
    else if (matchedTask) result.task.push(s);
    else if (matchedAction) result.action.push(s);
    else result.action.push(s); // 默认归到 Action
  });
  return result;
}

function formatStarText(r: StarResult): string {
  const parts: string[] = [];
  if (r.situation.length) parts.push(`【Situation 情境】\n${r.situation.join("；")}。`);
  else
    parts.push(
      "【Situation 情境】\n（未识别到背景描述，建议补充：在什么场景/时间/团队下？）",
    );
  if (r.task.length) parts.push(`【Task 任务】\n${r.task.join("；")}。`);
  else parts.push("【Task 任务】\n（未识别到任务描述，建议补充：你具体负责什么/目标是什么？）");
  if (r.action.length) parts.push(`【Action 行动】\n${r.action.join("；")}。`);
  else parts.push("【Action 行动】\n（未识别到行动描述，建议补充：你具体做了什么？）");
  if (r.result.length) parts.push(`【Result 结果】\n${r.result.join("；")}。`);
  else
    parts.push(
      "【Result 结果】\n（未识别到结果描述，强烈建议补充：可量化的成果、数据指标）",
    );
  return parts.join("\n\n");
}

// ===== 增强 3: 面试题练习 =====
type QType = "behavior" | "tech" | "project" | "system";
interface Question {
  id: string;
  question: string;
  type: QType;
}
const INTERVIEW_QUESTIONS: Question[] = [
  { id: "q1", question: "请做一下自我介绍（控制在 2 分钟内）", type: "behavior" },
  { id: "q2", question: "为什么选择我们公司 / 这个岗位？", type: "behavior" },
  { id: "q3", question: "说说你做过最有挑战的一个项目，遇到什么难题，如何解决？", type: "project" },
  { id: "q4", question: "如何设计一个短链服务？请给出整体架构与关键取舍。", type: "system" },
  { id: "q5", question: "讲解一下 HTTPS 的握手过程，以及它如何防止中间人攻击。", type: "tech" },
  { id: "q6", question: "讲一次你和同事意见不一致的经历，你是如何处理的？", type: "behavior" },
  { id: "q7", question: "你最大的缺点是什么？你如何改进？", type: "behavior" },
  { id: "q8", question: "在高并发场景下，如何保证缓存与数据库的一致性？", type: "tech" },
  { id: "q9", question: "设计一个秒杀系统，覆盖限流、库存、防超卖。", type: "system" },
  { id: "q10", question: "未来三年的职业规划是什么？", type: "behavior" },
  { id: "q11", question: "讲一次你推动跨团队协作的经历。", type: "behavior" },
  { id: "q12", question: "你是如何排查线上一个偶现的性能问题的？", type: "tech" },
];

const QUESTION_TYPE_LABEL: Record<QType, string> = {
  behavior: "行为面试",
  tech: "技术深度",
  project: "项目深挖",
  system: "系统设计",
};

const QUESTION_TYPE_COLOR: Record<QType, string> = {
  behavior: "bg-violet-100 text-violet-700",
  tech: "bg-blue-100 text-blue-700",
  project: "bg-amber-100 text-amber-700",
  system: "bg-emerald-100 text-emerald-700",
};

const QUESTION_KEYWORDS: Record<QType, string[]> = {
  behavior: ["具体", "例子", "团队", "沟通", "承担", "学习", "成长", "反思", "总结"],
  tech: ["原理", "性能", "并发", "一致性", "容错", "扩展", "权衡", "trade-off", "数据", "指标"],
  project: ["角色", "负责", "挑战", "方案", "架构", "成果", "数据", "复盘", "团队"],
  system: ["架构", "容量", "估算", "限流", "缓存", "一致性", "扩展", "可用", "权衡", "降级"],
};

interface EvalResult {
  score: number;
  pros: string[];
  improvements: string[];
  reference: string;
}

function evaluateAnswer(q: Question, answer: string): EvalResult {
  const text = answer.trim();
  let score = 30; // 基础分
  const pros: string[] = [];
  const improvements: string[] = [];

  // 长度评分 (最多 30 分)
  const len = text.length;
  let lenScore = 0;
  if (len > 300) lenScore = 30;
  else if (len > 150) lenScore = 22;
  else if (len > 80) lenScore = 14;
  else if (len > 30) lenScore = 8;
  else lenScore = 3;
  score += lenScore;
  if (len > 150) pros.push("回答详实，内容有展开");
  else improvements.push("回答偏短，建议展开到 200-400 字，结构化表达");

  // 关键词匹配 (最多 20 分)
  const keywords = QUESTION_KEYWORDS[q.type];
  const matched = keywords.filter((k) => text.toLowerCase().includes(k.toLowerCase()));
  const kwScore = Math.round((matched.length / keywords.length) * 20);
  score += kwScore;
  if (matched.length >= Math.ceil(keywords.length / 2)) {
    pros.push(
      `覆盖了 ${matched.length}/${keywords.length} 个关键点（${matched.slice(0, 3).join("、")}）`,
    );
  } else {
    const missing = keywords.filter(
      (k) => !text.toLowerCase().includes(k.toLowerCase()),
    );
    improvements.push(
      `关键点覆盖不足（${matched.length}/${keywords.length}），可补充：${missing.slice(0, 3).join("、")}`,
    );
  }

  // STAR 结构检测 (最多 20 分)
  let structScore = 0;
  const hasSit = /因为|由于|当时|背景|面临|场景/.test(text);
  const hasTask = /目标|任务|需要|负责|要求|希望/.test(text);
  const hasAction = /做了|采用|实现|参与|使用|通过|完成|搭建|设计|重构|优化|开发|推动|组织|编写|引入/.test(
    text,
  );
  const hasResult = /结果|最终|获得|提升|降低|达成|完成|提高了|降低了|缩短了|增加了|节省了|上线|效果/.test(
    text,
  );
  if (hasSit) structScore += 5;
  if (hasTask) structScore += 5;
  if (hasAction) structScore += 5;
  if (hasResult) structScore += 5;
  score += structScore;
  if (hasResult) pros.push("回答中包含结果/数据，有 STAR 结构意识");
  if (!hasResult) improvements.push("缺少可量化的结果，建议补充数据指标（如提升 X%、降低 Y ms）");
  if (!hasSit) improvements.push("建议补充情境（Situation）说明背景");
  if (!hasAction) improvements.push("建议明确写出你个人的具体行动（Action）");

  score = Math.min(100, Math.max(0, Math.round(score)));

  const referenceMap: Record<string, string> = {
    q1: "结构化介绍：1）基本信息 30s；2）核心技术栈与代表项目 60s；3）为什么应聘这个岗位 30s。避免流水账，突出与岗位匹配的点。",
    q2: "三层回答：1）公司层面（业务/文化/技术栈）你认可的具体点；2）岗位层面与你能力的匹配点；3）你能给团队带来的独特价值。",
    q3: "按 STAR 展开：S 说清项目背景与挑战；T 你的具体职责；A 关键技术决策与权衡；R 可量化成果（QPS、延迟、覆盖用户数）+ 复盘。",
    q4: "要点：发号器（雪花/自增）/ 存储（KV）/ 缓存 / 302 跳转 / 防缓存穿透 / 可用性估算 / 监控。重点讨论 trade-off。",
    q5: "TLS 1.2 握手：ClientHello → ServerHello + Certificate → KeyExchange → Finished。重点：证书链验证、密钥协商、前向保密、防中间人。",
    q6: "聚焦事实 → 倾听对方 → 寻找共同目标 → 数据/实验验证 → 达成共识。避免贬低对方，强调你推动了什么。",
    q7: "选一个真实但不致命的缺点 + 你正在采取的具体改进行动 + 已有的进展。避免假缺点（追求完美）。",
    q8: "讨论：延迟双删、Canal 订阅 binlog、最终一致性方案、强一致性场景用 2PC/TCC。结合业务权衡强一致 vs 最终一致。",
    q9: "分层：CDN/前端限流 → 网关限流（令牌桶）→ 应用层（库存预扣、Redis 原子扣减 Lua）→ DB 兜底。防超卖：Redis Lua + 唯一订单。",
    q10: "技术线（IC → Senior → Staff）/ 管理线，结合岗位现实。给出 1 年/3 年具体目标，与公司业务方向挂钩。",
    q11: "讲清楚背景为什么需要跨团队 → 你建立的沟通机制 → 产出。强调主动性和影响力。",
    q12: "排查链路：监控 → 日志 → 火焰图 → 复现 → 根因。给出一个具体案例的根因和优化方案。",
  };
  return {
    score,
    pros: pros.slice(0, 3),
    improvements: improvements.slice(0, 3),
    reference: referenceMap[q.id] ?? "建议按 STAR 结构组织答案，重点突出你的个人贡献和可量化的结果。",
  };
}

// ===== localStorage 计数工具 =====
const PRACTICE_KEY = "interview:practice_count";
const STAR_KEY = "interview:star_count";

function loadCount(key: string): number {
  if (typeof window === "undefined") return 0;
  try {
    const v = window.localStorage.getItem(key);
    return v ? Number(v) || 0 : 0;
  } catch {
    return 0;
  }
}
function saveCount(key: string, v: number) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, String(v));
  } catch {
    // 静默失败
  }
}

export default function InterviewPage() {
  const router = useRouter();
  const toast = useToast();

  const [stats, setStats] = useState<InterviewStats | null>(null);
  const [companies, setCompanies] = useState<CompanyInfo[]>([]);
  const [myReports, setMyReports] = useState<InterviewReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const PAGE_SIZE = 20;

  // 分页加载"我的面试报告"
  const loadMyReports = useCallback(
    async (targetPage: number) => {
      try {
        let target = targetPage;
        let data = await interviewApi.myReports({
          page: target,
          page_size: PAGE_SIZE,
        });
        // 若目标页为空且非首页，回退到首页
        if (data.items.length === 0 && target > 1) {
          target = 1;
          data = await interviewApi.myReports({
            page: 1,
            page_size: PAGE_SIZE,
          });
        }
        setMyReports(data.items);
        setTotal(data.total);
        setPage(target);
      } catch (err) {
        toast.push(
          err instanceof Error ? err.message : "加载失败",
          "error",
        );
      }
    },
    [toast],
  );

  // 表单状态
  const [company, setCompany] = useState("");
  const [position, setPosition] = useState("");
  const [city, setCity] = useState("");
  const [interviewYear, setInterviewYear] = useState<number>(2024);
  const [rounds, setRounds] = useState<number>(3);
  const [result, setResult] = useState("pending");
  const [dimensions, setDimensions] = useState<string[]>([]);
  const [difficulty, setDifficulty] = useState<number>(3);
  const [summary, setSummary] = useState("");

  // ===== 增强 2/3/4 的状态 =====
  const [starInput, setStarInput] = useState("");
  const [starOutput, setStarOutput] = useState<string | null>(null);
  const [starLoading, setStarLoading] = useState(false);
  const [practiceCount, setPracticeCount] = useState(0);
  const [starCount, setStarCount] = useState(0);
  const [selectedQId, setSelectedQId] = useState<string>(INTERVIEW_QUESTIONS[0].id);
  const [answer, setAnswer] = useState("");
  const [evalResult, setEvalResult] = useState<EvalResult | null>(null);
  const [evalLoading, setEvalLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [st, comps, mine] = await Promise.all([
          interviewApi.stats(),
          interviewApi.companies(),
          interviewApi.myReports({ page: 1, page_size: PAGE_SIZE }),
        ]);
        setStats(st);
        setCompanies(comps);
        setMyReports(mine.items);
        setTotal(mine.total);
      } catch (err) {
        toast.push(
          err instanceof Error ? err.message : "加载数据失败",
          "error",
        );
      } finally {
        setLoading(false);
      }
    })();
    // 初始化练习/改写计数(从 localStorage 读取, 跨会话保留)
    setPracticeCount(loadCount(PRACTICE_KEY));
    setStarCount(loadCount(STAR_KEY));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toast]);

  const toggleDimension = (dim: string) => {
    setDimensions((prev) =>
      prev.includes(dim) ? prev.filter((d) => d !== dim) : [...prev, dim],
    );
  };

  const refreshStats = async () => {
    try {
      const st = await interviewApi.stats();
      setStats(st);
    } catch {
      // 静默失败
    }
  };

  const handleSubmit = async () => {
    const co = company.trim();
    const pos = position.trim();
    if (!co || !pos) {
      toast.push("请填写公司和岗位", "error");
      return;
    }

    const body: InterviewSubmit = {
      company: co,
      position: pos,
      interview_year: interviewYear,
    };
    if (city.trim()) body.city = city.trim();
    if (rounds) body.rounds = rounds;
    if (result) body.result = result;
    if (dimensions.length > 0) body.dimensions = dimensions;
    if (difficulty) body.difficulty = difficulty;
    if (summary.trim()) body.summary = summary.trim();

    setSubmitting(true);
    try {
      await interviewApi.submit(body);
      toast.push("提交成功，感谢你的分享！", "success");
      setCompany("");
      setPosition("");
      setCity("");
      setSummary("");
      setDimensions([]);
      loadMyReports(page);
      refreshStats();
    } catch (err) {
      toast.push(
        err instanceof Error ? err.message : "提交失败",
        "error",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await interviewApi.remove(id);
      toast.push("已删除该记录", "success");
      loadMyReports(page);
      refreshStats();
    } catch (err) {
      toast.push(
        err instanceof Error ? err.message : "删除失败",
        "error",
      );
    }
  };

  const handleViewAggregate = () => {
    const co = company.trim();
    if (!co) {
      toast.push("请先填写公司名称", "info");
      return;
    }
    const c = encodeParam(co);
    router.push(`/interview/result?c=${c}`);
  };

  // ===== 派生:能力雷达 / 准备度 =====
  const abilityScores = useMemo(() => computeAbilityScores(myReports), [myReports]);
  const abilityAvg = useMemo(() => {
    if (!abilityScores) return 0;
    const vals = Object.values(abilityScores);
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  }, [abilityScores]);

  const readiness = useMemo(() => {
    const reportScore = Math.min(30, myReports.length * 6); // 最多 30 分
    const practiceScore = Math.min(30, practiceCount * 6); // 最多 30 分
    const starScore = Math.min(20, starCount * 4); // 最多 20 分
    const radarScore = Math.min(20, (abilityAvg / 10) * 20); // 最多 20 分
    return Math.round(reportScore + practiceScore + starScore + radarScore);
  }, [myReports.length, practiceCount, starCount, abilityAvg]);

  const readinessLabel =
    readiness < 30
      ? "刚开始准备"
      : readiness < 60
        ? "基础就绪"
        : readiness < 80
          ? "准备充分"
          : "胸有成竹";
  const readinessColor =
    readiness >= 80
      ? "text-emerald-600"
      : readiness >= 60
        ? "text-brand-600"
        : readiness >= 30
          ? "text-amber-600"
          : "text-red-600";

  // ===== STAR 改写处理 =====
  const handleStarRewrite = useCallback(() => {
    const text = starInput.trim();
    if (!text) {
      toast.push("请先输入一段经历描述", "info");
      return;
    }
    setStarLoading(true);
    // 规则引擎同步计算, 加一点延迟模拟"AI 思考"以提升体感
    setTimeout(() => {
      const r = rewriteStar(text);
      setStarOutput(formatStarText(r));
      const next = starCount + 1;
      setStarCount(next);
      saveCount(STAR_KEY, next);
      setStarLoading(false);
    }, 350);
  }, [starInput, starCount, toast]);

  // ===== 面试题评估处理 =====
  const handleEvaluate = useCallback(() => {
    const a = answer.trim();
    if (!a) {
      toast.push("请输入你的回答", "info");
      return;
    }
    setEvalLoading(true);
    setTimeout(() => {
      const q =
        INTERVIEW_QUESTIONS.find((x) => x.id === selectedQId) ??
        INTERVIEW_QUESTIONS[0];
      const r = evaluateAnswer(q, a);
      setEvalResult(r);
      const next = practiceCount + 1;
      setPracticeCount(next);
      saveCount(PRACTICE_KEY, next);
      setEvalLoading(false);
    }, 350);
  }, [answer, selectedQId, practiceCount, toast]);

  const selectedQuestion =
    INTERVIEW_QUESTIONS.find((q) => q.id === selectedQId) ?? INTERVIEW_QUESTIONS[0];

  if (loading) return <ListSkeleton />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">面试经验</h1>
        <p className="text-sm text-ink-500 mt-1">
          匿名分享你的面试经历，聚合后展示"这家公司面试官实际看重什么"
        </p>
      </div>

      {/* 统计 */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="card text-center">
            <p className="text-2xl font-bold text-brand-600">
              {stats.total_reports}
            </p>
            <p className="text-xs text-ink-500">面试样本</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-green-600">
              {stats.company_count}
            </p>
            <p className="text-xs text-ink-500">覆盖公司</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-amber-600">
              {stats.position_count}
            </p>
            <p className="text-xs text-ink-500">覆盖岗位</p>
          </div>
        </div>
      )}

      {/* 增强 4: 面试准备度仪表盘 */}
      <div className="card">
        <h2 className="font-semibold text-ink-800 mb-4 flex items-center gap-2">
          <Gauge className="h-4 w-4 text-brand-500" />
          面试准备度
          <span className="text-xs font-normal text-ink-400">
            （基于面试记录 / 题目练习 / STAR 改写 / 能力均分综合计算）
          </span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
          <div className="flex justify-center">
            <ReadinessGauge score={readiness} />
          </div>
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-baseline gap-3">
              <span className="text-3xl font-bold text-ink-800">{readiness}</span>
              <span className="text-sm text-ink-400">/ 100</span>
              <span className={cn("text-base font-semibold ml-2", readinessColor)}>
                {readinessLabel}
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="rounded-lg border border-ink-100 bg-ink-50 px-3 py-2 text-center">
                <p className="text-lg font-semibold text-ink-800">{myReports.length}</p>
                <p className="text-xs text-ink-500">面试记录</p>
              </div>
              <div className="rounded-lg border border-ink-100 bg-ink-50 px-3 py-2 text-center">
                <p className="text-lg font-semibold text-ink-800">{practiceCount}</p>
                <p className="text-xs text-ink-500">题目练习</p>
              </div>
              <div className="rounded-lg border border-ink-100 bg-ink-50 px-3 py-2 text-center">
                <p className="text-lg font-semibold text-ink-800">{starCount}</p>
                <p className="text-xs text-ink-500">STAR 改写</p>
              </div>
              <div className="rounded-lg border border-ink-100 bg-ink-50 px-3 py-2 text-center">
                <p className="text-lg font-semibold text-ink-800">
                  {abilityAvg > 0 ? abilityAvg.toFixed(1) : "—"}
                </p>
                <p className="text-xs text-ink-500">能力均分</p>
              </div>
            </div>
            <p className="text-xs text-ink-400 leading-relaxed">
              评分构成：面试记录（≤30）+ 题目练习（≤30）+ STAR 改写（≤20）+ 能力雷达均分（≤20）。
              多练习多复盘，分数会持续上升。
            </p>
          </div>
        </div>
      </div>

      {/* 增强 1 + 增强 2: 能力画像雷达图 + STAR 改写助手 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 增强 1: 面试能力画像 */}
        <div className="card">
          <h2 className="font-semibold text-ink-800 mb-4 flex items-center gap-2">
            <RadarIcon className="h-4 w-4 text-brand-500" />
            我的面试能力画像
          </h2>
          {abilityScores ? (
            <>
              <AbilityRadar scores={abilityScores} />
              <div className="mt-3 grid grid-cols-4 gap-2 text-xs">
                {ABILITY_DIMENSIONS.map((d) => (
                  <div
                    key={d}
                    className="flex items-center justify-between rounded border border-ink-100 bg-ink-50 px-2 py-1"
                  >
                    <span className="text-ink-500">{d}</span>
                    <span className="font-semibold text-ink-700">
                      {abilityScores[d].toFixed(1)}
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <EmptyState
              title="还没有能力画像"
              description="完成面试后会生成你的能力画像，从 8 个维度可视化展示你的面试强弱项"
            />
          )}
        </div>

        {/* 增强 2: STAR 改写助手 */}
        <div className="card">
          <h2 className="font-semibold text-ink-800 mb-4 flex items-center gap-2">
            <PenLine className="h-4 w-4 text-brand-500" />
            STAR 改写助手
          </h2>
          <Textarea
            value={starInput}
            onChange={(e) => setStarInput(e.target.value)}
            placeholder="把一段经历粘贴在这里，例如：&quot;我负责订单服务，因为接口慢被吐槽，做了缓存改造，最终 RT 从 800ms 降到 120ms&quot;"
            rows={4}
            maxLength={600}
          />
          <div className="mt-2 flex items-center justify-between">
            <span className="text-xs text-ink-400">
              {starInput.length}/600 · 已改写 {starCount} 次
            </span>
            <Button onClick={handleStarRewrite} loading={starLoading} size="sm">
              <Sparkles className="h-4 w-4" /> AI 优化
            </Button>
          </div>

          {starOutput && (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="rounded-lg border border-ink-200 bg-ink-50 p-3">
                <p className="mb-2 text-xs font-semibold text-ink-500">
                  原文
                </p>
                <p className="whitespace-pre-wrap text-sm text-ink-700 leading-relaxed">
                  {starInput}
                </p>
              </div>
              <div className="rounded-lg border border-brand-200 bg-brand-50 p-3">
                <p className="mb-2 text-xs font-semibold text-brand-700">
                  STAR 结构改写
                </p>
                <pre className="whitespace-pre-wrap font-sans text-sm text-ink-800 leading-relaxed">
                  {starOutput}
                </pre>
              </div>
            </div>
          )}
          <p className="mt-3 text-xs text-ink-400">
            面试时用 STAR 结构讲述经历，通过率提升 40%
          </p>
        </div>
      </div>

      {/* 增强 3: 面试题练习 + 一题一评 */}
      <div className="card">
        <h2 className="font-semibold text-ink-800 mb-4 flex items-center gap-2">
          <ListChecks className="h-4 w-4 text-brand-500" />
          面试题练习
          <span className="text-xs font-normal text-ink-400">
            （{INTERVIEW_QUESTIONS.length} 道高频题 · 已练习 {practiceCount} 次）
          </span>
        </h2>

        <div className="space-y-4">
          {/* 题目选择 */}
          <div>
            <label className="block text-xs font-medium text-ink-500 mb-1">
              选择题目
            </label>
            <Select
              value={selectedQId}
              onChange={(e) => {
                setSelectedQId(e.target.value);
                setEvalResult(null);
                setAnswer("");
              }}
            >
              {INTERVIEW_QUESTIONS.map((q) => (
                <option key={q.id} value={q.id}>
                  [{QUESTION_TYPE_LABEL[q.type]}] {q.question}
                </option>
              ))}
            </Select>
            <div className="mt-2 flex items-center gap-2">
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-xs font-medium",
                  QUESTION_TYPE_COLOR[selectedQuestion.type],
                )}
              >
                {QUESTION_TYPE_LABEL[selectedQuestion.type]}
              </span>
              <span className="text-sm text-ink-700">
                {selectedQuestion.question}
              </span>
            </div>
          </div>

          {/* 回答输入 */}
          <div>
            <label className="block text-xs font-medium text-ink-500 mb-1">
              你的回答
            </label>
            <Textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="建议按 STAR 结构组织：情境 → 任务 → 行动 → 结果（结果尽量给出可量化数据）"
              rows={6}
              maxLength={1500}
            />
            <div className="mt-1 flex items-center justify-between">
              <span className="text-xs text-ink-400">{answer.length}/1500</span>
              <Button onClick={handleEvaluate} loading={evalLoading} size="sm">
                <Send className="h-4 w-4" /> 提交评估
              </Button>
            </div>
          </div>

          {/* 评估结果 */}
          {evalResult && (
            <div className="rounded-lg border border-ink-200 bg-ink-50 p-4 space-y-3 animate-fade-in">
              <div className="flex items-baseline gap-3">
                <span className="text-xs font-medium text-ink-500">评分</span>
                <span
                  className={cn(
                    "text-2xl font-bold",
                    evalResult.score >= 80
                      ? "text-emerald-600"
                      : evalResult.score >= 60
                        ? "text-brand-600"
                        : evalResult.score >= 30
                          ? "text-amber-600"
                          : "text-red-600",
                  )}
                >
                  {evalResult.score}
                </span>
                <span className="text-sm text-ink-400">/ 100</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <p className="mb-1.5 flex items-center gap-1 text-xs font-semibold text-emerald-700">
                    <CheckCircle2 className="h-3.5 w-3.5" /> 优点
                  </p>
                  {evalResult.pros.length > 0 ? (
                    <ul className="space-y-1">
                      {evalResult.pros.map((p, i) => (
                        <li
                          key={i}
                          className="text-xs text-ink-600 leading-relaxed pl-4 relative before:content-['•'] before:absolute before:left-0 before:text-emerald-500"
                        >
                          {p}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-ink-400">暂无明显亮点，继续加油</p>
                  )}
                </div>
                <div>
                  <p className="mb-1.5 flex items-center gap-1 text-xs font-semibold text-amber-700">
                    <AlertCircle className="h-3.5 w-3.5" /> 改进建议
                  </p>
                  {evalResult.improvements.length > 0 ? (
                    <ul className="space-y-1">
                      {evalResult.improvements.map((p, i) => (
                        <li
                          key={i}
                          className="text-xs text-ink-600 leading-relaxed pl-4 relative before:content-['•'] before:absolute before:left-0 before:text-amber-500"
                        >
                          {p}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-ink-400">已经很完整，几乎没有需要改进的地方</p>
                  )}
                </div>
              </div>

              <div>
                <p className="mb-1.5 flex items-center gap-1 text-xs font-semibold text-blue-700">
                  <Lightbulb className="h-3.5 w-3.5" /> 参考答案
                </p>
                <p className="text-xs text-ink-600 leading-relaxed bg-white rounded border border-ink-100 p-2.5">
                  {evalResult.reference}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 公司面经库 - 浏览入口 */}
      {companies.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-ink-800 mb-4 flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-brand-500" />
            公司面经库
            <span className="text-xs font-normal text-ink-400">（点击公司查看聚合数据）</span>
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {companies.map((c) => (
              <Link
                key={c.name}
                href={`/interview/result?c=${encodeURIComponent(btoa(unescape(encodeURIComponent(c.name))))}`}
                className="flex items-center justify-between rounded-lg border border-ink-200 bg-ink-50 px-3 py-2.5 hover:border-brand-300 hover:bg-brand-50 transition-colors group"
              >
                <span className="text-sm font-medium text-ink-700 group-hover:text-brand-700 truncate">{c.name}</span>
                <span className="ml-2 flex-shrink-0 rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700">{c.count}</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* 提交表单 */}
      <div className="card">
        <h2 className="font-semibold text-ink-800 mb-4 flex items-center gap-2">
          <Briefcase className="h-4 w-4 text-brand-500" />
          匿名提交面试经验
        </h2>

        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-ink-500 mb-1">
                公司 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="如：腾讯"
                className="w-full rounded-lg border border-ink-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                list="interview-company-list"
              />
              <datalist id="interview-company-list">
                {companies.map((c) => (
                  <option key={c.name} value={c.name} />
                ))}
              </datalist>
            </div>

            <div>
              <label className="block text-xs font-medium text-ink-500 mb-1">
                岗位 <span className="text-red-500">*</span>
              </label>
              <Input
                value={position}
                onChange={(e) => setPosition(e.target.value)}
                placeholder="如：后端开发"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-ink-500 mb-1">
                城市
              </label>
              <Input
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="如：深圳"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-ink-500 mb-1">
                面试年份 <span className="text-red-500">*</span>
              </label>
              <Select
                value={interviewYear}
                onChange={(e) => setInterviewYear(Number(e.target.value))}
              >
                {YEARS.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <label className="block text-xs font-medium text-ink-500 mb-1">
                面试轮数
              </label>
              <Select
                value={rounds}
                onChange={(e) => setRounds(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((r) => (
                  <option key={r} value={r}>
                    {r} 轮
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {/* 面试结果 */}
          <div>
            <label className="block text-xs font-medium text-ink-500 mb-2">
              面试结果 <span className="text-red-500">*</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {INTERVIEW_RESULTS.map((r) => {
                const active = result === r;
                return (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setResult(r)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-sm transition-colors",
                      active
                        ? "border-brand-500 bg-brand-50 text-brand-700"
                        : "border-ink-200 bg-white text-ink-600 hover:border-brand-300 hover:text-brand-600",
                    )}
                  >
                    {INTERVIEW_RESULT_LABEL[r] ?? r}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 考察维度多选 */}
          <div>
            <label className="block text-xs font-medium text-ink-500 mb-2">
              考察维度 <span className="text-red-500">*</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {INTERVIEW_DIMENSIONS.map((dim) => {
                const active = dimensions.includes(dim);
                return (
                  <button
                    key={dim}
                    type="button"
                    onClick={() => toggleDimension(dim)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-sm transition-colors",
                      active
                        ? "border-brand-500 bg-brand-50 text-brand-700"
                        : "border-ink-200 bg-white text-ink-600 hover:border-brand-300 hover:text-brand-600",
                    )}
                  >
                    {INTERVIEW_DIMENSION_LABEL[dim] ?? dim}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 难度评分 */}
          <div>
            <label className="block text-xs font-medium text-ink-500 mb-2">
              难度评分
            </label>
            <div className="flex items-center gap-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setDifficulty(star)}
                  className="p-1"
                  aria-label={`${star} 星`}
                >
                  <Star
                    className={cn(
                      "h-6 w-6 transition-colors",
                      star <= difficulty
                        ? "fill-amber-400 text-amber-400"
                        : "text-ink-300 hover:text-amber-300",
                    )}
                  />
                </button>
              ))}
              <span className="text-sm text-ink-500 ml-2">
                {difficulty}/5
              </span>
            </div>
          </div>

          {/* 一句话总结 */}
          <div>
            <label className="block text-xs font-medium text-ink-500 mb-1">
              一句话总结
            </label>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="如：侧重算法和系统设计，三轮技术面"
              maxLength={200}
              rows={2}
              className="w-full rounded-lg border border-ink-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Button onClick={handleSubmit} loading={submitting}>
              <Send className="h-4 w-4" /> 提交报告
            </Button>
            <Button variant="secondary" onClick={handleViewAggregate}>
              <BarChart3 className="h-4 w-4" /> 查看聚合结果
            </Button>
            <span className="text-xs text-ink-400">
              数据完全匿名，仅用于聚合统计
            </span>
          </div>
        </div>
      </div>

      {/* 我的提交记录 */}
      <div className="card">
        <h2 className="font-semibold text-ink-800 mb-4">我的提交记录</h2>
        {myReports.length === 0 ? (
          <EmptyState
            title="暂无提交记录"
            description="提交你的第一份面试报告，它会出现在这里"
          />
        ) : (
          <div className="space-y-3">
            {myReports.map((r) => (
              <div
                key={r.id}
                className="rounded-lg border border-ink-100 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-ink-800">
                        {r.company} · {r.position}
                      </span>
                      <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
                        {INTERVIEW_RESULT_LABEL[r.result] ?? r.result}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-ink-400">
                      {r.interview_year}年{r.city ? ` · ${r.city}` : ""}
                      {r.rounds ? ` · ${r.rounds}轮` : ""}
                      {r.difficulty ? ` · 难度${r.difficulty}/5` : ""}
                    </p>
                    {r.dimensions.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {r.dimensions.map((d) => (
                          <span
                            key={d}
                            className="rounded bg-ink-100 px-1.5 py-0.5 text-xs text-ink-500"
                          >
                            {INTERVIEW_DIMENSION_LABEL[d] ?? d}
                          </span>
                        ))}
                      </div>
                    )}
                    {r.summary && (
                      <p className="mt-1 text-sm text-ink-600">{r.summary}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Link
                      href={`/interview/result?c=${encodeParam(r.company)}`}
                      className="text-xs text-brand-600 hover:underline"
                    >
                      查看聚合
                    </Link>
                    <button
                      onClick={() => handleDelete(r.id)}
                      className="flex h-8 w-8 items-center justify-center rounded-md text-ink-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                      aria-label="删除记录"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          onPageChange={(p) => loadMyReports(p)}
        />
      </div>
    </div>
  );
}
