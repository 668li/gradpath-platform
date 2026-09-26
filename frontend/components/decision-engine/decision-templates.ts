// frontend/components/decision-engine/decision-templates.ts
// 示例决策模板（用于决策中心空态引导，用户「以此创建」时预填表单，不写库）。
// 独立模块：Next.js page 文件禁止导出自定义符号（tsc 强约束），数据与页面分离。
import type { DecisionResponse } from "@/types";

export type DecisionTemplate = Omit<
  DecisionResponse,
  "id" | "user_id" | "created_at" | "updated_at"
>;

export const DECISION_TEMPLATES: DecisionTemplate[] = [
  {
    destination_type: "postgrad",
    status: "planned",
    decision_date: "",
    review_date: "",
    reasoning:
      "本科双非一本计算机，GPA 3.4/4.0，有两段中小厂后端实习。目标进大厂算法/研发岗，但双非学历在简历筛选阶段吃亏；读研既能刷新院校背景（冲 985/强势 211），又能补强算法与机器学习基础，为转算法岗铺路。",
    prediction: "若上岸中上游 985（如川大/中南/山大档）计算机专硕，秋招算法/研发岗竞争力明显提升，目标年薪 35w+（含股票与签字费）；若落到强势 211，则 25-30w 区间更现实。",
    assumptions: [
      "数学一与 408 专业课基础尚可，统考目标 380 分左右",
      "能承受脱产 1 年 + 学费/生活成本的沉没成本",
      "目标院校计算机报录比 < 8:1，且专业课不压分",
      "读研期间能拿到一段大厂算法相关实习",
    ],
    details: { school: "某 985 高校（统考 408）", major: "计算机技术（专硕）", target_score: "380（政治 65 / 英二 75 / 数一 125 / 408 115）" },
    confidence: 3,
    ai_analysis: null,
    actual_outcome: null,
    review_notes: null,
  },
  {
    destination_type: "employment",
    status: "planned",
    decision_date: "",
    review_date: "",
    reasoning:
      "已有两段实习（一段 B 轮 SaaS 中厂后端、一段大厂暑期实习拿 return offer 意向）。先就业积累 2 年工程经验与项目履历，再视情况决定是否考研或内部转岗；直接读研的机会成本偏高。",
    prediction: "入职后 2 年内可成长为独立开发者/小组骨干，年薪有望达 25-30w（base 20w + 年终 + 期权）；若 return offer 落定，起薪可直接到 30w+。",
    assumptions: [
      "暑期实习转正概率高（面试官已口头承诺 return）",
      "技术栈（Go/微服务）与岗位匹配，无需大规模补课",
      "可接受一线城市节奏（加班 + 租房成本）",
      "两年内保持学习，避免技术停滞",
    ],
    details: { company: "某 B 轮 SaaS 中厂（约 500 人）", position: "后端开发工程师（Go）" },
    confidence: 4,
    ai_analysis: null,
    actual_outcome: null,
    review_notes: null,
  },
];
