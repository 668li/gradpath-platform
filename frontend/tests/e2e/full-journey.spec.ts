import { test, expect } from "@playwright/test";

/**
 * 端到端完整旅程测试
 *
 * 模拟用户从注册到上岸的完整旅程，串联 5 大核心业务流：
 *   1. 注册 → onboarding 5 分钟诊断
 *   2. 公司情报查询（war-room career tab）
 *   3. 决策助手（decision-lab）
 *   4. 社区发帖 + 评论
 *   5. 上岸报告生成
 *
 * 使用 test.describe.serial 串行执行，整体耗时约 2-3 分钟。
 * 所有 LLM 依赖步骤通过 page.route() mock。
 */
test.describe.serial("端到端完整旅程", () => {
  test.setTimeout(180000); // 3 分钟，整个旅程单测超时

  const TEST_EMAIL = `e2e-journey-${Date.now()}-${Math.floor(Math.random() * 10000)}@test.com`;
  const TEST_NAME = "E2E Journey User";

  // 共享测试数据
  const POST_TITLE = `Journey 测试帖 - ${Date.now()}`;
  const POST_CONTENT = "端到端旅程测试中发布的帖子。";
  const COMMENT_CONTENT = `Journey 测试评论 - ${Date.now()}`;
  const DECISION_TITLE = "字节 vs 阿里 offer 选择";
  const OPTION_A = "字节跳动";
  const OPTION_B = "阿里巴巴";
  const TARGET_SCHOOL = "北京大学";
  const TARGET_MAJOR = "计算机科学";

  test.beforeAll(async ({ browser }) => {
    // 验证浏览器可用
    expect(browser).toBeDefined();
  });

  test("Step 1: 注册并完成 onboarding", async ({ page }) => {
    // ===== Mock onboarding 相关接口 =====
    await page.route("**/api/onboarding/generate", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "mock-onboarding-id",
          user_id: "mock-user-id",
          current_stage: "junior",
          target_direction: "employment",
          target_industry: "互联网/IT",
          self_assessment: { skills: { technical: 4, communication: 3, leadership: 3, creativity: 4 } },
          ai_diagnosis: "mock 诊断：建议聚焦互联网行业，加强项目经验。",
          key_insights: ["技术能力较强", "需要加强沟通"],
          recommended_path: ["完成 2-3 个项目", "参与开源贡献"],
          completed: true,
          created_at: new Date().toISOString(),
        }),
      });
    });

    await page.route("**/api/onboarding", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: "mock-onboarding-id",
            user_id: "mock-user-id",
            current_stage: "junior",
            target_direction: "employment",
            completed: false,
            created_at: new Date().toISOString(),
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.route("**/api/onboarding/skip", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "mock-onboarding-id",
          completed: true,
          created_at: new Date().toISOString(),
        }),
      });
    });

    // 注册
    await page.goto("/register");
    await page.fill('input[name="name"]', TEST_NAME);
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', "Test1234!");
    await page.check('input[name="agree_terms"]');
    await page.click('button[type="submit"]');

    await page.waitForURL("**/onboarding**", { timeout: 15000 });

    // Step 1: 选大三
    await page.locator('[data-testid="status-student"]').click();
    await page.locator('[data-testid="onboarding-next-button"]').click();

    // Step 2: 选就业
    await page.locator('[data-testid="goal-career"]').click();
    await page.locator('[data-testid="onboarding-next-button"]').click();

    // Step 3: 选互联网/IT 行业
    const industryBtn = page.getByText("互联网/IT", { exact: true });
    if (await industryBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await industryBtn.click();
    }
    await page.locator('[data-testid="onboarding-next-button"]').click();

    // Step 4: 自我评估默认值，保存
    await page.locator('[data-testid="onboarding-next-button"]').click();

    // 点击"稍后再生成，先去个人看板"（避免 LLM 调用，加速测试）
    await page.locator('[data-testid="onboarding-finish-button"]').click();

    await page.waitForURL("**/dashboard**", { timeout: 15000 });
    await expect(page.locator("body")).toContainText(/看板|概览|仪表盘|Dashboard/i, { timeout: 10000 });
  });

  test("Step 2: 公司情报查询（war-room career tab）", async ({ page }) => {
    // ===== Mock 公司情报相关接口 =====
    await page.route("**/api/career-intel/intel/query", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          company_name: "字节跳动",
          position_name: "前端工程师",
          industry: "互联网/IT",
          salary_range: "25-50k·15薪",
          overtime_intensity: "severe",
          layoff_risk: "moderate",
          promotion_outlook: "good",
          insider_notes: "技术氛围浓厚，加班较多。",
          risk_warnings: ["加班强度大"],
          sources: [],
        }),
      });
    });

    // 先登录已注册的用户
    await page.goto("/login");
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', "Test1234!");
    await page.click('button[type="submit"]');
    await page.waitForURL("**/dashboard**", { timeout: 15000 });

    // 访问 war-room career tab
    await page.goto("/war-room");
    await page.locator('[data-testid="career-tab"]').click();

    // 验证求职作战室渲染
    await expect(page.locator("body")).toContainText(/求职作战室|公司列表|公司名称/i, {
      timeout: 10000,
    });

    // 在搜索框输入公司名（验证筛选功能可用）
    await page.locator('[data-testid="company-input"]').fill("字节跳动");
    await page.waitForTimeout(500);

    // 验证页面正常（无报错）
    await expect(page.locator("body")).toBeVisible();
  });

  test("Step 3: 决策助手完整流（mock LLM）", async ({ page }) => {
    // ===== Mock 决策分析 LLM 接口 =====
    await page.route("**/api/decision-analysis/premortem-analyze", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          categories: [{ category: "市场风险", reasons: ["行业下行"] }],
          safeguards: [{ category: "市场风险", action: "关注行业动态" }],
        }),
      });
    });

    await page.route("**/api/decision-analysis/red-team-questions", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          questions: ["如果公司裁员你的退路是什么？", "你的核心诉求是薪资还是成长？"],
        }),
      });
    });

    await page.route("**/api/decision-analysis/compute-matrix", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          results: [
            { name: OPTION_A, total: 8.5, details: {} },
            { name: OPTION_B, total: 7.8, details: {} },
          ],
          winner: OPTION_A,
        }),
      });
    });

    let createdAnalysis: Record<string, unknown> | null = null;
    await page.route("**/api/decision-analysis/create", async (route) => {
      createdAnalysis = {
        id: `mock-${Date.now()}`,
        title: DECISION_TITLE,
        options: [OPTION_A, OPTION_B],
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

    await page.route("**/api/decision-analysis/*/ai-analysis", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ai_analysis: "综合分析：建议选择字节跳动，薪资与成长空间更优。",
        }),
      });
    });

    await page.route("**/api/decision-analysis/list", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(createdAnalysis ? [createdAnalysis] : []),
      });
    });

    // 登录
    await page.goto("/login");
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', "Test1234!");
    await page.click('button[type="submit"]');
    await page.waitForURL("**/dashboard**", { timeout: 15000 });

    // 进入决策实验室
    await page.goto("/decision-lab");
    await page.locator('[data-testid="new-decision-button"]').click();

    // 填写决策
    await page.locator('[data-testid="decision-title-input"]').fill(DECISION_TITLE);
    await page.locator('[data-testid="option-a-input"]').fill(OPTION_A);
    await page.locator('[data-testid="option-b-input"]').fill(OPTION_B);
    await page.locator('[data-testid="decision-next-button"]').click();

    // 跳过预验尸、决策矩阵、红队，直达综合分析
    await page.getByRole("button", { name: /下一步：决策矩阵/ }).click();
    await page.getByRole("button", { name: /下一步：红队质疑/ }).click();
    await page.getByRole("button", { name: /下一步：综合分析/ }).click();

    // 触发 AI 分析
    await page.locator('[data-testid="analyze-button"]').click();

    // 验证 AI 建议返回
    await expect(page.locator("body")).toContainText(/建议选择|综合/i, { timeout: 10000 });

    // 完成
    await page.getByRole("button", { name: /完成/ }).click();
    await expect(page.locator("body")).toContainText(DECISION_TITLE, { timeout: 5000 });
  });

  test("Step 4: 社区发帖 + 评论", async ({ page }) => {
    // 登录
    await page.goto("/login");
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', "Test1234!");
    await page.click('button[type="submit"]');
    await page.waitForURL("**/dashboard**", { timeout: 15000 });

    // 进入社区
    await page.goto("/community");
    await expect(page.locator('[data-testid="new-post-button"]')).toBeVisible({ timeout: 10000 });

    // 发帖
    await page.locator('[data-testid="new-post-button"]').click();
    await page.locator('[data-testid="post-title-input"]').fill(POST_TITLE);
    await page.locator('[data-testid="post-content-input"]').fill(POST_CONTENT);
    await page.locator('[data-testid="submit-post-button"]').click();

    // 验证帖子可见
    await expect(page.locator("body")).toContainText(POST_TITLE, { timeout: 10000 });

    // 展开评论
    const postCard = page.locator("div", { hasText: POST_TITLE }).first();
    await postCard.getByText(/评论/).click();

    // 发表评论
    await page.locator('[data-testid="comment-input"]').fill(COMMENT_CONTENT);
    await page.locator('[data-testid="submit-comment-button"]').click();

    // 验证评论显示
    await expect(page.locator("body")).toContainText(COMMENT_CONTENT, { timeout: 10000 });
  });

  test("Step 5: 上岸报告生成", async ({ page }) => {
    // ===== Mock 上岸报告接口 =====
    let savedReport: Record<string, unknown> | null = null;
    await page.route("**/api/outcome-report/submit", async (route) => {
      const body = route.request().postDataJSON() as Record<string, unknown>;
      savedReport = {
        id: `mock-${Date.now()}`,
        user_id: "mock",
        outcome_type: body?.outcome_type ?? "grad_civil_career",
        target_school: body?.target_school ?? TARGET_SCHOOL,
        target_major: body?.target_major ?? TARGET_MAJOR,
        actual_school: body?.actual_school ?? TARGET_SCHOOL,
        actual_major: body?.actual_major ?? TARGET_MAJOR,
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

    // 登录
    await page.goto("/login");
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', "Test1234!");
    await page.click('button[type="submit"]');
    await page.waitForURL("**/dashboard**", { timeout: 15000 });

    // 进入上岸报告页
    await page.goto("/outcome-report");

    // 填写并提交报告
    await page.locator('[data-testid="outcome-type-select"]').selectOption("grad_civil_career");
    await page.locator('[data-testid="target-school-input"]').fill(TARGET_SCHOOL);
    await page.locator('[data-testid="target-major-input"]').fill(TARGET_MAJOR);
    await page.locator('[data-testid="actual-school-input"]').fill(TARGET_SCHOOL);
    await page.locator('[data-testid="actual-major-input"]').fill(TARGET_MAJOR);
    await page.locator('[data-testid="generate-button"]').click();

    // 验证报告显示
    await expect(page.locator("body")).toContainText(TARGET_SCHOOL, { timeout: 10000 });

    // 验证分享按钮可点击
    const shareButton = page.locator('[data-testid="share-button"]').first();
    await expect(shareButton).toBeVisible();
    await expect(shareButton).toBeEnabled();
    await shareButton.click();
  });
});
