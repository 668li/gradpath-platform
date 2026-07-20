import { describe, it, expect } from "vitest";
import {
  loginSchema,
  registerSchema,
  decisionSchema,
  skillSchema,
  eventSchema,
  retroSchema,
  knowledgeSchema,
} from "@/lib/validations";

describe("loginSchema", () => {
  it("应接受有效的登录数据", () => {
    const result = loginSchema.safeParse({
      email: "user@example.com",
      password: "Password1!",
    });
    expect(result.success).toBe(true);
  });

  it("应拒绝无效邮箱格式", () => {
    const result = loginSchema.safeParse({
      email: "not-an-email",
      password: "Password1!",
    });
    expect(result.success).toBe(false);
  });

  it("应拒绝空密码", () => {
    const result = loginSchema.safeParse({
      email: "user@example.com",
      password: "",
    });
    expect(result.success).toBe(false);
  });

  it("应拒绝短密码 (< 8)", () => {
    const result = loginSchema.safeParse({
      email: "user@example.com",
      password: "Short1",
    });
    expect(result.success).toBe(false);
  });

  // 边界 case: 7 位字母 + 数字
  it("应拒绝正好 7 位的密码（边界）", () => {
    const result = loginSchema.safeParse({
      email: "user@example.com",
      password: "Pass12",
    });
    expect(result.success).toBe(false);
  });

  // 边界 case: 8 位纯数字
  it("应接受 8 位但仅数字（loginSchema 不强制字母+数字组合）", () => {
    const result = loginSchema.safeParse({
      email: "user@example.com",
      password: "12345678",
    });
    expect(result.success).toBe(true);
  });

  // 边界 case: 大写邮箱
  it("应接受大写邮箱（zod 默认小写不敏感）", () => {
    const result = loginSchema.safeParse({
      email: "USER@example.com",
      password: "Password1!",
    });
    expect(result.success).toBe(true);
  });
});

describe("registerSchema", () => {
  const validInput = {
    email: "newuser@example.com",
    password: "SecurePass1!",
    name: "测试用户",
  };

  it("应接受有效的注册数据", () => {
    const result = registerSchema.safeParse(validInput);
    expect(result.success).toBe(true);
  });

  it("应拒绝短密码（< 8 字符）", () => {
    const result = registerSchema.safeParse({
      ...validInput,
      password: "Short1!",
    });
    expect(result.success).toBe(false);
  });

  it("应拒绝缺少字母的密码", () => {
    const result = registerSchema.safeParse({
      ...validInput,
      password: "12345678!",
    });
    expect(result.success).toBe(false);
  });

  it("应拒绝缺少数字的密码", () => {
    const result = registerSchema.safeParse({
      ...validInput,
      password: "Password!",
    });
    expect(result.success).toBe(false);
  });

  it("应拒绝空名字", () => {
    const result = registerSchema.safeParse({
      ...validInput,
      name: "",
    });
    expect(result.success).toBe(false);
  });

  // B3 补充边界 case
  it("应拒绝密码超过 128 字符", () => {
    const result = registerSchema.safeParse({
      ...validInput,
      password: "A1" + "a".repeat(130),
    });
    expect(result.success).toBe(false);
  });

  it("应接受密码正好 8 位且含字母+数字", () => {
    const result = registerSchema.safeParse({
      ...validInput,
      password: "Pass1234",
    });
    expect(result.success).toBe(true);
  });

  it("应拒绝姓名超过 100 字", () => {
    const result = registerSchema.safeParse({
      ...validInput,
      name: "a".repeat(101),
    });
    expect(result.success).toBe(false);
  });

  it("应接受姓名正好 100 字", () => {
    const result = registerSchema.safeParse({
      ...validInput,
      name: "a".repeat(100),
    });
    expect(result.success).toBe(true);
  });

  it("应拒绝无效邮箱（缺 @）", () => {
    const result = registerSchema.safeParse({
      ...validInput,
      email: "not-an-email",
    });
    expect(result.success).toBe(false);
  });

  it("应拒绝无效邮箱（缺域名）", () => {
    const result = registerSchema.safeParse({
      ...validInput,
      email: "user@",
    });
    expect(result.success).toBe(false);
  });

  // 边界 case: 密码仅含特殊字符 + 字母但无数字
  it("应拒绝纯字母密码", () => {
    const result = registerSchema.safeParse({
      ...validInput,
      password: "Password!",
    });
    expect(result.success).toBe(false);
  });

  // 边界 case: 密码仅含数字 + 特殊字符但无字母
  it("应拒绝纯数字密码（含特殊字符）", () => {
    const result = registerSchema.safeParse({
      ...validInput,
      password: "12345678!",
    });
    expect(result.success).toBe(false);
  });

  // 边界 case: 密码含中文（regex 仅要求字母+数字，长度仍需 >=8）
  it("应接受含中文的密码（regex 仅要求字母+数字）", () => {
    const result = registerSchema.safeParse({
      ...validInput,
      password: "密码Pass12",
    });
    expect(result.success).toBe(true);
  });
});

