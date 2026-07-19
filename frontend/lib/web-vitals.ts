import type { Metric } from "web-vitals";

type VitalMetric = {
  name: string;
  value: number;
  rating: "good" | "needs-improvement" | "poor";
  delta: number;
  id: string;
};

const vitalsBuffer: VitalMetric[] = [];

function sendToAnalytics(metric: VitalMetric) {
  vitalsBuffer.push(metric);

  // 优先发送到埋点API（tracker）
  try {
    import("@/lib/tracker").then(({ trackWebVital }) => {
      trackWebVital(metric.name, metric.value);
    });
  } catch {
    // tracker not available
  }

  // 兼容旧端点（如果存在）
  if (typeof window !== "undefined" && navigator.sendBeacon) {
    const body = JSON.stringify(metric);
    navigator.sendBeacon("/api/vitals", body);
  }
}

function onCLS(callback: (m: Metric) => void) {
  try {
    import("web-vitals").then(({ onCLS }) => onCLS(callback));
  } catch {
    // web-vitals not available
  }
}

function onINP(callback: (m: Metric) => void) {
  try {
    import("web-vitals").then(({ onINP }) => onINP(callback));
  } catch {
    // web-vitals not available
  }
}

function onLCP(callback: (m: Metric) => void) {
  try {
    import("web-vitals").then(({ onLCP }) => onLCP(callback));
  } catch {
    // web-vitals not available
  }
}

function onTTFB(callback: (m: Metric) => void) {
  try {
    import("web-vitals").then(({ onTTFB }) => onTTFB(callback));
  } catch {
    // web-vitals not available
  }
}

function onFCP(callback: (m: Metric) => void) {
  try {
    import("web-vitals").then(({ onFCP }) => onFCP(callback));
  } catch {
    // web-vitals not available
  }
}

export function reportWebVitals() {
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

export function getVitalsBuffer(): VitalMetric[] {
  return vitalsBuffer;
}
