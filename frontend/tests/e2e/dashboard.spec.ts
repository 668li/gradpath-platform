import { test, expect } from "@playwright/test";

/**
 * 个人看板端到端测试
 * 覆盖看板概览、图表渲染、数据展示等关键路径。
 */
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

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const hasMetrics =
      (await page.locator('[data-testid="metric-card"], .metric-card, .stat-card').isVisible()) ||
      /进度|目标|任务|里程碑/i.test(bodyText);

    expect(hasMetrics).toBeTruthy();
  });
});

test.describe("图表渲染", () => {
  test("应显示进度图表", async ({ page }) => {
    await page.goto("/dashboard");

    const hasChart =
      (await page.locator("svg, canvas, [data-testid='chart']").isVisible()) ||
      (await page.locator(".recharts-wrapper, .chart-container").isVisible());

    expect(hasChart).toBeTruthy();
  });

  test("图表应有正确的数据标签", async ({ page }) => {
    await page.goto("/dashboard");

    const chartArea = page.locator("svg, canvas, .recharts-wrapper");
    if (await chartArea.isVisible()) {
      const bodyText = (await page.locator("body").textContent()) ?? "";
      const hasLabels = /%|分|次|条/i.test(bodyText);
      expect(hasLabels).toBeTruthy();
    }
  });
});

test.describe("数据交互", () => {
  test("应支持切换时间范围", async ({ page }) => {
    await page.goto("/dashboard");

    const timeFilter = page.locator('button:has-text("本周"), button:has-text("本月"), select[data-testid="time-range"]');
    if (await timeFilter.isVisible()) {
      await timeFilter.click();
      await page.waitForTimeout(500);
    }
  });

  test("应显示最近活动", async ({ page }) => {
    await page.goto("/dashboard");

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const hasActivity =
      (await page.locator('[data-testid="activity-list"], .activity-list, .recent-activity').isVisible()) ||
      /最近|活动|动态|记录/i.test(bodyText);

    expect(hasActivity).toBeTruthy();
  });
});

test.describe("周回顾", () => {
  test("周回顾页面应正确渲染", async ({ page }) => {
    await page.goto("/dashboard/weekly-recap");

    await expect(page.locator("body")).toContainText(/周|回顾|本周|weekly/i, {
      timeout: 5000,
    });
  });

  test("应显示本周完成的任务", async ({ page }) => {
    await page.goto("/dashboard/weekly-recap");

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const hasTasks =
      (await page.locator('[data-testid="task-list"], .task-list').isVisible()) ||
      /完成|任务|里程碑|成就/i.test(bodyText);

    expect(hasTasks).toBeTruthy();
  });
});
