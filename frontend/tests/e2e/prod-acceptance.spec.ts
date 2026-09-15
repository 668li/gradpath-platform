import { test, expect } from "@playwright/test";
import { randomBytes } from "node:crypto";

/**
 * 生产验收 · 交互修复四验（默认不运行）
 *
 * 只在显式开启时运行，CI 与本地 e2e 不受影响：
 *   PROD_ACCEPTANCE=1 PLAYWRIGHT_BASE_URL=https://quxianglab.cn npx playwright test prod-acceptance --reporter=line
 *
 * 覆盖四件事（都是"点下去有没有反应"类，代码层已证、需要在真浏览器点一次）：
 *   A. 导航里带子项的分组父条目应可导航（原为纯展开按钮，href 被吞）
 *   B. 技能树页不再出现「能力地图加载失败」（后端 /api/skills/map 从未存在，视图已摘）
 *   C. 非管理员访问 /admin 应被重定向到 /dashboard
 *   D. 移动端 375px 顶栏「命令面板」一次点击即可打开（原入口在抽屉底部被截断）
 *
 * 账号在运行时随机生成；跑完请用 psql 删除 acc-*@example.com，勿留生产脏账号。
 */

const enabled = process.env.PROD_ACCEPTANCE === "1";

// 本机直连生产会被 fail2ban 盯上（记忆：本机 IP 曾两次接近自封），所以走 SSH 隧道出站：
//   ssh -N -L 18443:127.0.0.1:443 gradpath
// 浏览器把生产域名解析到隧道口，Host/SNI 仍是 quxianglab.cn，nginx 照常按 vhost 服务。
test.use({
  ignoreHTTPSErrors: true,
  launchOptions: {
    args: [
      `--host-resolver-rules=MAP quxianglab.cn 127.0.0.1:${process.env.PROD_TUNNEL_PORT ?? "18443"}`,
    ],
  },
});

test.describe("生产验收 · 交互修复四验", () => {
  test.skip(!enabled, "仅当 PROD_ACCEPTANCE=1 且 PLAYWRIGHT_BASE_URL 指向生产时运行");
  test.setTimeout(240_000);

  test("导航分组 / 技能树 / admin 守卫 / 移动端命令面板", async ({ page, browser }) => {
    const email = `acc-${Date.now()}@example.com`;
    const password = `Aa${randomBytes(6).toString("hex")}!9`;

    // ---- 造号（API）----
    const reg = await page.request.post("/api/auth/register", {
      data: { email, password, name: "验收账号" },
    });
    expect(reg.status(), `register 应 201，实得 ${reg.status()}`).toBe(201);

    const login = await page.request.post("/api/auth/login", { data: { email, password } });
    expect(login.ok(), "login 应成功").toBeTruthy();
    const tokens = (await login.json()) as { access_token: string; refresh_token: string };

    // 跳过 onboarding，否则 (app) 布局会把所有受保护页重定向到 /onboarding
    const skipped = await page.request.post("/api/onboarding/skip", {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });
    expect(skipped.ok(), "onboarding/skip 应成功").toBeTruthy();

    const seed = async (p: typeof page) => {
      // Edge Middleware 读不到 localStorage，路由守卫看的是 gradpath_token cookie
      // （lib/api/client.ts setToken 会同步维护该 cookie，注入时必须写齐两处，
      // 否则 goto /dashboard 会被中间件 302 到 /login）
      await p.addInitScript(
        (t: { a: string; r: string }) => {
          window.localStorage.setItem("gradpath_access_token", t.a);
          window.localStorage.setItem("gradpath_refresh_token", t.r);
          document.cookie = `gradpath_token=${encodeURIComponent(t.a)}; Path=/; SameSite=Lax; Max-Age=2592000`;
        },
        { a: tokens.access_token, r: tokens.refresh_token },
      );
    };

    // ---- A. 桌面：分组父条目可导航 ----
    await page.setViewportSize({ width: 1440, height: 900 });
    await seed(page);
    // init script 要等首次导航落地后才执行：先访公开页把 cookie 写进生产源，
    // 否则对 /dashboard 的第一次请求不带 cookie，会被 Edge Middleware 302 到 /login
    await page.goto("/login");
    await page.goto("/dashboard");
    const groupParent = page.locator('aside a[href="/decision-center"]').first();
    await expect(groupParent, "导航中应存在指向 /decision-center 的分组父条目").toBeVisible();
    await groupParent.click();
    await expect(page, "点分组父条目应真的导航到决策中心").toHaveURL(/\/decision-center/, {
      timeout: 20_000,
    });

    // ---- B. 技能树页不再报能力地图失败 ----
    await page.goto("/skills");
    await expect(page.getByText("能力地图加载失败")).toHaveCount(0);
    await expect(page.locator("body")).toContainText("技能", { timeout: 20_000 });

    // ---- C. 非管理员访问 /admin 被重定向 ----
    await page.goto("/admin");
    await expect(page, "/admin 应把非管理员踢回 /dashboard").toHaveURL(/\/dashboard/, {
      timeout: 20_000,
    });

    // ---- D. 移动端 375px：顶栏命令面板一次点击可开 ----
    const ctx = await browser.newContext({ viewport: { width: 375, height: 700 }, locale: "zh-CN" });
    const mobile = await ctx.newPage();
    await seed(mobile);
    await mobile.goto("/login");
    await mobile.goto("/dashboard");
    const trigger = mobile.getByRole("button", { name: "打开命令面板" });
    await expect(trigger, "移动端顶栏应有命令面板入口").toBeVisible({ timeout: 20_000 });
    await trigger.click();
    await expect(mobile.getByRole("dialog", { name: "命令面板" }), "一次点击应打开面板").toBeVisible({
      timeout: 10_000,
    });
    await ctx.close();

    console.log(`[prod-acceptance] 验收账号（跑完请删）：${email}`);
  });
});