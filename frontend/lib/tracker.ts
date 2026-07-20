// frontend/lib/tracker.ts
// 用户行为埋点客户端 — 发送事件到 /api/tracking/events
// 修复: 统一使用 @/lib/api 的 getToken 读取 access_token,
// 避免 localStorage 键名不一致 (旧代码使用 "token"/"auth_token", 实际键为 "gradpath_access_token")
// 注：路由已从 /api/events 迁移到 /api/tracking/events，避免与职业事件 API 冲突
import { getToken } from "@/lib/api";

export type EventType = "page_view" | "click" | "dwell" | "error" | "web_vital";

interface TrackPayload {
  [key: string]: unknown;
}

let sessionId = "";

export function getSessionId(): string {
  if (!sessionId) {
    sessionId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `sess_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  }
  return sessionId;
}

function getCurrentPage(): string {
  if (typeof window === "undefined") return "";
  return window.location.pathname;
}

// 事件缓冲队列（批量发送）
const eventBuffer: Array<{
  session_id: string;
  event_type: string;
  page: string | null;
  element: string | null;
  payload: TrackPayload | null;
}> = [];

let flushTimer: ReturnType<typeof setTimeout> | null = null;

export function track(
  type: EventType,
  page?: string | null,
  element?: string | null,
  payload?: TrackPayload | null,
) {
  if (typeof window === "undefined") return;

  const event = {
    session_id: getSessionId(),
    event_type: type,
    page: page ?? getCurrentPage(),
    element: element ?? null,
    payload: payload ?? null,
  };

  eventBuffer.push(event);

  // 缓冲满或定时刷新
  if (eventBuffer.length >= 10) {
    flushEvents();
  } else if (!flushTimer) {
    flushTimer = setTimeout(flushEvents, 2000);
  }
}

export function flushEvents() {
  if (typeof window === "undefined" || eventBuffer.length === 0) return;

  if (flushTimer) {
    clearTimeout(flushTimer);
    flushTimer = null;
  }

  const events = [...eventBuffer];
  eventBuffer.length = 0;

  // 修复: 使用统一的 getToken 读取真实键名 "gradpath_access_token"
  const token = getToken();
  if (!token) return;

  const body = JSON.stringify({ events });

  // 优先 sendBeacon（不阻塞页面卸载），失败降级 fetch
  if (navigator.sendBeacon) {
    const blob = new Blob([body], { type: "application/json" });
    navigator.sendBeacon("/api/tracking/events", blob);
  } else {
    fetch("/api/tracking/events", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body,
      keepalive: true,
    }).catch(() => {
      // 静默失败，不阻塞用户操作
    });
  }
}

// 页面停留时间追踪
let pageEnterTime = 0;
let currentPath = "";

export function trackPageView(path: string) {
  // 记录上一页停留时间
  if (currentPath && pageEnterTime > 0) {
    const dwellMs = Date.now() - pageEnterTime;
    if (dwellMs > 0 && dwellMs < 1000 * 60 * 30) {
      track("dwell", currentPath, null, { duration_ms: dwellMs });
    }
  }

  currentPath = path;
  pageEnterTime = Date.now();
  track("page_view", path);
}

// 全局点击追踪（带 data-track-id 的元素）
export function initClickTracking() {
  if (typeof document === "undefined") return;
  document.addEventListener("click", (e) => {
    const target = (e.target as HTMLElement)?.closest("[data-track-id]") as HTMLElement | null;
    if (target) {
      const trackId = target.getAttribute("data-track-id");
      const page = getCurrentPage();
      track("click", page, trackId, {
        text: target.textContent?.slice(0, 50),
        tag: target.tagName.toLowerCase(),
      });
    }
  });
}

// 全局错误追踪
export function initErrorTracking() {
  if (typeof window === "undefined") return;
  window.addEventListener("error", (e) => {
    track("error", getCurrentPage(), null, {
      message: e.message?.slice(0, 200),
      stack: e.error?.stack?.slice(0, 500),
      filename: e.filename,
      lineno: e.lineno,
    });
  });
  window.addEventListener("unhandledrejection", (e) => {
    track("error", getCurrentPage(), null, {
      message: String(e.reason)?.slice(0, 200),
      type: "unhandledrejection",
    });
  });
}

// Web Vitals 接入
export function trackWebVital(metric: string, value: number) {
  track("web_vital", getCurrentPage(), null, { metric, value });
}

// 页面隐藏时刷新缓冲
export function initVisibilityFlush() {
  if (typeof document === "undefined") return;
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      flushEvents();
    }
  });
  window.addEventListener("beforeunload", () => flushEvents());
}

// 初始化所有追踪（在 layout 中调用）
export function initTracker() {
  initClickTracking();
  initErrorTracking();
  initVisibilityFlush();
}
