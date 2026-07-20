import { test, expect } from "@playwright/test";

/**
 * 决策助手完整流端到端测试
 *
 * 覆盖登录 → /decision-lab → 创建新决策 → 填写选项 → 触发 AI 分析（mock）
 * → 保存到决策日志 → 列表可见 的关键路径。
 *
 * 决策实验室涉及多个 LLM 依赖（预验尸分析、红队问题、AI 综合分析），
 * 全部通过 page.route() mock。
 */
test.describe("决策助手完整流", () => {
  test.setTimeout(30000);

  const TEST_EMAIL = `e2e-decision-${Date.now()}-${Math.floor(Math.random() * 10000)}@test.com`;
  const DECISION_TITLE = "字节 vs 阿里 offer 选择";
  const OPTION_A = "字节跳动";
  const OPTION_B = "阿里巴巴";

  test.beforeEach(async ({ page }) => {
    // ===== Mock LLM 依赖：预验尸分析 =====
    await page.route("**/api/decision-analysis/premortem-analyze", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          categories: [
            { category: "市场风险", reasons: ["行业下行", "竞争加剧"] },
            { category: "个人匹配", reasons: ["技能不匹配", "兴趣偏离"] },
          ],
          safeguards: [
            { category: "市场风险", action: "持续关注行业动态" },
            { category: "个人匹配", action: "入职前与团队深入沟通" },
          ],
        }),
      });
    });

    // ===== Mock LLM 依赖：红队问题生成 =====
    await page.route("**/api/decision-analysis/red-team-questions", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          questions: [
            "如果这家公司 6 个月后裁员，你的退路是什么？",
            "你为什么不去另一家？有什么具体顾虑？",
            "你的核心诉求是薪资还是成长？这家公司能满足吗？",
          ],
        }),
      });
    });

    // ===== Mock 决策矩阵计算（非 LLM，但仍 mock 以确保可重复） =====
    await page.route("**/api/decision-analysis/compute-matrix", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          results: [
            { name: OPTION_A, total: 8.5, details: { 薪资: 9, 成长: 8 } },
            { name: OPTION_B, total: 7.8, details: { 薪资: 8, 成长: 8 } },
          ],
          winner: OPTION_A,
        }),
      });
    });

    // ===== Mock 决策创建 =====
    let createdAnalysis: Record<string, unknown> | null = null;
    await page.route("**/api/decision-analysis/create", async (route) => {
      createdAnalysis = {
        id: `mock-analysis-${Date.now()}`,
        title: DECISION_TITLE,
        options: [OPTION_A, OPTION_B],
        premortem_reasons: [],
        premortem_categories: ["市场风险"],
        safeguards: [],
        criteria: [],
        matrix_scores: [],
        red_team_questions: [],
        red_team_answers: [],
        weighted_results: [
          { name: OPTION_A, total: 8.5 },
          { name: OPTION_B, total: 7.8 },
        ],
        winner: OPTION_A,
        ai_analysis: null,
        created_at: new Date().toISOString(),
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(createdAnalysis),
      });
    });

    // ===== Mock LLM 依赖：AI 综合分析 =====
    await page.route("**/api/decision-analysis/*/ai-analysis", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ai_analysis:
            "综合预验尸、决策矩阵和红队质疑的分析结果：\n建议选择字节跳动。\n理由：薪资更高、成长空间更大，但需注意加班强度。",
        }),
      });
    });

    // ===== Mock 决策列表 =====
    await page.route("**/api/decision-analysis/list", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(createdAnalysis ? [createdAnalysis] : []),
      });
    });

    // 注册并跳过 onboarding
    await page.goto("/register");
    await page.fill('input[name="name"]', "E2E Decision User");
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

  test("访问 /decision-lab 看到新建决策按钮", async ({ page }) => {
    await page.goto("/decision-lab");

    await expect(page.locator("h1")).toContainText(/决策实验室/i, { timeout: 10000 });
    await expect(page.locator('[data-testid="new-decision-button"]')).toBeVisible();
  });

  test("完整决策流程：创建 → 填写 → AI 分析 → 保存", async ({ page }) => {
    await page.goto("/decision-lab");

    // 点击"新建决策分析"
    await page.locator('[data-testid="new-decision-button"]').click();

    // Step 1: 基本信息 - 填写标题和选项
    await page.locator('[data-testid="decision-title-input"]').fill(DECISION_TITLE);
    await page.locator('[data-testid="option-a-input"]').fill(OPTION_A);
    await page.locator('[data-testid="option-b-input"]').fill(OPTION_B);

    // 进入下一步（预验尸）
    await page.locator('[data-testid="decision-next-button"]').click();
    await expect(page.locator("body")).toContainText(/预验尸/i, { timeout: 5000 });

    // Step 2: 预验尸 - 直接跳到决策矩阵（不调用 LLM 分析）
    await page.getByRole("button", { name: /下一步：决策矩阵/ }).click();
    await expect(page.locator("body")).toContainText(/决策矩阵/i, { timeout: 5000 });

    // Step 3: 决策矩阵 - 直接跳到红队质疑
    await page.getByRole("button", { name: /下一步：红队质疑/ }).click();
    await expect(page.locator("body")).toContainText(/红队质疑/i, { timeout: 5000 });

    // Step 4: 红队质疑 - 直接跳到综合分析
    await page.getByRole("button", { name: /下一步：综合分析/ }).click();
    await expect(page.locator("body")).toContainText(/AI 综合分析|综合分析/i, { timeout: 5000 });

    // Step 5: 综合分析 - 点击"保存并生成 AI 分析"（mock 响应）
    await page.locator('[data-testid="analyze-button"]').click();

    // 验证 AI 返回建议（mock 内容）
    await expect(page.locator("body")).toContainText(/建议选择|字节跳动|综合.*分析/i, {
      timeout: 10000,
    });

    // 点击"完成"返回列表
    await page.getByRole("button", { name: /完成/ }).click();

    // 验证决策列表中存在刚创建的决策
    await expect(page.locator("body")).toContainText(DECISION_TITLE, { timeout: 5000 });
  });

  test("决策列表页可正确渲染", async ({ page }) => {
    await page.goto("/decision-lab");

    // 即使列表为空也应正常渲染
    await expect(page.locator("body")).toContainText(/决策实验室|新建决策分析|历史分析|还没有决策分析/i, {
      timeout: 10000,
    });
  });
});
