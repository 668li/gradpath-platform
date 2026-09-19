import { test, expect } from "@playwright/test";
import { registerAndLandOnDashboard, uniqueEmail } from "./helpers";

/**
 * 公司情报查询完整流端到端测试
 *
 * ⚠️ 2026-09-19 复测状态（方向席位 E2E 全量实测后改写）：
 * 本 spec 原覆盖的 UI 面已全部不存在——
 *   1. /war-room 已被 next.config.js 302 到 /decision-center（信息架构重构 a5b731d），
 *      "作战室/career tab/公司列表" UI 只剩 war-room/page.tsx 孤儿文件，URL 不可达；
 *   2. /employment 已重建为"就业中心·面经库"，公司情报列表不再展示；
 *   3. 后端 /api/career-intel/* 仍存活。
 * 产品需拍板：恢复公司情报 UI 入口（迁到何处）、或连孤儿 war-room/page.tsx 一起删。
 * 拍板前原三个用例转 test.fixme（暂停不红），保留一条重定向真值测试守护现状。
 */
test.describe("公司情报查询完整流", () => {
  test.setTimeout(30000);

  test.beforeEach(async ({ page }) => {
    // 注册新用户并完成 onboarding（每个 test 独立邮箱，避免 409）
    await registerAndLandOnDashboard(page, "E2E Intel User", uniqueEmail("intel"));
  });

  test("/war-room 现状：302 重定向到决策中心", async ({ page }) => {
    await page.goto("/war-room");

    // 信息架构重构后的真值：war-room 不再作为独立页面存在
    await expect(page).toHaveURL(/\/decision-center/, { timeout: 15000 });
    await expect(page.locator("h1")).toContainText(/决策中心/i, { timeout: 10000 });
  });

  test.fixme("访问 war-room 并切换到 career tab 查看公司列表", async () => {
    // 原 UI（h1=作战室 + career-tab + company-input）随 302 变孤儿，恢复/迁移入口后启用
  });

  test.fixme("输入公司名筛选公司列表", async () => {
    // 同上：company-input 只存在于不可达的 war-room/page.tsx
  });

  test.fixme("保存情报后在 /employment 列表可见", async () => {
    // /employment 已重建为面经库，公司情报列表 UI 已移除；后端 /api/career-intel/* 仍在
  });
});
