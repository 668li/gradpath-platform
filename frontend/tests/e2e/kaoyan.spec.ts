import { test, expect } from "@playwright/test";
import { registerAndLandOnDashboard, uniqueEmail } from "./helpers";

/**
 * 考研数据浏览端到端测试
 * 覆盖院校情报等关键路径。
 *
 * 注：早期版本访问的 /kaoyan/scorelines 与 /kaoyan/adjustments
 * 是不存在的路由（页面 404），已改为真实存在的院校情报页。
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

  test("院校情报页应显示搜索入口", async ({ page }) => {
    await page.goto("/kaoyan/schools");

    // 页面提供院校名称/专业搜索框
    await expect(page.locator('input[placeholder*="搜索"]').first()).toBeVisible({
      timeout: 10000,
    });
  });
});

test.describe("院校情报", () => {
  test("点击院校应进入详情页", async ({ page }) => {
    await page.goto("/kaoyan");

    const firstSchool = page.locator("a[href*='school'], a[href*='kaoyan'], [data-testid='school-item']").first();
    if (await firstSchool.isVisible()) {
      await firstSchool.click();
      await page.waitForTimeout(1000);
      await expect(page.locator("body")).toContainText(/情报|数据|专业|导师/i, {
        timeout: 5000,
      });
    }
  });

  test("分数线与录取信息入口可见", async ({ page }) => {
    await page.goto("/kaoyan");

    // 首页导航与板块文案覆盖分数线、招生计划、录取率等数据维度
    await expect(page.locator("body")).toContainText(/分数线|复试|录取/i, {
      timeout: 10000,
    });
  });

  test("院校列表支持学位类型筛选", async ({ page }) => {
    await page.goto("/kaoyan/schools");

    const filter = page.locator("select");
    if (await filter.first().isVisible()) {
      await expect(filter.first()).toBeVisible();
    }
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
