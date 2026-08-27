import type { Page } from "@playwright/test";

/**
 * 生成当前时刻唯一的测试邮箱。
 *
 * CI Postgres 为空库且无种子用户，spec 必须自注册账号；
 * describe 级共享常量邮箱的 bug 会让第二个 test 注册同邮箱时收到 409。
 * 因此在 beforeEach 内每次调用本函数生成新邮箱。
 */
export function uniqueEmail(prefix: string): string {
  return `e2e-${prefix}-${Date.now()}-${Math.floor(Math.random() * 10000)}@test.com`;
}

/**
 * 注册新用户并稳定落在 /dashboard。
 *
 * 新用户注册后被送到 /onboarding（布局层发现 onboarding 未完成即重定向）；
 * 点"跳过"持久化 skipped 后进入 /dashboard。下次进受保护页时布局层
 * 读到的 onboarding 状态为 completed，不会再被踢回 onboarding。
 */
export async function registerAndLandOnDashboard(
  page: Page,
  name: string,
  email: string,
): Promise<void> {
  await page.goto("/register");
  await page.fill('input[name="name"]', name);
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', "Test1234!");
  await page.check('input[name="agree_terms"]');
  await page.click('button[type="submit"]');

  // 注册成功后落在 /onboarding 或 /dashboard
  await page.waitForURL(/(onboarding|dashboard)/, { timeout: 20000 });
  if (page.url().includes("/onboarding")) {
    await page.locator('[data-testid="onboarding-skip-button"]').click();
  }
  await page.waitForURL("**/dashboard**", { timeout: 20000 });
}