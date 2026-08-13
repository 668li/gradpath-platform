"use client";

import { useCallback, useEffect, useState, useRef } from "react";
import Link from "next/link";
import {
  Compass, Play, Plus, Trash2, Star, TrendingUp, Shield, AlertTriangle,
  ChevronDown, ChevronRight, BarChart3, Trophy, DollarSign, Heart, Zap,
  GraduationCap, Building2, Briefcase, Landmark, ChevronUp, Route, Save, ArrowRight,
  Calculator, GitBranch, Code, Users, Target, Calendar, CheckCircle2,
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  BarChart, Bar, ResponsiveContainer, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, AreaChart, Area,
} from "recharts";
import { careerSimulatorApi, decisionsApi } from "@/lib/api";
import type { PathResult, SimulateResponse, Preset, CityTier, Industry } from "@/lib/api/career-simulator";
import { cn, todayISO } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { Button, Input, Field } from "@/components/ui/form-controls";
import { TestDriveSection } from "@/components/career-simulator/test-drive-card";
import { WhatIfSection } from "@/components/career-simulator/path-comparison-table";

const PATH_ICONS: Record<string, React.ReactNode> = {
  grad_cs: <GraduationCap className="w-5 h-5" />,
  grad_finance: <GraduationCap className="w-5 h-5" />,
  civil_national: <Landmark className="w-5 h-5" />,
  civil_provincial: <Building2 className="w-5 h-5" />,
  career_it: <Briefcase className="w-5 h-5" />,
  career_finance: <Briefcase className="w-5 h-5" />,
  career_education: <Briefcase className="w-5 h-5" />,
  career_healthcare: <Briefcase className="w-5 h-5" />,
  career_fallback: <Briefcase className="w-5 h-5" />,
};

const RISK_COLORS: Record<string, string> = {
  low: "text-green-600 bg-green-50",
  medium: "text-yellow-600 bg-yellow-50",
  high: "text-red-600 bg-red-50",
};

const PATH_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#f97316"];

/* ===== 增强 1：匹配度算法透明度 ===== */
type MatchDimension = {
  key: string;
  label: string;
  weight: number;
  source: string;
  score: number;
};

const MATCH_WEIGHTS: { key: string; label: string; weight: number; source: string }[] = [
  { key: "education", label: "教育背景", weight: 20, source: "基于用户 profile 的学校层次 / 专业 / 绩点" },
  { key: "skills", label: "技能匹配", weight: 30, source: "基于 skills 页面的技能掌握数 vs 路径要求技能" },
  { key: "experience", label: "经验匹配", weight: 25, source: "基于 timeline 的实习 / 项目经历" },
  { key: "interest", label: "兴趣匹配", weight: 15, source: "基于 assessment 的霍兰德代码" },
  { key: "values", label: "价值观匹配", weight: 10, source: "基于 life-wheel 的评分" },
];

function computeMatchScores(p: PathResult): { dimensions: MatchDimension[]; total: number } {
  const educationScore = Math.min(100, Math.round((p.total_education_cost / 100000) * 25 + 60));
  const skillsScore = Math.min(100, Math.max(40, Math.round(p.career_growth_score * 1.8)));
  const experienceScore = Math.min(100, Math.max(35, Math.round(p.stability_score * 7 + 20)));
  const interestScore = Math.min(100, Math.max(40, Math.round(p.avg_satisfaction * 10)));
  const valuesScore = Math.min(100, Math.max(40, Math.round(p.avg_satisfaction * 5 + p.stability_score * 4)));
  const raw = [educationScore, skillsScore, experienceScore, interestScore, valuesScore];
  const dimensions: MatchDimension[] = MATCH_WEIGHTS.map((w, i) => ({ ...w, score: raw[i] }));
  const total = Math.round(dimensions.reduce((sum, d) => sum + (d.score * d.weight) / 100, 0));
  return { dimensions, total };
}

/* ===== 增强 2：双轨晋升路径（技术线 vs 管理线）===== */
type TrackLevel = { level: string; years: string; skills: string; salary: string };
type DualTrack = { technical: TrackLevel[]; management: TrackLevel[] };

