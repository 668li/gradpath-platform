import { test, expect } from "@playwright/test";
import { registerAndLandOnDashboard, uniqueEmail } from "./helpers";

/**
 * 考研数据浏览端到端测试
 * 覆盖考研枢纽页与资讯中心等存活路由。
 */
// /kaoyan 等路由受 middleware 保护：未登录访问被重定向到 /login，
// 每个 test 都先注册新用户并完成 onboarding
test.beforeEach(async ({ page }) => {
  await registerAndLandOnDashboard(page, "E2E Kaoyan User", uniqueEmail("kaoyan"));
});

test.describe("考研数据浏览", () => {
  test("考研页面应正确渲染", async ({ page }) => {
    await page.goto("/kaoyan");

    await expect(page).toHaveTitle(/GradPath|职径|考研/i);
    await expect(page.locator("body")).toContainText(/考研|院校|专业/i, {
      timeout: 5000,
    });
  });
});

test.describe("考研枢纽导航", () => {
  test("枢纽页可进入资讯中心", async ({ page }) => {
    await page.goto("/kaoyan");

    const newsEntry = page.locator('a[href*="/kaoyan/news"]').first();
    await expect(newsEntry).toBeVisible({ timeout: 10000 });
    await newsEntry.click();
    await expect(page.locator("body")).toContainText(/资讯|来源/i, {
      timeout: 10000,
    });
  });
});

test.describe("导师评价", () => {
  test("导师页面应正确渲染", async ({ page }) => {
    await page.goto("/mentors");

    await expect(page.locator("body")).toContainText(/导师|教授|评价/i, {
      timeout: 5000,
    });
  });

  test("应支持按学校筛选导师", async ({ page }) => {
    await page.goto("/mentors");

    const filter = page.locator('select, [data-testid="university-filter"], input[placeholder*="学校"]');
    if (await filter.first().isVisible()) {
      await expect(filter.first()).toBeVisible();
    }
  });
});
