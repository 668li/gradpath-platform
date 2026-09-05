// frontend/components/__tests__/role-match.test.ts
import { describe, it, expect } from "vitest";
import { applyIdentityBoost, topRoles, IDENTITY_BOOST } from "@/components/assessment/role-match";

const base = [
  { role: "软件工程师", match: 90 },
  { role: "数据分析师", match: 85 },
  { role: "考研科研", match: 70 },
  { role: "公务员", match: 68 },
  { role: "教师", match: 66 },
  { role: "产品经理", match: 60 },
];

describe("applyIdentityBoost", () => {
  it("目标方向含考研 → 升学/体制内角色 +15，其余不动", () => {
    const boosted = applyIdentityBoost(base, "考研");
    const byRole = Object.fromEntries(boosted.map((r) => [r.role, r.match]));
    expect(byRole["考研科研"]).toBe(70 + IDENTITY_BOOST);
    expect(byRole["公务员"]).toBe(68 + IDENTITY_BOOST);
    expect(byRole["教师"]).toBe(66 + IDENTITY_BOOST);
    expect(byRole["软件工程师"]).toBe(90);
  });

  it("目标方向含考公 → 同样加成", () => {
    const byRole = Object.fromEntries(
      applyIdentityBoost(base, "考公进体制").map((r) => [r.role, r.match]),
    );
    expect(byRole["公务员"]).toBe(83);
  });

  it("目标方向为就业或为空 → 不加成", () => {
    expect(applyIdentityBoost(base, "直接就业")).toEqual(base);
    expect(applyIdentityBoost(base, null)).toEqual(base);
    expect(applyIdentityBoost(base, undefined)).toEqual(base);
  });

  it("加成封顶 100", () => {
    const boosted = applyIdentityBoost([{ role: "公务员", match: 95 }], "考公");
    expect(boosted[0].match).toBe(100);
  });

  it("不改动入参数组", () => {
    applyIdentityBoost(base, "考研");
    expect(base[2].match).toBe(70);
  });
});

describe("topRoles", () => {
  it("考研用户 top5 不再被纯 IT 角色刷屏", () => {
    const top = topRoles(base, "考研").map((r) => r.role);
    expect(top).toEqual(["软件工程师", "数据分析师", "考研科研", "公务员", "教师"]);
  });

  it("无目标方向时保持纯匹配分排序", () => {
    const top = topRoles(base, null).map((r) => r.role);
    expect(top).toEqual(["软件工程师", "数据分析师", "考研科研", "公务员", "教师"]);
    expect(topRoles(base, null).length).toBe(5);
  });

  it("不排序入参、按 topN 截断", () => {
    const input = [
      { role: "A", match: 10 },
      { role: "B", match: 90 },
      { role: "C", match: 50 },
    ];
    expect(topRoles(input, null, 2).map((r) => r.role)).toEqual(["B", "C"]);
    expect(input[0].role).toBe("A");
  });
});