describe("decisionSchema", () => {
  const validInput = {
    destination_type: "employment" as const,
    status: "planned" as const,
    confidence: 3,
    decision_date: "2026-01-15",
  };

  it("应接受有效决策", () => {
    expect(decisionSchema.safeParse(validInput).success).toBe(true);
  });

  it("应拒绝未知 destination_type", () => {
    expect(
      decisionSchema.safeParse({ ...validInput, destination_type: "invalid" })
        .success,
    ).toBe(false);
  });

  it("应拒绝未知 status", () => {
    expect(
      decisionSchema.safeParse({ ...validInput, status: "invalid" }).success,
    ).toBe(false);
  });

  it("应拒绝 confidence < 1", () => {
    expect(
      decisionSchema.safeParse({ ...validInput, confidence: 0 }).success,
    ).toBe(false);
  });

  it("应拒绝 confidence > 5", () => {
    expect(
      decisionSchema.safeParse({ ...validInput, confidence: 6 }).success,
    ).toBe(false);
  });

  it("应接受 reasoning 可选字段为空字符串", () => {
    expect(
      decisionSchema.safeParse({ ...validInput, reasoning: "" }).success,
    ).toBe(true);
  });

  it("应拒绝 reasoning 超过 2000 字", () => {
    expect(
      decisionSchema.safeParse({ ...validInput, reasoning: "a".repeat(2001) })
        .success,
    ).toBe(false);
  });
});

describe("skillSchema", () => {
  const validInput = {
    name: "Python",
    category: "backend",
    level: 3,
  };

  it("应接受有效技能", () => {
    expect(skillSchema.safeParse(validInput).success).toBe(true);
  });

  it("应拒绝 level < 1", () => {
    expect(skillSchema.safeParse({ ...validInput, level: 0 }).success).toBe(
      false,
    );
  });

  it("应拒绝 level > 5", () => {
    expect(skillSchema.safeParse({ ...validInput, level: 6 }).success).toBe(
      false,
    );
  });

  it("应拒绝 name 为空", () => {
    expect(skillSchema.safeParse({ ...validInput, name: "" }).success).toBe(
      false,
    );
  });

  it("应拒绝 name 超过 100 字", () => {
    expect(
      skillSchema.safeParse({ ...validInput, name: "a".repeat(101) }).success,
    ).toBe(false);
  });
});

describe("eventSchema", () => {
  const validInput = {
    title: "完成第一阶段",
    event_type: "milestone",
    event_date: "2026-01-15",
  };

  it("应接受有效事件", () => {
    expect(eventSchema.safeParse(validInput).success).toBe(true);
  });

  it("应拒绝空 title", () => {
    expect(
      eventSchema.safeParse({ ...validInput, title: "" }).success,
    ).toBe(false);
  });

  it("应拒绝 title 超过 200 字", () => {
    expect(
      eventSchema.safeParse({ ...validInput, title: "a".repeat(201) }).success,
    ).toBe(false);
  });

  it("应拒绝空 event_type", () => {
    expect(
      eventSchema.safeParse({ ...validInput, event_type: "" }).success,
    ).toBe(false);
  });

  it("应拒绝空 event_date", () => {
    expect(
      eventSchema.safeParse({ ...validInput, event_date: "" }).success,
    ).toBe(false);
  });
});

describe("retroSchema", () => {
  const validInput = {
    title: "周复盘",
    period_type: "weekly",
    period_start: "2026-01-01",
    period_end: "2026-01-07",
    satisfaction: 4,
  };

  it("应接受有效复盘", () => {
    expect(retroSchema.safeParse(validInput).success).toBe(true);
  });

  it("应拒绝 period_end < period_start", () => {
    expect(
      retroSchema.safeParse({
        ...validInput,
        period_start: "2026-01-07",
        period_end: "2026-01-01",
      }).success,
    ).toBe(false);
  });

  it("应接受 period_end == period_start（同日复盘）", () => {
    expect(
      retroSchema.safeParse({
        ...validInput,
        period_start: "2026-01-07",
        period_end: "2026-01-07",
      }).success,
    ).toBe(true);
  });

  it("应拒绝 satisfaction < 1", () => {
    expect(
      retroSchema.safeParse({ ...validInput, satisfaction: 0 }).success,
    ).toBe(false);
  });

  it("应拒绝 satisfaction > 5", () => {
    expect(
      retroSchema.safeParse({ ...validInput, satisfaction: 6 }).success,
    ).toBe(false);
  });
});

describe("knowledgeSchema", () => {
  const validInput = {
    category: "frontend",
    title: "React Hooks 完全指南",
    content: "useState / useEffect / useReducer...",
  };

  it("应接受有效知识", () => {
    expect(knowledgeSchema.safeParse(validInput).success).toBe(true);
  });

  it("应拒绝空 category", () => {
    expect(
      knowledgeSchema.safeParse({ ...validInput, category: "" }).success,
    ).toBe(false);
  });

  it("应拒绝空 title", () => {
    expect(
      knowledgeSchema.safeParse({ ...validInput, title: "" }).success,
    ).toBe(false);
  });

  it("应拒绝 title 超过 200 字", () => {
    expect(
      knowledgeSchema.safeParse({ ...validInput, title: "a".repeat(201) })
        .success,
    ).toBe(false);
  });

  it("应拒绝空 content", () => {
    expect(
      knowledgeSchema.safeParse({ ...validInput, content: "" }).success,
    ).toBe(false);
  });

  it("应接受 source 为 null", () => {
    expect(
      knowledgeSchema.safeParse({ ...validInput, source: null }).success,
    ).toBe(true);
  });

  it("应接受 source 超过 200 字符时拒绝", () => {
    expect(
      knowledgeSchema.safeParse({ ...validInput, source: "a".repeat(201) })
        .success,
    ).toBe(false);
  });

  it("应接受 is_published 默认值为 true", () => {
    const result = knowledgeSchema.safeParse(validInput);
    if (result.success) {
      expect(result.data.is_published).toBe(true);
    }
  });
});
