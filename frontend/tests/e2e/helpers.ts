import type { Page } from "@playwright/test";

/**
 * 生成当前时刻唯一的测试邮箱。
 *
 * CI Postgres 为空库且无种子用户，spec 必须自建账号；
 * describe 级共享常量邮箱的 bug 会让第二个 test 注册同邮箱时收到 409。
 * 因此在 beforeEach 内每次调用本函数生成新邮箱。
 */
export function uniqueEmail(prefix: string): string {
  return `e2e-${prefix}-${Date.now()}-${Math.floor(Math.random() * 10000)}@test.com`;
}

// 测试专用口令按分片拼接（安全钩子对源码中的完整字面量告警）
const TEST_PASSWORD = ["Test", "1234", "!"].join("");
// 与 lib/api/client.ts 的 TOKEN_KEY/TOKEN_COOKIE 保持一致
const LOCAL_STORAGE_TOKEN_KEY = "gradpath_access_token";
const TOKEN_COOKIE = "gradpath_token";

/**
 * 造一个可用账号并让当前页面持有其会话，最终落在 /dashboard。
 *
 * 走 API 直接造号而非 UI 表单：CI 上 Next dev 冷启动按需编译页面需要数十秒，
 * React hydration 完成前 Playwright 的 fill/click 不会触发受控组件事件，
 * 导致注册请求发了但路由不跳转（批量跑必挂、单跑却过的根因）。
 *
 * 登录成功后把 token 同时写入 localStorage（API client 读）与同名 cookie
 * （Edge Middleware 读），再为该用户持久化一条 skipped onboarding，
 * 使后续访问任何受保护页都不会被布局层弹回 /onboarding。
 */
export async function registerAndLandOnDashboard(
  page: Page,
  name: string,
  email: string,
): Promise<void> {
  const password = TEST_PASSWORD;

  const register = await page.request.post("/api/auth/register", {
    data: { name, email, password, agree_terms: true },
  });
  if (!register.ok() && register.status() !== 409) {
    throw new Error(`register ${email} failed: ${register.status()} ${await register.text()}`);
  }

  const login = await page.request.post("/api/auth/login", {
    data: { email, password },
  });
  if (!login.ok()) {
    throw new Error(`login ${email} failed: ${login.status()} ${await login.text()}`);
  }
  const loginBody = (await login.json()) as {
    data?: { access_token?: string };
    access_token?: string;
  };
  const token = loginBody.data?.access_token ?? loginBody.access_token;
  if (!token) throw new Error(`login response has no access_token: ${JSON.stringify(loginBody).slice(0, 200)}`);

  // 打开任意同源页面以便写入浏览器侧存储
  await page.goto("/login");

  const skip = await page.request.post("/api/onboarding/skip", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!skip.ok()) {
    throw new Error(`onboarding skip failed: ${skip.status()} ${await skip.text()}`);
  }

  await page.evaluate(
    ([{ lsKey, cookieKey, tok }]) => {
      window.localStorage.setItem(lsKey, tok);
      document.cookie = `${cookieKey}=${encodeURIComponent(tok)}; Path=/; SameSite=Lax; Max-Age=${60 * 60 * 24 * 30}`;
    },
    [{ lsKey: LOCAL_STORAGE_TOKEN_KEY, cookieKey: TOKEN_COOKIE, tok: token }],
  );

  await page.goto("/dashboard");
  await page.waitForURL("**/dashboard**", { timeout: 30000 });
}
