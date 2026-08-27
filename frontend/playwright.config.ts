import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright 端到端测试配置
 * 文档: https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "html",

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    locale: "zh-CN",
    timezoneId: "Asia/Shanghai",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 7"] },
      testMatch: /mobile.*\.spec\.ts/,
    },
  ],

  // 自动启动 Next.js dev server
  // CI 里由 workflow 步骤预启动(带 DATABASE_URL/NEXT_PUBLIC_API_URL 等环境),这里直接复用;
  // 本地未启动时才由 Playwright 拉起
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 60 * 1000,
  },
});
