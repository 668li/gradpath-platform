import { test, expect } from "@playwright/test";

/**
 * 5 分钟诊断完整流端到端测试
 *
 * 覆盖注册 → onboarding 4 步诊断 → 进入 dashboard 的关键路径。
 * LLM 步骤（生成 AI 诊断报告）通过 page.route() mock，避免真实调用。
 */
test.describe("5 分钟诊断完整流", () => {
  test.setTimeout(30000);

  let uniqueEmail: string;

  test.beforeEach(async ({ page }) => {
    uniqueEmail = `e2e-onboard-${Date.now()}-${Math.floor(Math.random() * 10000)}@test.com`;

    // Mock LLM 依赖：生成 AI 诊断报告
    await page.route("**/api/onboarding/generate", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "mock-onboarding-id",
          user_id: "mock-user-id",
          current_stage: "junior",
          target_direction: "postgrad",
          target_industry: null,
          self_assessment: { skills: { technical: 4, communication: 3, leadership: 3, creativity: 4 } },
          ai_diagnosis: "这是一份 mock 的 AI 诊断报告：你的考研准备路径整体合理，建议加强真题训练。",
          key_insights: ["数学基础扎实", "英语需要加强"],
          recommended_path: ["暑期完成 10 套真题", "9 月开始模拟面试"],
          completed: true,
          created_at: new Date().toISOString(),
        }),
      });
    });

    // Mock onboarding save 接口（避免依赖后端真实写入）
    await page.route("**/api/onboarding", async (route) => {
      if (route.request().method() !== "POST") {
        return route.continue();
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "mock-onboarding-id",
          user_id: "mock-user-id",
          current_stage: "junior",
          target_direction: "postgrad",
          target_industry: null,
          self_assessment: { skills: { technical: 4, communication: 3, leadership: 3, creativity: 4 } },
          completed: false,
          created_at: new Date().toISOString(),
        }),
      });
    });

    // Mock onboarding skip
    await page.route("**/api/onboarding/skip", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "mock-onboarding-id",
          user_id: "mock-user-id",
          completed: true,
          created_at: new Date().toISOString(),
        }),
      });
    });

    // 注册新用户
    await page.goto("/register");
    await page.fill('input[name="name"]', "E2E Test User");
    await page.fill('input[type="email"]', uniqueEmail);
    await page.fill('input[type="password"]', "Test1234!");
    await page.check('input[name="agree_terms"]');
    await page.click('button[type="submit"]');

    // 注册成功后跳转到 onboarding（layout 检测到未完成会重定向）
    await page.waitForURL("**/onboarding**", { timeout: 15000 });
  });

  test("完成 5 分钟诊断并进入 dashboard", async ({ page }) => {
    // Step 1: 当前状态 - 选择"大三"
    await page.locator('[data-testid="status-student"]').click();
    await page.locator('[data-testid="onboarding-next-button"]').click();

    // Step 2: 目标方向 - 选择"考研"
    await page.locator('[data-testid="goal-kaoyan"]').click();
    await page.locator('[data-testid="onboarding-next-button"]').click();

    // Step 3: 目标行业（可选，直接下一步）
    await expect(page.locator("body")).toContainText(/目标行业/);
    await page.locator('[data-testid="onboarding-next-button"]').click();

    // Step 4: 自我评估（使用默认值，直接保存并生成）
    await expect(page.locator("body")).toContainText(/自我评估/);
    await page.locator('[data-testid="onboarding-next-button"]').click();

    // 进入生成页（step 4），点击"稍后再生成，先去个人看板"避免 LLM 调用
    await page.locator('[data-testid="onboarding-finish-button"]').click();

    // 验证跳转到 dashboard
    await page.waitForURL("**/dashboard**", { timeout: 15000 });
    await expect(page.locator("h1")).toContainText(/欢迎|Dashboard|看板|概览|仪表/i, { timeout: 10000 });
  });

  test("完成诊断并生成 AI 报告（mock）", async ({ page }) => {
    // Step 1: 已毕业
    await page.locator('[data-testid="status-graduated"]').click();
    await page.locator('[data-testid="onboarding-next-button"]').click();

    // Step 2: 就业方向
    await page.locator('[data-testid="goal-career"]').click();
    await page.locator('[data-testid="onboarding-next-button"]').click();

    // Step 3: 跳过行业选择
    await page.locator('[data-testid="onboarding-next-button"]').click();

    // Step 4: 保存
    await page.locator('[data-testid="onboarding-next-button"]').click();

    // 点击"生成 AI 诊断报告"（mock 响应）
    await page.locator('[data-testid="onboarding-generate-button"]').click();

    // 验证 AI 诊断结果页面渲染
    await expect(page.locator("body")).toContainText(/诊断完成|AI 诊断|关键洞察|推荐路径/i, {
      timeout: 10000,
    });

    // 点击"进入个人看板"
    await page.getByRole("button", { name: /进入个人看板/ }).click();
    await page.waitForURL("**/dashboard**", { timeout: 15000 });
  });

  test("跳过诊断直接进入 dashboard", async ({ page }) => {
    await page.locator('[data-testid="onboarding-skip-button"]').click();
    await page.waitForURL("**/dashboard**", { timeout: 15000 });
  });
});