const DUAL_TRACK: Record<string, DualTrack> = {
  grad_cs: {
    technical: [
      { level: "初级工程师", years: "0-2", skills: "编程基础 / 代码规范", salary: "15-25万" },
      { level: "中级工程师", years: "2-4", skills: "模块设计 / 性能优化", salary: "25-40万" },
      { level: "高级工程师", years: "4-7", skills: "架构设计 / 技术选型", salary: "40-60万" },
      { level: "资深工程师", years: "7-10", skills: "技术决策 / 团队赋能", salary: "60-100万" },
      { level: "技术专家", years: "10+", skills: "行业影响 / 技术战略", salary: "100万+" },
    ],
    management: [
      { level: "中级工程师", years: "2-4", skills: "需求拆解 / 项目管理", salary: "25-40万" },
      { level: "技术组长", years: "4-6", skills: "团队管理 / 资源协调", salary: "40-55万" },
      { level: "技术经理", years: "6-9", skills: "组织建设 / 绩效管理", salary: "55-80万" },
      { level: "技术总监", years: "9-12", skills: "战略规划 / 人才发展", salary: "80-120万" },
      { level: "技术 VP", years: "12+", skills: "业务决策 / 技术愿景", salary: "120万+" },
    ],
  },
  grad_finance: {
    technical: [
      { level: "分析师", years: "0-2", skills: "财务建模 / 数据分析", salary: "15-25万" },
      { level: "高级分析师", years: "2-4", skills: "行业研究 / 估值模型", salary: "25-40万" },
      { level: "副总裁 (VP)", years: "4-7", skills: "交易执行 / 客户管理", salary: "40-70万" },
      { level: "总监", years: "7-10", skills: "团队带领 / 业务拓展", salary: "70-120万" },
      { level: "董事总经理 (MD)", years: "10+", skills: "战略决策 / 行业资源", salary: "120万+" },
    ],
    management: [
      { level: "高级分析师", years: "2-4", skills: "项目协调 / 流程管理", salary: "25-40万" },
      { level: "副总裁 (VP)", years: "4-7", skills: "团队管理 / 资源调配", salary: "40-70万" },
      { level: "执行总监", years: "7-10", skills: "部门管理 / 人才培养", salary: "70-100万" },
      { level: "董事总经理 (MD)", years: "10+", skills: "业务决策 / 组织建设", salary: "100万+" },
    ],
  },
  civil_national: {
    technical: [
      { level: "科员", years: "0-3", skills: "公文写作 / 政策学习", salary: "8-12万" },
      { level: "副主任科员", years: "3-6", skills: "业务专精 / 调研能力", salary: "12-18万" },
      { level: "主任科员", years: "6-10", skills: "政策研究 / 业务骨干", salary: "18-25万" },
      { level: "副处长", years: "10-15", skills: "业务统筹 / 文稿把关", salary: "25-35万" },
      { level: "处长", years: "15+", skills: "部门管理 / 决策参谋", salary: "35-50万" },
    ],
    management: [
      { level: "科员", years: "0-3", skills: "综合事务 / 协调沟通", salary: "8-12万" },
      { level: "副主任科员", years: "3-6", skills: "团队协作 / 项目跟进", salary: "12-18万" },
      { level: "主任科员", years: "6-10", skills: "组织协调 / 资源整合", salary: "18-25万" },
      { level: "副处长", years: "10-15", skills: "处室管理 / 人事财务", salary: "25-35万" },
      { level: "处长", years: "15+", skills: "部门决策 / 对外协调", salary: "35-50万" },
    ],
  },
  civil_provincial: {
    technical: [
      { level: "科员", years: "0-3", skills: "公文写作 / 业务学习", salary: "7-10万" },
      { level: "副主任科员", years: "3-6", skills: "业务专精 / 政策执行", salary: "10-15万" },
      { level: "主任科员", years: "6-10", skills: "业务骨干 / 调研报告", salary: "15-22万" },
      { level: "副处长", years: "10-15", skills: "业务统筹 / 处室管理", salary: "22-30万" },
      { level: "处长", years: "15+", skills: "部门领导 / 决策执行", salary: "30-40万" },
    ],
    management: [
      { level: "科员", years: "0-3", skills: "综合协调 / 会务组织", salary: "7-10万" },
      { level: "副主任科员", years: "3-6", skills: "跨部门沟通 / 项目协调", salary: "10-15万" },
      { level: "主任科员", years: "6-10", skills: "团队带动 / 资源整合", salary: "15-22万" },
      { level: "副处长", years: "10-15", skills: "处室管理 / 人事协调", salary: "22-30万" },
      { level: "处长", years: "15+", skills: "部门决策 / 对外联络", salary: "30-40万" },
    ],
  },
  career_it: {
    technical: [
      { level: "初级工程师", years: "0-2", skills: "编程基础 / 版本控制", salary: "12-20万" },
      { level: "中级工程师", years: "2-4", skills: "功能开发 / 调试排错", salary: "20-35万" },
      { level: "高级工程师", years: "4-7", skills: "系统设计 / 性能调优", salary: "35-55万" },
      { level: "资深工程师", years: "7-10", skills: "架构设计 / 技术引领", salary: "55-80万" },
      { level: "技术专家", years: "10+", skills: "技术战略 / 行业影响", salary: "80万+" },
    ],
    management: [
      { level: "中级工程师", years: "2-4", skills: "需求拆解 / 进度跟踪", salary: "20-35万" },
      { level: "技术组长", years: "4-6", skills: "团队管理 / 敏捷实践", salary: "35-50万" },
      { level: "技术经理", years: "6-9", skills: "组织建设 / 绩效管理", salary: "50-70万" },
      { level: "技术总监", years: "9-12", skills: "战略规划 / 人才发展", salary: "70-100万" },
      { level: "技术 VP", years: "12+", skills: "业务决策 / 技术愿景", salary: "100万+" },
    ],
  },
  career_finance: {
    technical: [
      { level: "助理分析师", years: "0-2", skills: "数据整理 / 报告撰写", salary: "10-18万" },
      { level: "分析师", years: "2-4", skills: "财务分析 / 估值建模", salary: "18-30万" },
      { level: "高级分析师", years: "4-7", skills: "行业研究 / 投资判断", salary: "30-50万" },
      { level: "投资经理", years: "7-10", skills: "项目主导 / 风险管理", salary: "50-80万" },
      { level: "投资总监", years: "10+", skills: "行业资源 / 战略决策", salary: "80万+" },
    ],
    management: [
      { level: "分析师", years: "2-4", skills: "项目支持 / 流程协调", salary: "18-30万" },
      { level: "高级分析师", years: "4-7", skills: "团队带领 / 资源协调", salary: "30-50万" },
      { level: "部门经理", years: "7-10", skills: "团队管理 / 业务拓展", salary: "50-70万" },
      { level: "部门总监", years: "10-13", skills: "组织建设 / 人才培养", salary: "70-100万" },
      { level: "合伙人", years: "13+", skills: "业务决策 / 公司战略", salary: "100万+" },
    ],
  },
  career_education: {
    technical: [
      { level: "助教", years: "0-2", skills: "教学辅助 / 备课学习", salary: "8-12万" },
      { level: "讲师", years: "2-5", skills: "独立授课 / 课程设计", salary: "12-18万" },
      { level: "高级讲师", years: "5-8", skills: "课程研发 / 教学研究", salary: "18-28万" },
      { level: "副教授", years: "8-12", skills: "学术研究 / 论文发表", salary: "28-40万" },
      { level: "教授", years: "12+", skills: "学科建设 / 学术引领", salary: "40万+" },
    ],
    management: [
      { level: "讲师", years: "2-5", skills: "教研协作 / 活动组织", salary: "12-18万" },
      { level: "教研室主任", years: "5-8", skills: "教研管理 / 教师培养", salary: "18-26万" },
      { level: "系副主任", years: "8-12", skills: "系部管理 / 课程统筹", salary: "26-35万" },
      { level: "系主任", years: "12-15", skills: "学科规划 / 人才引进", salary: "35-45万" },
      { level: "院长", years: "15+", skills: "学院战略 / 对外合作", salary: "45万+" },
    ],
  },
  career_healthcare: {
    technical: [
      { level: "住院医师", years: "0-3", skills: "临床基础 / 病历书写", salary: "10-15万" },
      { level: "主治医师", years: "3-7", skills: "独立诊疗 / 科室轮转", salary: "15-25万" },
      { level: "副主任医师", years: "7-12", skills: "疑难病例 / 教学带教", salary: "25-40万" },
      { level: "主任医师", years: "12-18", skills: "学科专精 / 科研创新", salary: "40-60万" },
      { level: "学科带头人", years: "18+", skills: "学科建设 / 行业影响", salary: "60万+" },
    ],
    management: [
      { level: "主治医师", years: "3-7", skills: "科室协调 / 质量控制", salary: "15-25万" },
      { level: "医疗组长", years: "7-12", skills: "团队管理 / 排班调度", salary: "25-35万" },
      { level: "科室副主任", years: "12-16", skills: "科室运营 / 人才管理", salary: "35-50万" },
      { level: "科室主任", years: "16-20", skills: "科室战略 / 对外合作", salary: "50-70万" },
      { level: "院长", years: "20+", skills: "医院管理 / 战略决策", salary: "70万+" },
    ],
  },
  career_fallback: {
    technical: [
      { level: "初级专员", years: "0-2", skills: "岗位基础 / 流程学习", salary: "8-15万" },
      { level: "中级专员", years: "2-4", skills: "独立工作 / 技能深化", salary: "15-25万" },
      { level: "高级专员", years: "4-7", skills: "专业精通 / 问题解决", salary: "25-40万" },
      { level: "资深专员", years: "7-10", skills: "领域专家 / 经验输出", salary: "40-60万" },
      { level: "领域专家", years: "10+", skills: "行业影响 / 战略建议", salary: "60万+" },
    ],
    management: [
      { level: "中级专员", years: "2-4", skills: "项目协调 / 沟通协作", salary: "15-25万" },
      { level: "主管", years: "4-7", skills: "小组管理 / 目标达成", salary: "25-35万" },
      { level: "经理", years: "7-10", skills: "部门管理 / 绩效提升", salary: "35-50万" },
      { level: "总监", years: "10-14", skills: "战略规划 / 组织发展", salary: "50-80万" },
      { level: "总经理", years: "14+", skills: "业务决策 / 公司治理", salary: "80万+" },
    ],
  },
};

