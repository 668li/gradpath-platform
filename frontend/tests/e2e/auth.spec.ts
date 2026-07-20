import { test, expect } from "@playwright/test";

/**
 * 认证流程端到端测试
 *
 * 覆盖登录页渲染、表单校验、错误提示等关键路径。
 * 注意：此测试依赖后端 API server 运行在 localhost:8000。
 */
test.describe("认证流程", () => {
  test("登录页应正确渲染", async ({ page }) => {
    await page.goto("/login");

    // 等待页面加载
    await expect(page).toHaveTitle(/GradPath|职径/i);

    // 检查关键元素存在
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.getByRole("button", { name: /登录|登 录|Login/i })).toBeVisible();
  });

  test("空表单提交应显示校验错误", async ({ page }) => {
    await page.goto("/login");

    // 点击登录按钮（不填写任何内容）
    await page.getByRole("button", { name: /登录|登 录|Login/i }).click();

    // 应显示某种校验提示（具体文案取决于实现）
    await expect(page.locator("body")).toContainText(/邮箱|密码|required|必填/i, {
      timeout: 3000,
    });
  });

  test("无效凭据应显示错误提示", async ({ page }) => {
    await page.goto("/login");

    await page.fill('input[type="email"]', "nonexistent@test.com");
    await page.fill('input[type="password"]', "WrongPassword1!");

    await page.getByRole("button", { name: /登录|登 录|Login/i }).click();

    // 应显示错误提示（401 或类似）
    await expect(page.locator("body")).toContainText(/错误|失败|无效|incorrect/i, {
      timeout: 5000,
    });
  });
});

test.describe("注册页", () => {
  test("注册页应正确渲染", async ({ page }) => {
    await page.goto("/register");

    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.getByRole("button", { name: /注册|注 册|Register/i })).toBeVisible();
  });
});
