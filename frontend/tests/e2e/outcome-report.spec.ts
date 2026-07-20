import { test, expect } from "@playwright/test";

/**
 * 上岸报告完整流端到端测试
 *
 * 覆盖登录 → /outcome-report → 选择上岸类型 → 填写关键信息 → 提交
 * → 验证报告页面显示 → 验证"分享到社区"按钮可点击 的关键路径。
 */
test.describe("上岸报告完整流", () => {
  test.setTimeout(30000);

  const TEST_EMAIL = `e2e-outcome-${Date.now()}-${Math.floor(Math.random() * 10000)}@test.com`;
  const TARGET_SCHOOL = "北京大学";
  const TARGET_MAJOR = "计算机科学";
  const ACTUAL_SCHOOL = "清华大学";
  const ACTUAL_MAJOR = "软件工程";

  test.beforeEach(async ({ page }) => {
    // ===== Mock 上岸报告提交 =====
    let savedReport: Record<string, unknown> | null = null;
    await page.route("**/api/outcome-report/submit", async (route) => {
      const body = route.request().postDataJSON() as Record<string, unknown>;
      savedReport = {
        id: `mock-outcome-${Date.now()}`,
        user_id: "mock-user",
        outcome_type: body?.outcome_type ?? "grad_civil_career",
        target_school: body?.target_school ?? TARGET_SCHOOL,
        target_major: body?.target_major ?? TARGET_MAJOR,
        actual_school: body?.actual_school ?? ACTUAL_SCHOOL,
        actual_major: body?.actual_major ?? ACTUAL_MAJOR,
        score_total: body?.score_total ?? 380,
        admission_path: body?.admission_path ?? "normal",
        year: body?.year ?? 2025,
        is_public: body?.is_public ?? "private",
        created_at: new Date().toISOString(),
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(savedReport),
      });
    });

    // ===== Mock 我的报告列表 =====
    await page.route("**/api/outcome-report/mine", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: savedReport ? [savedReport] : [],
          total: savedReport ? 1 : 0,
        }),
      });
    });

    // 注册并跳过 onboarding
    await page.goto("/register");
    await page.fill('input[name="name"]', "E2E Outcome User");
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', "Test1234!");
    await page.check('input[name="agree_terms"]');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/(onboarding|dashboard)/, { timeout: 15000 });
    const url = page.url();
    if (url.includes("/onboarding")) {
      await page.locator('[data-testid="onboarding-skip-button"]').click();
      await page.waitForURL("**/dashboard**", { timeout: 15000 });
    }
  });

  test("上岸报告页面应正确渲染", async ({ page }) => {
    await page.goto("/outcome-report");

    await expect(page.locator("h1")).toContainText(/上岸报告/i, { timeout: 10000 });
    await expect(page.locator('[data-testid="generate-button"]')).toBeVisible();
    await expect(page.locator('[data-testid="outcome-type-select"]')).toBeVisible();
  });

  test("完整提交流程：选择类型 → 填写信息 → 提交 → 验证报告显示", async ({ page }) => {
    await page.goto("/outcome-report");

    // 选择上岸类型（grad_civil_career: 上岸）
    await page.locator('[data-testid="outcome-type-select"]').selectOption("grad_civil_career");

    // 考试年份默认为当前年份，无需修改

    // 填写目标院校与专业
    await page.locator('[data-testid="target-school-input"]').fill(TARGET_SCHOOL);
    await page.locator('[data-testid="target-major-input"]').fill(TARGET_MAJOR);

    // 填写实际录取院校与专业
    await page.locator('[data-testid="actual-school-input"]').fill(ACTUAL_SCHOOL);
    await page.locator('[data-testid="actual-major-input"]').fill(ACTUAL_MAJOR);

    // 点击提交
    await page.locator('[data-testid="generate-button"]').click();

    // 验证"我的报告"区域出现刚提交的报告
    await expect(page.locator("body")).toContainText(TARGET_SCHOOL, { timeout: 10000 });
    await expect(page.locator("body")).toContainText(ACTUAL_SCHOOL);

    // 验证"分享到社区"按钮可点击
    const shareButton = page.locator('[data-testid="share-button"]').first();
    await expect(shareButton).toBeVisible();
    await expect(shareButton).toBeEnabled();

    // 点击分享按钮（触发 toast 即可，不验证实际分享逻辑）
    await shareButton.click();
  });

  test("切换上岸类型为未上岸应正常工作", async ({ page }) => {
    await page.goto("/outcome-report");

    // 切换为"未上岸"
    await page.locator('[data-testid="outcome-type-select"]').selectOption("failed");

    // 填写必要字段并提交
    await page.locator('[data-testid="target-school-input"]').fill("某高校");
    await page.locator('[data-testid="target-major-input"]').fill("某专业");
    await page.locator('[data-testid="generate-button"]').click();

    // 验证提交成功（报告区域出现）
    await expect(page.locator("body")).toContainText(/未上岸|某高校/i, { timeout: 10000 });
  });
});