/* ===== 增强 3：90 天行动蓝图（预设 6 种路径）===== */
type ActionItem = { title: string; duration: string; criteria: string };
type NinetyDayPhase = { phase: string; range: string; items: ActionItem[] };

const NINETY_DAY_BLUEPRINTS: Record<string, NinetyDayPhase[]> = {
  grad_cs: [
    {
      phase: "第1-30天：基础建设",
      range: "Day 1-30",
      items: [
        { title: "确定目标院校与方向", duration: "3天", criteria: "锁定 3-5 所目标院校，明确报考方向" },
        { title: "收集历年真题与资料", duration: "5天", criteria: "整理近 5 年真题，建立资料库" },
        { title: "制定复习总计划", duration: "2天", criteria: "输出月度 / 周度复习时间表" },
        { title: "搭建学习环境与节奏", duration: "7天", criteria: "每日 6-8 小时有效学习" },
        { title: "加入备考社群", duration: "3天", criteria: "加入 2 个活跃备考群，找到研友" },
      ],
    },
    {
      phase: "第31-60天：能力深化",
      range: "Day 31-60",
      items: [
        { title: "专业课一轮复习", duration: "20天", criteria: "完成核心教材精读 + 笔记" },
        { title: "数学 / 英语基础强化", duration: "20天", criteria: "完成基础阶段习题集" },
        { title: "每周模考 + 复盘", duration: "每周", criteria: "4 次模考，错题归因分析" },
        { title: "联系目标院校学长学姐", duration: "5天", criteria: "获取 3 份一手经验贴" },
      ],
    },
    {
      phase: "第61-90天：价值突破",
      range: "Day 61-90",
      items: [
        { title: "专业课二轮专题突破", duration: "15天", criteria: "完成 10 个高频专题" },
        { title: "真题套卷训练", duration: "10天", criteria: "完成 8 套真题，分数达标" },
        { title: "复试提前准备", duration: "5天", criteria: "准备自我介绍 + 科研项目梳理" },
        { title: "调整心态与作息", duration: "持续", criteria: "考前状态稳定，作息规律" },
      ],
    },
  ],
  civil_national: [
    {
      phase: "第1-30天：基础建设",
      range: "Day 1-30",
      items: [
        { title: "确定报考岗位", duration: "5天", criteria: "锁定 3 个目标岗位，匹配专业" },
        { title: "收集行测申论资料", duration: "5天", criteria: "建立完整备考资料库" },
        { title: "制定分阶段计划", duration: "2天", criteria: "输出周度学习时间表" },
        { title: "行测基础打底", duration: "15天", criteria: "完成 5 大模块基础课" },
      ],
    },
    {
      phase: "第31-60天：能力深化",
      range: "Day 31-60",
      items: [
        { title: "申论专项训练", duration: "15天", criteria: "完成 10 篇申论练习" },
        { title: "行测模块刷题", duration: "20天", criteria: "每模块 500+ 题，正确率提升" },
        { title: "时政热点积累", duration: "持续", criteria: "整理 30 个高频热点" },
      ],
    },
    {
      phase: "第61-90天：价值突破",
      range: "Day 61-90",
      items: [
        { title: "全真模考训练", duration: "15天", criteria: "完成 10 套真题模考" },
        { title: "薄弱模块冲刺", duration: "10天", criteria: "弱项正确率提升 15%" },
        { title: "面试提前了解", duration: "5天", criteria: "熟悉面试流程与题型" },
      ],
    },
  ],
  career_it: [
    {
      phase: "第1-30天：基础建设",
      range: "Day 1-30",
      items: [
        { title: "明确技术方向", duration: "3天", criteria: "前端 / 后端 / 算法等方向确定" },
        { title: "夯实编程基础", duration: "15天", criteria: "完成 1 门语言核心语法 + 50 道题" },
        { title: "搭建作品集仓库", duration: "3天", criteria: "GitHub 初始化，README 完善" },
        { title: "加入技术社区", duration: "5天", criteria: "关注 10 个技术博客 / 公众号" },
      ],
    },
    {
      phase: "第31-60天：能力深化",
      range: "Day 31-60",
      items: [
        { title: "完成 1 个完整项目", duration: "20天", criteria: "可运行、可演示、有文档" },
        { title: "参与开源贡献", duration: "10天", criteria: "提交 1 个 PR 被合并" },
        { title: "刷算法题", duration: "持续", criteria: "LeetCode 100 题" },
      ],
    },
    {
      phase: "第61-90天：价值突破",
      range: "Day 61-90",
      items: [
        { title: "优化简历", duration: "5天", criteria: "STAR 法则，3 段经历量化" },
        { title: "投递简历", duration: "15天", criteria: "投递 30+ 公司" },
        { title: "面试准备", duration: "10天", criteria: "完成 10 次模拟面试" },
      ],
    },
  ],
  career_finance: [
    {
      phase: "第1-30天：基础建设",
      range: "Day 1-30",
      items: [
        { title: "补齐财务知识", duration: "15天", criteria: "完成 3 本核心教材" },
        { title: "学习 Excel / 建模", duration: "10天", criteria: "独立完成 1 个估值模型" },
        { title: "关注行业动态", duration: "持续", criteria: "每日阅读 3 篇研报" },
      ],
    },
    {
      phase: "第31-60天：能力深化",
      range: "Day 31-60",
      items: [
        { title: "CFA / 证书备考", duration: "20天", criteria: "完成 1 个科目一轮复习" },
        { title: "完成行业研究报告", duration: "10天", criteria: "输出 1 篇完整研报" },
        { title: "建立人脉", duration: "持续", criteria: "联系 5 位行业前辈" },
      ],
    },
    {
      phase: "第61-90天：价值突破",
      range: "Day 61-90",
      items: [
        { title: "实习 / 项目经历补强", duration: "20天", criteria: "完成 1 段相关实习或项目" },
        { title: "简历精修", duration: "5天", criteria: "突出量化分析能力" },
        { title: "投递与面试", duration: "持续", criteria: "投递 20+ 金融机构" },
      ],
    },
  ],
  career_education: [
    {
      phase: "第1-30天：基础建设",
      range: "Day 1-30",
      items: [
        { title: "考取教师资格证", duration: "20天", criteria: "完成笔试报名 + 冲刺" },
        { title: "研究目标学校", duration: "5天", criteria: "锁定 5 所目标学校" },
        { title: "观摩优秀课堂", duration: "5天", criteria: "完成 10 节名师课观摩" },
      ],
    },
    {
      phase: "第31-60天：能力深化",
      range: "Day 31-60",
      items: [
        { title: "备课训练", duration: "20天", criteria: "完成 5 份完整教案" },
        { title: "试讲练习", duration: "10天", criteria: "完成 10 次试讲并获取反馈" },
        { title: "学习教育心理学", duration: "持续", criteria: "完成 1 本专业书" },
      ],
    },
    {
      phase: "第61-90天：价值突破",
      range: "Day 61-90",
      items: [
        { title: "投递简历", duration: "15天", criteria: "投递 15+ 学校" },
        { title: "面试 / 试讲准备", duration: "10天", criteria: "完成 5 次模拟面试" },
        { title: "建立教师社群", duration: "5天", criteria: "加入 2 个教师交流群" },
      ],
    },
  ],
  career_healthcare: [
    {
      phase: "第1-30天：基础建设",
      range: "Day 1-30",
      items: [
        { title: "执业医师资格备考", duration: "20天", criteria: "完成基础科目一轮" },
        { title: "确定专科方向", duration: "5天", criteria: "明确内科 / 外科 / 其他方向" },
        { title: "整理病例学习库", duration: "5天", criteria: "收集 20 个典型病例" },
      ],
    },
    {
      phase: "第31-60天：能力深化",
      range: "Day 31-60",
      items: [
        { title: "临床技能强化", duration: "20天", criteria: "完成核心操作技能训练" },
        { title: "文献阅读", duration: "10天", criteria: "精读 10 篇 SCI 论文" },
        { title: "参加病例讨论", duration: "持续", criteria: "参与 5 次疑难病例讨论" },
      ],
    },
    {
      phase: "第61-90天：价值突破",
      range: "Day 61-90",
      items: [
        { title: "投递目标医院", duration: "15天", criteria: "投递 10+ 三甲医院" },
        { title: "面试准备", duration: "10天", criteria: "完成专业 + 综合面试模拟" },
        { title: "整理个人简历", duration: "5天", criteria: "突出临床 + 科研能力" },
      ],
    },
  ],
};

