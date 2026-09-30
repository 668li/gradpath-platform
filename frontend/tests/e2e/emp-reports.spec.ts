import { test, expect } from '@playwright/test';
import { registerAndLandOnDashboard, uniqueEmail } from './helpers';

/**
 * EMP-1c 本地交互验证（2026-09-30）：院校就业报告区块展开流程。
 * 依赖本地 sqlite 已种 test-univ 数据（scripts 手动种子）。
 */
test.describe('EMP-1c 院校就业报告区块', () => {
  test.beforeEach(async ({ page }) => {
    await registerAndLandOnDashboard(page, 'E2E EMP', uniqueEmail('emp'));
  });

  test('展开学校显示报告详情与原文链接', async ({ page }) => {
    await page.goto('/employment?tab=market');
    // 报告区块标题出现
    await expect(page.getByText(/院校就业报告/).first()).toBeVisible({ timeout: 30_000 });
    // 校名按钮（区块内，section 限定避免误匹配导航）
    const section = page.locator('section', { has: page.getByText('院校就业报告') }).first();
    const schoolBtn = section.locator('button[aria-expanded]').first();
    await expect(schoolBtn).toBeVisible({ timeout: 15_000 });
    await schoolBtn.click();
    // 展开后出现报告原文链接与就业率
    await expect(section.getByText(/查看报告原文/).first()).toBeVisible({ timeout: 15_000 });
    await expect(section.getByText(/就业率/).first()).toBeVisible();
  });
});
