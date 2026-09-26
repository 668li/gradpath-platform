// frontend/tests/e2e/retirement-guard.spec.ts
// D3（2026-09-26 marathon 余量池）：退役线回归护栏——考公 API 已删端点保持 404、
// 退役页出明确退役说明、首页口号不再承诺推送。防"考公路复活"回归。
// 本地跑：npx playwright test tests/e2e/retirement-guard.spec.ts --workers=2
import { test, expect } from "@playwright/test";

const RETIRED_APIS = [
  "/api/civil-service/positions",
  "/api/civil-service/province-positions",
  "/api/civil-service/post-intel/public?limit=10",
  "/api/gwy-positions",
  "/api/gwy-score-lines",
];

test.describe("退役线回归护栏（D3）", () => {
  for (const api of RETIRED_APIS) {
    test(`已删考公端点保持非 200：${api}`, async ({ request }) => {
      const resp = await request.get(api);
      expect(resp.status(), `${api} 应为 404/405/422 等非 200，防复活`).not.toBe(200);
    });
  }

  test("退役页出明确退役说明（R-07 口径）", async ({ page }) => {
    // middleware 只认 gradpath_token cookie 的存在性；未带会被 307 到 /login
    await page.context().addCookies([
      { name: "gradpath_token", value: "e2e-probe", url: "http://localhost:3000" },
    ]);
    await page.goto("/civil-service");
    await expect(page.getByText("该功能已随考公路退役")).toBeVisible({ timeout: 15_000 });
  });

  test("首页新口号在墙、旧推送承诺下墙（C1）", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("每条情报都带官方来源的考研决策伴随")).toBeVisible({
      timeout: 15_000,
    });
    const body = await page.content();
    expect(body).not.toContain("准时推你一把");
    expect(body).not.toContain("全覆盖");
  });

  test("时间线 API 返回考研真节点且带 date_status（B2）", async ({ request }) => {
    // 数据面断言依赖本地 backend：8001 未起（纯前端本地跑）时跳过——生产冒烟已实证
    let backendUp = false;
    try {
      const h = await request.get("http://127.0.0.1:8001/health", { timeout: 3_000 });
      backendUp = h.ok();
    } catch {
      backendUp = false;
    }
    test.skip(!backendUp, "本地 backend 未启动，跳过数据面断言（生产冒烟已实证）");
    const resp = await request.get("/api/civil-service/timeline/exams");
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    const exams = Array.isArray(data) ? data : (data.exams ?? data.items ?? []);
    const kaoyan = exams.find((e: { code?: string }) => (e.code ?? "").includes("kaoyan"));
    expect(kaoyan, "时间线应含 kaoyan-2027 考次").toBeTruthy();
    expect(kaoyan.next_node?.date_status).toBeTruthy();
  });
});