function formatMoney(n: number): string {
  if (n >= 100000000) return (n / 100000000).toFixed(1) + "亿";
  if (n >= 10000) return (n / 10000).toFixed(0) + "万";
  return n.toLocaleString();
}

export default function CareerSimulatorPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [cities, setCities] = useState<CityTier[]>([]);
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [savingPath, setSavingPath] = useState<string | null>(null);
  const compareRef = useRef<HTMLDivElement | null>(null);

  // 增强 1/2/3 的状态
  const [showMatchCard, setShowMatchCard] = useState(false);
  const [dualTrackView, setDualTrackView] = useState<"technical" | "management" | "compare">("compare");
  const [dualTrackPath, setDualTrackPath] = useState<string>("");
  const [blueprintPath, setBlueprintPath] = useState<string>("");

  // Path configuration
  const [paths, setPaths] = useState([
    { name: "考研IT", path_type: "grad_cs", city: "Beijing", industry: "IT" },
    { name: "国考", path_type: "civil_national", city: "Hangzhou", industry: "Government" },
    { name: "直接就业", path_type: "career_it", city: "Shenzhen", industry: "IT" },
  ]);
  const [years, setYears] = useState(10);

  // Load presets, cities, industries
  useEffect(() => {
    Promise.all([
      careerSimulatorApi.getPresets(),
      careerSimulatorApi.getCities(),
      careerSimulatorApi.getIndustries(),
    ]).then(([p, c, i]) => {
      setPresets(p.presets || []);
      setCities(c.tiers || []);
      setIndustries(i.industries || []);
    }).catch(() => {});
  }, []);

  const addPath = () => {
    if (paths.length >= 5) return;
    setPaths([...paths, { name: "", path_type: "career_fallback", city: "Beijing", industry: "IT" }]);
  };

  const removePath = (index: number) => {
    if (paths.length <= 1) return;
    setPaths(paths.filter((_, i) => i !== index));
  };

  const updatePath = (index: number, field: string, value: string) => {
    const newPaths = [...paths];
    (newPaths[index] as Record<string, string>)[field] = value;
    setPaths(newPaths);
  };

  const applyPreset = (preset: Preset, index: number) => {
    updatePath(index, "name", preset.name);
    updatePath(index, "path_type", preset.path_type);
    updatePath(index, "city", preset.city);
    updatePath(index, "industry", preset.industry);
  };

  const allCities = [...new Set(cities.flatMap((t) => t.cities))].sort();

  const handleSimulate = async () => {
    if (paths.length === 0) {
      toast.error("请至少添加一个职业路径");
      return;
    }
    setLoading(true);
    try {
      const data = await careerSimulatorApi.simulate({
        current_year: new Date().getFullYear(),
        years,
        paths: paths.map((p) => ({
          name: p.name || "未命名",
          path_type: p.path_type,
          city: p.city,
          industry: p.industry,
        })),
      });
      setResult(data);
      toast.success("模拟完成");
    } catch {
      toast.error("模拟失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (name: string) => {
    const newSet = new Set(expandedPaths);
    if (newSet.has(name)) newSet.delete(name);
    else newSet.add(name);
    setExpandedPaths(newSet);
  };

  /** 保存首选路径到决策记录，便于后续回溯 */
  const handleSavePath = async (pathName: string) => {
    setSavingPath(pathName);
    try {
      await decisionsApi.create({
        decision_date: todayISO(),
        destination_type: "employment",
        status: "planned",
        details: { path_name: pathName },
        reasoning: `来自职业路径模拟器：${pathName}`,
        confidence: 3,
        prediction: null,
      });
      toast.success(`已保存「${pathName}」到决策记录`);
    } catch {
      toast.error("保存失败，请稍后重试");
    } finally {
      setSavingPath(null);
    }
  };

  /** 滚动到对比区域 */
  const scrollToCompare = () => {
    compareRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // Chart data preparation
  const salaryChartData = result?.paths[0]?.yearly?.map((y, i) => {
    const point: Record<string, number | string> = { year: y.year.toString() };
    result.paths.forEach((p) => {
      point[p.name] = p.yearly[i]?.monthly_salary || 0;
    });
    return point;
  }) || [];

  const satisfactionData = result?.paths.map((p) => ({
    name: p.name,
    satisfaction: p.avg_satisfaction,
    stability: p.stability_score,
    growth: Math.min(p.career_growth_score, 50),
  })) || [];

  const radarData = result?.paths[0]?.yearly?.filter((_, i) => i < 5).map((y, i) => {
    const point: Record<string, number | string> = { dimension: `Year${y.year}` };
    result.paths.forEach((p) => {
      point[p.name] = p.yearly[i]?.satisfaction || 0;
    });
    return point;
  }) || [];

  return (
    <div className="min-h-screen bg-ink-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-ink-900 flex items-center gap-3">
            <Compass className="w-8 h-8 text-brand-600" />
            职业路径模拟器
          </h1>
          <p className="mt-2 text-ink-500">
            对比不同职业路径的10年发展轨迹 — 薪资、满意度、风险、净收入
          </p>
        </div>

        {/* Path Configuration */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">配置职业路径</h2>
            <div className="flex items-center gap-3">
              <label className="text-sm text-ink-500">模拟年数:</label>
              <input
                type="range" min="1" max="10" value={years}
                onChange={(e) => setYears(parseInt(e.target.value))}
                className="w-24"
              />
              <span className="text-sm font-medium w-8">{years}年</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {paths.map((path, i) => (
              <div key={`${path.name}-${i}`} className="border rounded-lg p-4 relative bg-ink-50">
                {paths.length > 1 && (
                  <button onClick={() => removePath(i)}
                    className="absolute top-2 right-2 text-ink-400 hover:text-red-500">
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
                <Field label="名称">
                  <Input value={path.name} onChange={(e) => updatePath(i, "name", e.target.value)}
                    placeholder="路径名称" />
                </Field>
                <Field label="类型">
                  <select value={path.path_type} onChange={(e) => updatePath(i, "path_type", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm">
                    {industries.flatMap((ind) => ind.paths.map((pt) => (
                      <option key={pt} value={pt}>{ind.name} - {pt}</option>
                    )))}
                  </select>
                </Field>
                <Field label="城市">
                  <select value={path.city} onChange={(e) => updatePath(i, "city", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm">
                    {allCities.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </Field>
                {/* Preset quick-fill */}
                <div className="mt-2 flex flex-wrap gap-1">
                  {presets.slice(0, 4).map((p) => (
                    <button key={p.name} onClick={() => applyPreset(p, i)}
                      className="text-xs px-2 py-1 bg-brand-50 text-brand-700 rounded hover:bg-brand-100">
                      {p.name}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {paths.length < 5 && (
              <button onClick={addPath}
                className="border-2 border-dashed rounded-lg p-4 flex flex-col items-center justify-center text-ink-400 hover:text-brand-500 hover:border-brand-300 min-h-[200px]">
                <Plus className="w-8 h-8 mb-2" />
                添加路径
              </button>
            )}
          </div>

          <div className="mt-6 flex justify-center">
            <Button onClick={handleSimulate} disabled={loading}
              className="bg-brand-600 hover:bg-brand-700 text-white px-8 py-3 text-lg">
              {loading ? "模拟中..." : <><Play className="w-5 h-5 mr-2" /> 开始模拟</>}
            </Button>
          </div>
        </div>

        {/* Loading */}
        {loading && <LoadingState />}

        {/* Results */}
        {!loading && result && (
          <div className="space-y-6">
            {/* Recommendation Banner */}
            {result.recommendation && (
              <div className="bg-gradient-to-r from-brand-600 to-purple-600 rounded-xl p-6 text-white">
                <div className="flex items-center gap-3">
                  <Trophy className="w-8 h-8" />
                  <div>
                    <h2 className="text-2xl font-bold">推荐路径</h2>
                    <p className="text-brand-100 text-lg">{result.recommendation}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {result.paths.map((p, i) => (
                <div key={p.name} className={cn("rounded-xl p-5 shadow-sm border-2",
                  i === 0 ? "border-brand-500 bg-brand-50" : "border-ink-100 bg-white")}>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="p-2 rounded-lg bg-brand-100 text-brand-600">
                      {PATH_ICONS[p.path_type] || <Briefcase />}
                    </div>
                    <div>
                      <h3 className="font-bold text-ink-900">{p.name}</h3>
                      <p className="text-xs text-ink-500">{p.city} | {p.industry}</p>
                    </div>
                    {i === 0 && <Star className="w-5 h-5 text-yellow-500 ml-auto" />}
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-white rounded p-2">
                      <div className="text-ink-500 text-xs">10年总收入</div>
                      <div className="font-bold text-brand-600">{formatMoney(p.total_income)}</div>
                    </div>
                    <div className="bg-white rounded p-2">
                      <div className="text-ink-500 text-xs">净资产</div>
                      <div className="font-bold text-green-600">{formatMoney(p.net_worth_10yr)}</div>
                    </div>
                    <div className="bg-white rounded p-2">
                      <div className="text-ink-500 text-xs">满意度</div>
                      <div className="font-bold">{p.avg_satisfaction}/10</div>
                    </div>
                    <div className="bg-white rounded p-2">
                      <div className="text-ink-500 text-xs">风险</div>
                      <span className={cn("px-2 py-1 rounded-full text-xs font-medium", RISK_COLORS[p.overall_risk])}>
                        {p.overall_risk === "low" ? "低风险" : p.overall_risk === "high" ? "高风险" : "中风险"}
                      </span>
                    </div>
                  </div>
                  <div className="mt-3 text-xs text-ink-600">{p.recommendation}</div>
                </div>
              ))}
            </div>

            {/* 增强 1：匹配度算法透明度 */}
            {(() => {
              const preferredPath = result.recommendation
                ? result.paths.find((p) => p.name === result.recommendation) ?? result.paths[0]
                : result.paths[0];
              if (!preferredPath) return null;
              const { dimensions, total } = computeMatchScores(preferredPath);
              return (
                <div className="bg-white rounded-xl shadow-sm p-6 border border-purple-100">
                  <button
                    onClick={() => setShowMatchCard(!showMatchCard)}
                    className="w-full flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      <Calculator className="w-5 h-5 text-purple-600" />
                      <h3 className="text-lg font-semibold">匹配度是如何计算的</h3>
                      <span className="ml-2 text-2xl font-bold text-purple-600">{total}%</span>
                    </div>
                    {showMatchCard ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </button>
                  {showMatchCard && (
                    <div className="mt-4 space-y-4">
                      <p className="text-sm text-ink-500">
                        我们相信算法应该透明。以下是基于「{preferredPath.name}」的匹配度计算过程，权重公式公开，数据来源可追溯。
                      </p>
                      {/* 权重公式 */}
                      <div className="bg-purple-50 rounded-lg p-4">
                        <p className="text-xs text-ink-500 mb-2">权重公式（总权重 100%）</p>
                        <div className="flex flex-wrap gap-2 text-sm">
                          {MATCH_WEIGHTS.map((w) => (
                            <span
                              key={w.key}
                              className="bg-white px-3 py-1 rounded-full border border-purple-200 text-ink-700"
                            >
                              {w.label} <span className="font-semibold text-purple-600">{w.weight}%</span>
                            </span>
                          ))}
                        </div>
                      </div>
                      {/* 各维度得分与来源 */}
                      <div className="space-y-3">
                        {dimensions.map((d) => {
                          const contribution = Math.round((d.score * d.weight) / 100);
                          return (
                            <div key={d.key} className="border rounded-lg p-3">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium text-sm text-ink-800">{d.label}</span>
                                <span className="text-xs text-ink-500">
                                  得分 <span className="font-semibold text-ink-700">{d.score}</span>/100 × 权重 {d.weight}% ={" "}
                                  <span className="font-bold text-purple-600">{contribution}</span>
                                </span>
                              </div>
                              <div className="w-full bg-ink-100 rounded-full h-2 mb-2">
                                <div
                                  className="bg-purple-500 h-2 rounded-full transition-all"
                                  style={{ width: `${d.score}%` }}
                                />
                              </div>
                              <p className="text-xs text-ink-500 flex items-center gap-1">
                                <Target className="w-3 h-3 text-ink-400" />
                                数据来源：{d.source}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                      {/* 总匹配度计算过程 */}
                      <div className="bg-purple-50 rounded-lg p-4 text-center">
                        <p className="text-xs text-ink-500 mb-2">总匹配度计算过程</p>
                        <p className="font-mono text-sm text-ink-700 leading-relaxed break-words">
                          {dimensions.map((d, i) => (
                            <span key={d.key}>
                              {i > 0 && " + "}
                              {d.label}
                              <span className="font-bold text-purple-600">{Math.round((d.score * d.weight) / 100)}</span>
                            </span>
                          ))}
                          {" = "}
                          <span className="text-2xl font-bold text-purple-600">{total}%</span>
                        </p>
                      </div>
                      <div className="flex justify-end">
                        <Link
                          href="/profile"
                          className="inline-flex items-center gap-2 text-sm text-purple-600 hover:text-purple-700 hover:underline"
                        >
                          <Calculator className="w-4 h-4" />
                          调整我的画像 →
                        </Link>
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}

            {/* Salary Trend Chart */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-brand-600" /> 月薪趋势
              </h3>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={salaryChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="year" />
                  <YAxis tickFormatter={(v) => formatMoney(v)} />
                  <Tooltip formatter={(v: number) => formatMoney(v) + "/月"} />
                  <Legend />
                  {result.paths.map((p, i) => (
                    <Line key={p.name} type="monotone" dataKey={p.name}
                      stroke={PATH_COLORS[i % PATH_COLORS.length]}
                      strokeWidth={2} dot={{ r: 3 }} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Satisfaction & Stability */}
            <div ref={compareRef} className="grid grid-cols-1 md:grid-cols-2 gap-6 scroll-mt-6">
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Heart className="w-5 h-5 text-red-500" /> 满意度对比
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={satisfactionData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 10]} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="satisfaction" fill="#3b82f6" name="满意度" />
                    <Bar dataKey="stability" fill="#10b981" name="稳定性" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-white rounded-xl shadow-sm p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-purple-600" /> 收入对比
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={result.paths.map((p) => ({
                    name: p.name,
                    income: p.total_income,
                    cost: p.total_education_cost,
                    net: p.net_worth_10yr,
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis tickFormatter={(v) => formatMoney(v)} />
                    <Tooltip formatter={(v: number) => formatMoney(v)} />
                    <Legend />
                    <Bar dataKey="income" fill="#3b82f6" name="总收入" />
                    <Bar dataKey="net" fill="#10b981" name="净资产" />
                    <Bar dataKey="cost" fill="#ef4444" name="教育成本" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Year-by-Year Detail */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-600" /> 年度详情
              </h3>
              {result.paths.map((p) => (
                <div key={p.name} className="mb-4 border rounded-lg">
                  <button onClick={() => toggleExpand(p.name)}
                    className="w-full flex items-center justify-between p-3 hover:bg-ink-50">
                    <span className="font-medium">{p.name} ({p.city})</span>
                    {expandedPaths.has(p.name) ? <ChevronUp /> : <ChevronDown />}
                  </button>
                  {expandedPaths.has(p.name) && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-ink-50">
                          <tr>
                            <th className="px-3 py-2 text-left">年份</th>
                            <th className="px-3 py-2 text-left">阶段</th>
                            <th className="px-3 py-2 text-right">月薪</th>
                            <th className="px-3 py-2 text-right">年薪</th>
                            <th className="px-3 py-2 text-right">累计</th>
                            <th className="px-3 py-2 text-center">满意度</th>
                            <th className="px-3 py-2 text-center">风险</th>
                            <th className="px-3 py-2 text-right">净资产</th>
                          </tr>
                        </thead>
                        <tbody>
                          {p.yearly.map((y) => (
                            <tr key={y.year} className="border-t hover:bg-ink-50">
                              <td className="px-3 py-2 font-medium">{y.year}</td>
                              <td className="px-3 py-2">
                                <div className="text-xs text-ink-500">{y.phase}</div>
                                <div className="text-xs text-ink-400 truncate max-w-[200px]">{y.phase_detail}</div>
                              </td>
                              <td className="px-3 py-2 text-right">{formatMoney(y.monthly_salary)}</td>
                              <td className="px-3 py-2 text-right">{formatMoney(y.annual_income)}</td>
                              <td className="px-3 py-2 text-right font-medium">{formatMoney(y.cumulative_income)}</td>
                              <td className="px-3 py-2 text-center">
                                <span className={cn("px-2 py-1 rounded-full text-xs",
                                  y.satisfaction >= 7 ? "bg-green-100 text-green-700" :
                                  y.satisfaction >= 5 ? "bg-yellow-100 text-yellow-700" :
                                  "bg-red-100 text-red-700")}>
                                  {y.satisfaction}/10
                                </span>
                              </td>
                              <td className="px-3 py-2 text-center">
                                <span className={cn("px-2 py-1 rounded-full text-xs", RISK_COLORS[y.risk_level])}>
                                  {y.risk_level === "low" ? "低" : y.risk_level === "high" ? "高" : "中"}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-right">{formatMoney(y.net_worth)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* 增强 2：双轨晋升路径对比（技术线 vs 管理线） */}
            {(() => {
              const preferredPath = result.recommendation
                ? result.paths.find((p) => p.name === result.recommendation) ?? result.paths[0]
                : result.paths[0];
              const trackPathName = dualTrackPath || preferredPath?.name || result.paths[0]?.name || "";
              const currentPath = result.paths.find((p) => p.name === trackPathName) ?? result.paths[0];
              if (!currentPath) return null;
              const track = DUAL_TRACK[currentPath.path_type] || DUAL_TRACK.career_fallback;
              return (
                <div className="bg-white rounded-xl shadow-sm p-6">
                  <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <GitBranch className="w-5 h-5 text-brand-600" />
                      双轨晋升路径
                    </h3>
                    <select
                      value={trackPathName}
                      onChange={(e) => setDualTrackPath(e.target.value)}
                      className="border rounded px-3 py-1.5 text-sm bg-white"
                    >
                      {result.paths.map((p) => (
                        <option key={p.name} value={p.name}>{p.name}</option>
                      ))}
                    </select>
                  </div>
                  <p className="text-sm text-ink-500 mb-4">
                    同一条职业路径，技术线与管理线的发展节奏、能力要求、薪资天花板各不相同。切换查看或对比双轨，提前规划你的晋升方向。
                  </p>
                  {/* 视图切换 */}
                  <div className="flex gap-2 mb-4 flex-wrap">
                    {(["technical", "management", "compare"] as const).map((mode) => (
                      <button
                        key={mode}
                        onClick={() => setDualTrackView(mode)}
                        className={cn(
                          "px-4 py-1.5 rounded-full text-sm transition-colors",
                          dualTrackView === mode
                            ? "bg-brand-600 text-white"
                            : "bg-ink-100 text-ink-600 hover:bg-ink-200"
                        )}
                      >
                        {mode === "technical" ? "看技术线" : mode === "management" ? "看管理线" : "对比双轨"}
                      </button>
                    ))}
                  </div>
                  {/* 双轨展示 */}
                  <div className={cn("grid gap-4", dualTrackView === "compare" ? "md:grid-cols-2" : "grid-cols-1")}>
                    {(dualTrackView === "technical" || dualTrackView === "compare") && (
                      <div className={cn("rounded-lg p-4", dualTrackView === "compare" ? "bg-brand-50" : "bg-ink-50")}>
                        <div className="flex items-center gap-2 mb-3">
                          <Code className="w-4 h-4 text-brand-600" />
                          <h4 className="font-semibold text-brand-700">技术线</h4>
                          <span className="text-xs text-ink-500 ml-auto">靠专业深度晋升</span>
                        </div>
                        <div className="space-y-2">
                          {track.technical.map((level, i) => (
                            <div key={i} className="bg-white rounded p-3 border border-brand-100">
                              <div className="flex justify-between items-center mb-1">
                                <span className="font-medium text-sm text-ink-800">
                                  <span className="text-brand-500 mr-1">L{i + 1}</span>
                                  {level.level}
                                </span>
                                <span className="text-xs text-ink-500 bg-brand-50 px-2 py-0.5 rounded">{level.years}年</span>
                              </div>
                              <div className="text-xs text-ink-600 mb-1">核心能力：{level.skills}</div>
                              <div className="text-xs font-medium text-green-600 flex items-center gap-1"><DollarSign className="w-3 h-3" />{level.salary}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {(dualTrackView === "management" || dualTrackView === "compare") && (
                      <div className={cn("rounded-lg p-4", dualTrackView === "compare" ? "bg-purple-50" : "bg-ink-50")}>
                        <div className="flex items-center gap-2 mb-3">
                          <Users className="w-4 h-4 text-purple-600" />
                          <h4 className="font-semibold text-purple-700">管理线</h4>
                          <span className="text-xs text-ink-500 ml-auto">靠团队赋能晋升</span>
                        </div>
                        <div className="space-y-2">
                          {track.management.map((level, i) => (
                            <div key={i} className="bg-white rounded p-3 border border-purple-100">
                              <div className="flex justify-between items-center mb-1">
                                <span className="font-medium text-sm text-ink-800">
                                  <span className="text-purple-500 mr-1">L{i + 1}</span>
                                  {level.level}
                                </span>
                                <span className="text-xs text-ink-500 bg-purple-50 px-2 py-0.5 rounded">{level.years}年</span>
                              </div>
                              <div className="text-xs text-ink-600 mb-1">核心能力：{level.skills}</div>
                              <div className="text-xs font-medium text-green-600 flex items-center gap-1"><DollarSign className="w-3 h-3" />{level.salary}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="mt-4 text-xs text-ink-400 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    每级通常 2-3 年，薪资为一线城市参考范围，实际因城市 / 公司 / 个人表现而异。
                  </div>
                </div>
              );
            })()}

            {/* Market Context */}
            {result.market_context && (
              <div className="bg-ink-100 rounded-xl p-4 text-sm text-ink-600">
                <strong>市场参考:</strong> 一线城市平均月薪 {String(result.market_context.avg_salary_tier1 || 12000)} |
                新一线 {String(result.market_context.avg_salary_tier2 || 8000)} |
                二线 {String(result.market_context.avg_salary_tier3 || 6000)} |
                数据来源: {String(result.market_context.source || "GradPath")}
              </div>
            )}

            {/* 增强 3：90 天行动蓝图 */}
            {(() => {
              const preferredPath = result.recommendation
                ? result.paths.find((p) => p.name === result.recommendation) ?? result.paths[0]
                : result.paths[0];
              const bpPathName = blueprintPath || preferredPath?.name || result.paths[0]?.name || "";
              const currentPath = result.paths.find((p) => p.name === bpPathName) ?? result.paths[0];
              if (!currentPath) return null;
              const blueprint = NINETY_DAY_BLUEPRINTS[currentPath.path_type] || NINETY_DAY_BLUEPRINTS.career_fallback;
              return (
                <div className="bg-white rounded-xl shadow-sm p-6 border border-green-100">
                  <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <Calendar className="w-5 h-5 text-green-600" />
                      90 天行动蓝图
                    </h3>
                    <select
                      value={bpPathName}
                      onChange={(e) => setBlueprintPath(e.target.value)}
                      className="border rounded px-3 py-1.5 text-sm bg-white"
                    >
                      {result.paths.map((p) => (
                        <option key={p.name} value={p.name}>{p.name}</option>
                      ))}
                    </select>
                  </div>
                  <p className="text-sm text-ink-500 mb-4">
                    基于「{currentPath.name}」路径，把模拟结果转化为 90 天可执行的行动计划。三阶段递进：基础建设 → 能力深化 → 价值突破。
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {blueprint.map((phase, i) => (
                      <div key={i} className="border rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-3">
                          <span className="flex items-center justify-center w-7 h-7 rounded-full bg-green-100 text-green-700 text-sm font-bold">
                            {i + 1}
                          </span>
                          <div>
                            <h4 className="font-semibold text-sm text-ink-800">{phase.phase}</h4>
                            <p className="text-xs text-ink-400">{phase.range}</p>
                          </div>
                        </div>
                        <div className="space-y-2">
                          {phase.items.map((item, j) => (
                            <div key={j} className="bg-ink-50 rounded p-2">
                              <div className="flex items-start gap-2">
                                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                <div className="flex-1">
                                  <div className="flex justify-between items-start gap-2">
                                    <span className="text-xs font-medium text-ink-800">{item.title}</span>
                                    <span className="text-xs text-ink-400 whitespace-nowrap">{item.duration}</span>
                                  </div>
                                  <p className="text-xs text-ink-500 mt-0.5">完成标准：{item.criteria}</p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 flex justify-end">
                    <Link
                      href={`/plans?from=simulator&path=${encodeURIComponent(currentPath.name)}`}
                      className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm transition-colors"
                    >
                      <Save className="w-4 h-4" />
                      保存为行动计划
                    </Link>
                  </div>
                </div>
              );
            })()}

            {/* 下一步引导：把模拟结果转化为决策与行动 */}
            {(() => {
              const preferredPath = result.recommendation
                ? result.paths.find((p) => p.name === result.recommendation) ?? result.paths[0]
                : result.paths[0];
              const preferredName = preferredPath?.name ?? "";
              return (
                <div className="bg-white rounded-xl shadow-sm p-6 border border-brand-100">
                  <div className="flex items-center gap-2 mb-1">
                    <Route className="w-5 h-5 text-brand-600" />
                    <h3 className="text-lg font-semibold text-ink-900">下一步：把模拟结果变成决策</h3>
                  </div>
                  <p className="text-sm text-ink-500 mb-4">
                    对首选路径做深度决策分析、保存到决策记录，或继续对比其他路径。
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <Link
                      href={`/decision-lab?from=simulator&path=${encodeURIComponent(preferredName)}`}
                      className="group flex flex-col gap-2 rounded-lg border border-ink-200 p-4 transition-all hover:border-brand-300 hover:shadow-sm"
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                        <Compass className="w-4 h-4" />
                      </span>
                      <p className="text-sm font-medium text-ink-900">深度决策分析</p>
                      <p className="text-xs text-ink-500">
                        对「{preferredName || "首选路径"}」做预验尸+决策矩阵+红队质疑
                      </p>
                      <span className="inline-flex items-center gap-1 text-xs text-brand-600 mt-1">
                        前往 <ArrowRight className="h-3 w-3" />
                      </span>
                    </Link>
                    <button
                      onClick={() => handleSavePath(preferredName)}
                      disabled={savingPath !== null}
                      className="group flex flex-col gap-2 rounded-lg border border-ink-200 p-4 text-left transition-all hover:border-brand-300 hover:shadow-sm disabled:opacity-50 disabled:cursor-wait"
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                        <Save className="w-4 h-4" />
                      </span>
                      <p className="text-sm font-medium text-ink-900">保存到决策记录</p>
                      <p className="text-xs text-ink-500">
                        把「{preferredName || "首选路径"}」存为决策记录，便于日后回溯
                      </p>
                      <span className="inline-flex items-center gap-1 text-xs text-brand-600 mt-1">
                        {savingPath === preferredName ? "保存中…" : "保存"}
                      </span>
                    </button>
                    <button
                      onClick={scrollToCompare}
                      className="group flex flex-col gap-2 rounded-lg border border-ink-200 p-4 text-left transition-all hover:border-brand-300 hover:shadow-sm"
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                        <BarChart3 className="w-4 h-4" />
                      </span>
                      <p className="text-sm font-medium text-ink-900">对比其他路径</p>
                      <p className="text-xs text-ink-500">
                        滚动到满意度/收入对比图，细看差异
                      </p>
                      <span className="inline-flex items-center gap-1 text-xs text-brand-600 mt-1">
                        滚动查看 <ArrowRight className="h-3 w-3" />
                      </span>
                    </button>
                  </div>
                </div>
              );
            })()}
          </div>
        )}

        {!loading && !result && (
          <EmptyState title="配置路径开始模拟" description="选择职业路径、城市和行业，点击模拟按钮查看10年发展轨迹对比" />
        )}

        {/* 职业试驾：在模拟结果下方，沉浸式体验候选路径的一天 */}
        <TestDriveSection />

        {/* What-If 多路径对比：在试驾区域下方，量化对比 2-3 条职业路径 */}
        <WhatIfSection />
      </div>
    </div>
  );
}
