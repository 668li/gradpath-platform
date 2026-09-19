import { test, expect } from "@playwright/test";
import { registerAndLandOnDashboard, uniqueEmail } from "./helpers";

/**
 * 决策助手完整流端到端测试
 *
 * ⚠️ 2026-09-19 复测状态（方向席位 E2E 全量实测后改写）：
 * 信息架构重构（f063b37 八路由302 + a5b731d）把 /decision-lab 302 到 /decision-center，
 * 但五步决策向导（new-decision-button/decision-title-input/analyze-button 等 testid）
 * 只存在于不可达的 decision-lab/page.tsx 孤儿里；决策中心的"新建决策"指向 /decisions
 * 又被 302 弹回决策中心（循环重定向）——**当前已提交树上结构化决策创建流程不可达**。
 * 产品需拍板：恢复创建入口（决策中心内嵌向导或移除 /decisions 重定向）、或下线向导。
 * 拍板前原向导用例转 test.fixme，保留重定向与页面渲染真值测试。
 *
 * 决策实验室涉及多个 LLM 依赖（预验尸分析、红队问题、AI 综合分析），
 * 全部通过 page.route() mock。
 */
test.describe("决策助手完整流", () => {
  test.setTimeout(30000);

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

    // 造号走 API（UI 注册在 CI 批量跑下有 hydration 竞态与限流 429 风险）
    await registerAndLandOnDashboard(page, "E2E Decision User", uniqueEmail("decision"));
  });

  test("/decision-lab 现状：302 重定向到决策中心且页面可渲染", async ({ page }) => {
    await page.goto("/decision-lab");

    await expect(page).toHaveURL(/\/decision-center/, { timeout: 15000 });
    await expect(page.locator("h1")).toContainText(/决策中心/i, { timeout: 10000 });
    // 页面有创建入口文案（真值：入口当前指向 /decisions，而该 URL 被 302 弹回——见头注的循环重定向缺陷）
    await expect(page.locator("body")).toContainText(/新建决策|创建决策/i, { timeout: 10000 });
  });

  test.fixme("完整决策流程：创建 → 填写 → AI 分析 → 保存", async () => {
    // 五步向导 testid 全部在孤儿 decision-lab/page.tsx 上（/decision-lab 已 302），
    // 产品拍板恢复创建入口后启用本用例并恢复 mock 流程
  });

  test("决策列表页可正确渲染", async ({ page }) => {
    await page.goto("/decision-lab");

    // 即使列表为空也应正常渲染（当前落地=决策中心，文案已随 IA 重构更新）
    await expect(page.locator("body")).toContainText(/决策中心|新建决策|创建决策|历史分析/i, {
      timeout: 10000,
    });
  });
});
