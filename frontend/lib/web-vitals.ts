// frontend/lib/web-vitals.ts
// C9 web-vitals 上报 — 将 LCP/CLS/INP/TTFB/FCP 指标上报到后端 /api/metrics/web-vitals
// 同时保留对 /api/tracking/events 的埋点（向后兼容）。
//
// 设计要点：
// 1. 使用 sendBeacon（不阻塞页面卸载，低优先级）；不可用时降级 fetch keepalive
// 2. 单条上报 — web-vitals 指标是稀疏事件（每个页面加载 5 次），无需批量
// 3. 失败静默 — web-vitals 上报失败不能影响用户体验
// 4. 仅在浏览器环境执行，SSR 自动跳过
// 5. 同时调用 tracker.trackWebVital 写入埋点事件流（保持向后兼容）
import type { Metric } from "web-vitals";

export type VitalRating = "good" | "needs-improvement" | "poor";

export interface VitalMetric {
  name: string;
  value: number;
  rating: VitalRating;
  delta: number;
  id: string;
}

interface WebVitalsPayload {
  name: string;
  value: number;
  rating: VitalRating;
  delta: number;
  id: string;
  page: string;
  session_id: string;
  timestamp: string;
}

const VITALS_ENDPOINT = "/api/metrics/web-vitals";
const VITALS_BUFFER_LIMIT = 50;

const vitalsBuffer: VitalMetric[] = [];

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  try {
    const key = "gradpath_session_id";
    let sid = window.sessionStorage.getItem(key);
    if (!sid) {
      sid =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `sess_${Date.now()}_${Math.random().toString(36).slice(2)}`;
      window.sessionStorage.setItem(key, sid);
    }
    return sid;
  } catch {
    // sessionStorage 不可用时退化为临时 ID
    return `sess_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  }
}

function getCurrentPage(): string {
  if (typeof window === "undefined") return "";
  return window.location.pathname;
}

/**
 * 上报单条 web-vital 指标到后端 /api/metrics/web-vitals。
 * 失败静默处理，不抛错。
 */
function reportToBackend(metric: VitalMetric): void {
  if (typeof window === "undefined") return;

  const payload: WebVitalsPayload = {
    name: metric.name,
    value: metric.value,
    rating: metric.rating,
    delta: metric.delta,
    id: metric.id,
    page: getCurrentPage(),
    session_id: getSessionId(),
    timestamp: new Date().toISOString(),
  };

  const body = JSON.stringify(payload);

  // 优先 sendBeacon（不阻塞页面卸载）
  try {
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: "application/json" });
      const ok = navigator.sendBeacon(VITALS_ENDPOINT, blob);
      if (ok) return;
    }
  } catch {
    // sendBeacon 抛错时降级到 fetch
  }

  // 降级：fetch keepalive
  try {
    void fetch(VITALS_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
      credentials: "include",
    }).catch(() => {
      // 静默失败
    });
  } catch {
    // 静默失败
  }
}

function sendToAnalytics(metric: VitalMetric): void {
  // 缓冲供测试与调试读取
  vitalsBuffer.push(metric);
  if (vitalsBuffer.length > VITALS_BUFFER_LIMIT) {
    vitalsBuffer.shift();
  }

  // 上报到后端 /api/metrics/web-vitals
  reportToBackend(metric);

  // 兼容：同步写入埋点事件流（/api/tracking/events）
  try {
    import("@/lib/tracker")
      .then(({ trackWebVital }) => {
        trackWebVital(metric.name, metric.value);
      })
      .catch(() => {
        // tracker not available
      });
  } catch {
    // 静默失败
  }
}

function onCLS(callback: (m: Metric) => void): void {
  try {
    import("web-vitals").then(({ onCLS }) => onCLS(callback));
  } catch {
    // web-vitals not available
  }
}

function onINP(callback: (m: Metric) => void): void {
  try {
    import("web-vitals").then(({ onINP }) => onINP(callback));
  } catch {
    // web-vitals not available
  }
}

function onLCP(callback: (m: Metric) => void): void {
  try {
    import("web-vitals").then(({ onLCP }) => onLCP(callback));
  } catch {
    // web-vitals not available
  }
}

function onTTFB(callback: (m: Metric) => void): void {
  try {
    import("web-vitals").then(({ onTTFB }) => onTTFB(callback));
  } catch {
    // web-vitals not available
  }
}

function onFCP(callback: (m: Metric) => void): void {
  try {
    import("web-vitals").then(({ onFCP }) => onFCP(callback));
  } catch {
    // web-vitals not available
  }
}

/**
 * 启动 web-vitals 监听，注册 5 个核心指标的回调。
 * 在 layout.tsx / app 入口调用一次即可。
 */
export function reportWebVitals(): void {
  if (typeof window === "undefined") return;

  const handleMetric = (metric: Metric) => {
    sendToAnalytics({
      name: metric.name,
      value: metric.value,
      rating: metric.rating,
      delta: metric.delta,
      id: metric.id,
    });
  };

  onCLS(handleMetric);
  onINP(handleMetric);
  onLCP(handleMetric);
  onTTFB(handleMetric);
  onFCP(handleMetric);
}

/**
 * 返回缓冲区中的 web-vitals 数据（供测试与调试）。
 */
export function getVitalsBuffer(): VitalMetric[] {
  return vitalsBuffer;
}

/**
 * 清空缓冲区（供测试使用）。
 */
export function resetVitalsBuffer(): void {
  vitalsBuffer.length = 0;
}

/**
 * 直接上报一条 web-vital 指标（供测试 / 自定义指标使用）。
 */
export function reportVital(metric: VitalMetric): void {
  sendToAnalytics(metric);
}
