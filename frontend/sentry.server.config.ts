// frontend/sentry.server.config.ts
// Sentry 服务端配置（Node.js runtime，Next.js SSR/RSC）。
import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: process.env.SENTRY_ENV || process.env.NODE_ENV,
    tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
    profilesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
    sendDefaultPii: false,
    beforeSend(event) {
      try {
        const request = (event as unknown as { request?: { headers?: Record<string, string>; data?: unknown; cookies?: unknown } }).request;
        if (request) {
          if (request.headers) {
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
          if (request.data) {
            request.data = scrubSensitive(request.data);
          }
          if (request.cookies) {
            request.cookies = "[REDACTED]";
          }
        }
      } catch {
        // ignore scrub errors
      }
      return event;
    },
  });
}

const SENSITIVE_KEYS = new Set([
  "password",
  "password_hash",
  "new_password",
  "current_password",
  "token",
  "access_token",
  "refresh_token",
  "secret",
  "secret_key",
  "api_key",
  "authorization",
  "cookie",
  "session",
  "csrf",
]);

function scrubSensitive(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(scrubSensitive);
  }
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = SENSITIVE_KEYS.has(k.toLowerCase()) ? "[REDACTED]" : scrubSensitive(v);
    }
    return out;
  }
  return value;
}
