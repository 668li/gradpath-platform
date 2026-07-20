// frontend/sentry.client.config.ts
// Sentry 客户端配置（浏览器端）。
// 仅当 NEXT_PUBLIC_SENTRY_DSN 环境变量存在时初始化，否则模块加载即跳过。
import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENV || process.env.NODE_ENV,
    // 采样率：生产环境 10%，开发环境 100%
    tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
    profilesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
    // 关闭 PII 自动收集，遵循最小化原则
    sendDefaultPii: false,
    // 通用 beforeSend 钩子：过滤敏感字段
    beforeSend(event) {
      try {
        // request headers
        const request = (event as unknown as { request?: { headers?: Record<string, string> } }).request;
        if (request && request.headers) {
          const scrubbed: Record<string, string> = {};
          for (const [k, v] of Object.entries(request.headers)) {
            const lk = k.toLowerCase();
            if (lk === "authorization" || lk === "cookie" || lk === "x-api-key") {
              scrubbed[k] = "[REDACTED]";
            } else {
              scrubbed[k] = v;
            }
          }
          request.headers = scrubbed;
        }
      } catch {
        // ignore scrub errors — never block event submission
      }
      return event;
    },
    // 忽略常见非关键错误
    ignoreErrors: [
      // 浏览器扩展噪声
      "top.GLOBALS",
      "ResizeObserver loop limit exceeded",
      "ResizeObserver loop completed with undelivered notifications",
      // 用户取消请求
      "AbortError",
      // 网络瞬时错误（已由 client.ts 重试）
      "Network request failed",
    ],
  });
}
