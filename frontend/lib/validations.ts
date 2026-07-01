import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("请输入有效的邮箱地址"),
  password: z.string().min(8, "密码至少 8 位"),
});

export const registerSchema = z.object({
  email: z.string().email("请输入有效的邮箱地址"),
  password: z.string().min(8, "密码至少 8 位").max(128, "密码最多 128 位"),
  name: z.string().min(1, "请输入姓名").max(100, "姓名最多 100 字"),
});

export const decisionSchema = z.object({
  destination_type: z.enum([
    "employment",
    "postgrad",
    "civil_service",
    "abroad",
    "phd",
    "startup",
    "gap_year",
  ]),
  status: z.enum(["planned", "confirmed", "executed", "changed"]),
  confidence: z.number().int().min(1, "请选择信心度").max(5, "信心度最高 5"),
  decision_date: z.string().min(1, "请选择决策日期"),
  reasoning: z.string().max(2000, "理由最多 2000 字").optional(),
});

export const skillSchema = z.object({
  name: z.string().min(1, "请输入技能名称").max(100, "名称最多 100 字"),
  category: z.string().min(1, "请选择类别"),
  level: z.number().int().min(1, "等级最低 1").max(5, "等级最高 5"),
  parent_id: z.string().optional(),
  notes: z.string().max(500, "备注最多 500 字").optional(),
});

export const eventSchema = z.object({
  title: z.string().min(1, "请输入事件标题").max(200, "标题最多 200 字"),
  event_type: z.string().min(1, "请选择事件类型"),
  event_date: z.string().min(1, "请选择日期"),
});

export const retroSchema = z
  .object({
    title: z.string().min(1, "请输入标题").max(200, "标题最多 200 字"),
    period_type: z.string().min(1, "请选择复盘类型"),
    period_start: z.string().min(1, "请选择开始日期"),
    period_end: z.string().min(1, "请选择结束日期"),
    satisfaction: z.number().int().min(1, "请选择满意度").max(5, "满意度最高 5"),
  })
  .refine((data) => data.period_end >= data.period_start, {
    message: "结束日期不能早于开始日期",
    path: ["period_end"],
  });

export type LoginForm = z.infer<typeof loginSchema>;
export type RegisterForm = z.infer<typeof registerSchema>;

export const knowledgeSchema = z.object({
  category: z.string().min(1, "请选择分类"),
  title: z.string().min(1, "标题不能为空").max(200, "标题最多 200 字"),
  content: z.string().min(1, "内容不能为空"),
  source: z.string().max(200, "来源最多 200 字").optional().nullable(),
  is_published: z.boolean().default(true),
});

export type KnowledgeForm = z.infer<typeof knowledgeSchema>;
