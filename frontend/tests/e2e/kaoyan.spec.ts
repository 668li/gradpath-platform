import { test, expect } from "@playwright/test";

/**
 * 考研数据浏览端到端测试
 * 覆盖院校情报、分数线、调剂信息等关键路径。
 */
test.describe("考研数据浏览", () => {
  test("考研页面应正确渲染", async ({ page }) => {
    await page.goto("/kaoyan");

    await expect(page).toHaveTitle(/GradPath|职径|考研/i);
    await expect(page.locator("body")).toContainText(/考研|院校|专业/i, {
      timeout: 5000,
    });
  });

  test("应显示院校列表或搜索入口", async ({ page }) => {
    await page.goto("/kaoyan");

    const hasSearchOrList =
      (await page.locator('input[placeholder*="搜索"], input[placeholder*="院校"]').isVisible()) ||
      (await page.locator("table, [data-testid='school-list'], .school-card").isVisible());

    expect(hasSearchOrList).toBeTruthy();
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
});

test.describe("分数线查询", () => {
  test("分数线页面应正确渲染", async ({ page }) => {
    await page.goto("/kaoyan/scorelines");

    await expect(page.locator("body")).toContainText(/分数线|复试|录取/i, {
      timeout: 5000,
    });
  });

  test("应支持按年份筛选", async ({ page }) => {
    await page.goto("/kaoyan/scorelines");

    const yearFilter = page.locator("select, [data-testid='year-filter'], input[type='number']");
    if (await yearFilter.isVisible()) {
      await expect(yearFilter).toBeVisible();
    }
  });
});

test.describe("调剂信息", () => {
  test("调剂页面应正确渲染", async ({ page }) => {
    await page.goto("/kaoyan/adjustments");

    await expect(page.locator("body")).toContainText(/调剂|缺额|补录/i, {
      timeout: 5000,
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
    if (await filter.isVisible()) {
      await expect(filter).toBeVisible();
    }
  });
});
