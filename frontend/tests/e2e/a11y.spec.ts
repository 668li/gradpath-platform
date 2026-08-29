import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { registerAndLandOnDashboard, uniqueEmail } from './helpers';

/**
 * 无障碍扫描测试
 *
 * 使用 axe-core 对关键页面进行 WCAG2A/AA 级别扫描，
 * 确保公开页面与登录后页面均无严重可访问性违规。
 */

async function expectNoViolations(page: Page, path: string): Promise<void> {
  await page.goto(path);
  // 等 Next dev 按需编译与样式注入完成后再扫描，避免过渡态误报
  await page.waitForLoadState('networkidle');
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    // Next dev 会把受保护页的重定向渲染为 <meta http-equiv="refresh">
    // 过渡标签（生产构建是真实 30x），axe 对其报 meta-refresh 假阳性，故排除
    .disableRules(['meta-refresh'])
    .analyze();
  expect(results.violations).toEqual([]);
}

test.describe('无障碍扫描 - 公开页面', () => {
  test('首页无 WCAG2A/AA 违规', async ({ page }) => {
    await expectNoViolations(page, '/');
  });

  test('登录页无障碍', async ({ page }) => {
    await expectNoViolations(page, '/login');
  });

  test('注册页无障碍（含 agree_terms 复选框）', async ({ page }) => {
    await expectNoViolations(page, '/register');
  });
});

test.describe('无障碍扫描 - 需登录页面', () => {
  test.beforeEach(async ({ page }) => {
    // CI Postgres 为空库（无种子用户），每个 test 注册独立新用户
    await registerAndLandOnDashboard(page, 'E2E A11y User', uniqueEmail('a11y'));
  });

  test('Dashboard 无障碍', async ({ page }) => {
    await expectNoViolations(page, '/dashboard');
  });

  test('Employment 无障碍', async ({ page }) => {
    await expectNoViolations(page, '/employment');
  });

  test('War-room 无障碍', async ({ page }) => {
    await expectNoViolations(page, '/war-room');
  });

  test('Kaoyan schools 无障碍', async ({ page }) => {
    await expectNoViolations(page, '/kaoyan/schools');
  });

  test('Profile 无障碍', async ({ page }) => {
    await expectNoViolations(page, '/profile');
  });
});
