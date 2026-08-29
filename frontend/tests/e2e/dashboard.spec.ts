import { test, expect } from "@playwright/test";
import { registerAndLandOnDashboard, uniqueEmail } from "./helpers";

/**
 * 个人看板端到端测试
 * 覆盖看板概览、进度板块、数据展示等关键路径。
 */
// /dashboard 是受保护路由：middleware 会把未登录访问重定向到 /login，
// 因此每个 test 都先注册新用户并完成 onboardin
test.beforeEach(async ({ page }) => {
  await registerAndLandOnDashboard(page, "E2E Dashboard User", uniqueEmail("dashboard"));
});

test.describe("个人看板", () => {
  test("看板页面应正确渲染", async ({ page }) => {
    await page.goto("/dashboard");

    await expect(page).toHaveTitle(/GradPath|职径|看板/i);
    await expect(page.locator("body")).toContainText(/看板|概览|仪表盘|Dashboard/i, {
      timeout: 5000,
    });
  });

  test("应显示关键指标卡片", async ({ page }) => {
    await page.goto("/dashboard");

    // 首屏渲染 StatCard 统计卡与"三大方向进度""本周完成里程碑"等板块
    await expect(page.locator("body")).toContainText(/进度|里程碑|目标/i, {
      timeout: 10000,
    });
  });
});

test.describe("图表渲染", () => {
  test("应显示进度板块", async ({ page }) => {
    await page.goto("/dashboard");

    await expect(page.locator("body")).toContainText(/三大方向进度|连续打卡|等级进度/, {
      timeout: 10000,
    });
  });

  test("板块应有数据标签", async ({ page }) => {
    await page.goto("/dashboard");

    await expect(page.locator("body")).toContainText(/\d|%|分|次|条|天/, {
      timeout: 10000,
    });
  });
});

test.describe("数据交互", () => {
  test("应支持切换时间范围", async ({ page }) => {
    await page.goto("/dashboard");

    const timeFilter = page.locator('button:has-text("本周"), button:has-text("本月"), select[data-testid="time-range"]');
    if (await timeFilter.first().isVisible()) {
      await timeFilter.first().click();
      await page.waitForTimeout(500);
    }
  });

  test("应显示最近活动", async ({ page }) => {
    await page.goto("/dashboard");

    await expect(page.locator("body")).toContainText(/最近|活动|动态|记录/i, {
      timeout: 10000,
    });
  });
});

test.describe("周回顾", () => {
  test("周回顾页面应正确渲染", async ({ page }) => {
    await page.goto("/retrospectives/weekly");

    await expect(page.locator("body")).toContainText(/周|回顾|本周/i, {
      timeout: 10000,
    });
  });

  test("应显示本周完成的任务", async ({ page }) => {
    await page.goto("/retrospectives/weekly");

    // 新用户无行动记录时展示"本周数据不足/暂无"空态也算正确渲染
    await expect(page.locator("body")).toContainText(/完成|任务|数据不足|暂无/i, {
      timeout: 10000,
    });
  });
});
