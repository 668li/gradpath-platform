import { test, expect } from "@playwright/test";

/**
 * 社区发帖完整流端到端测试
 *
 * 覆盖登录 → /community → 点击发帖 → 填写 title + content → 提交
 * → 验证帖子出现在列表 → 展开评论 → 发表评论 → 验证评论显示 的关键路径。
 *
 * 注意：本测试覆盖完整业务流，需后端运行；发帖/评论接口无 LLM 依赖，
 * 不需要 mock（但保留 page.route() 占位以备扩展）。
 */
test.describe("社区发帖完整流", () => {
  test.setTimeout(30000);

  const TEST_EMAIL = `e2e-community-${Date.now()}-${Math.floor(Math.random() * 10000)}@test.com`;
  const POST_TITLE = `E2E 测试帖子 - ${Date.now()}`;
  const POST_CONTENT = "这是一条来自 Playwright E2E 测试的帖子内容，用于验证发帖完整流程。";
  const COMMENT_CONTENT = `E2E 测试评论 - ${Date.now()}`;

  test.beforeEach(async ({ page }) => {
    // 注册并跳过 onboarding
    await page.goto("/register");
    await page.fill('input[name="name"]', "E2E Community User");
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

  test("社区页面应正确渲染", async ({ page }) => {
    await page.goto("/community");

    await expect(page.locator("h1")).toContainText(/社区/i, { timeout: 10000 });
    await expect(page.locator('[data-testid="new-post-button"]')).toBeVisible();
  });

  test("完整发帖流程：发帖 → 列表可见 → 评论", async ({ page }) => {
    await page.goto("/community");

    // 等待页面加载
    await expect(page.locator('[data-testid="new-post-button"]')).toBeVisible({ timeout: 10000 });

    // 点击"发帖"展开编辑器
    await page.locator('[data-testid="new-post-button"]').click();

    // 验证编辑器出现
    await expect(page.locator('[data-testid="post-title-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="post-content-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="submit-post-button"]')).toBeVisible();

    // 填写标题和内容（topic_type=school_major 已在源码中固定）
    await page.locator('[data-testid="post-title-input"]').fill(POST_TITLE);
    await page.locator('[data-testid="post-content-input"]').fill(POST_CONTENT);

    // 提交发帖
    await page.locator('[data-testid="submit-post-button"]').click();

    // 验证帖子出现在列表中
    await expect(page.locator("body")).toContainText(POST_TITLE, { timeout: 10000 });
    await expect(page.locator("body")).toContainText(POST_CONTENT);

    // 展开第一条帖子的评论区（找到包含我们标题的帖子卡片，点击评论按钮）
    const postCard = page.locator("div", { hasText: POST_TITLE }).first();
    await postCard.getByText(/评论/).click();

    // 验证评论输入框出现
    await expect(page.locator('[data-testid="comment-input"]')).toBeVisible({ timeout: 5000 });

    // 输入评论
    await page.locator('[data-testid="comment-input"]').fill(COMMENT_CONTENT);
    await page.locator('[data-testid="submit-comment-button"]').click();

    // 验证评论显示
    await expect(page.locator("body")).toContainText(COMMENT_CONTENT, { timeout: 10000 });
  });

  test("空内容提交应被前端阻止", async ({ page }) => {
    await page.goto("/community");
    await expect(page.locator('[data-testid="new-post-button"]')).toBeVisible({ timeout: 10000 });

    await page.locator('[data-testid="new-post-button"]').click();

    // 不填任何内容直接点击发布（应被 postsApi.create 前的 content.trim() 检查阻止）
    await page.locator('[data-testid="submit-post-button"]').click();

    // 编辑器仍应可见（未成功提交）
    await expect(page.locator('[data-testid="post-content-input"]')).toBeVisible();
  });
});

// 保留原有的只读测试（与已有 community.spec.ts 兼容）
test.describe("社区浏览（只读）", () => {
  test.setTimeout(30000);

  test("社区页面渲染广场与分类", async ({ page }) => {
    await page.goto("/community");

    await expect(page.locator("body")).toContainText(/社区|帖子|广场|讨论/i, {
      timeout: 10000,
    });
  });
});
