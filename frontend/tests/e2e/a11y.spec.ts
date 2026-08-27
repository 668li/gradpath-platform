import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { registerAndLandOnDashboard, uniqueEmail } from './helpers';

/**
 * 无障碍扫描测试
 *
 * 使用 axe-core 对关键页面进行 WCAG2A/AA 级别扫描，
 * 确保公开页面与登录后页面均无严重可访问性违规。
 */
test.describe('无障碍扫描 - 公开页面', () => {
  test('首页无 WCAG2A/AA 违规', async ({ page }) => {
    await page.goto('/');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('登录页无障碍', async ({ page }) => {
    await page.goto('/login');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('注册页无障碍（含 agree_terms 复选框）', async ({ page }) => {
    await page.goto('/register');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });
});

test.describe('无障碍扫描 - 需登录页面', () => {
  test.beforeEach(async ({ page }) => {
    // CI Postgres 为空库（无 test@example.com 种子用户），每个 test 注册独立新用户
    await registerAndLandOnDashboard(page, 'E2E A11y User', uniqueEmail('a11y'));
  });

  test('Dashboard 无障碍', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('Employment 无障碍', async ({ page }) => {
    await page.goto('/employment');
    await page.waitForLoadState('networkidle');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('War-room 无障碍', async ({ page }) => {
    await page.goto('/war-room');
    await page.waitForLoadState('networkidle');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('Kaoyan schools 无障碍', async ({ page }) => {
    await page.goto('/kaoyan/schools');
    await page.waitForLoadState('networkidle');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('Profile 无障碍', async ({ page }) => {
    await page.goto('/profile');
    await page.waitForLoadState('networkidle');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });
});
