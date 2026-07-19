"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { ToastProvider } from "@/components/ui/toast";
import { ErrorBoundary } from "@/components/error-boundary";
import { FeedbackWidget } from "@/components/FeedbackWidget";
import { initTracker, trackPageView } from "@/lib/tracker";

// 优化：web-vitals 使用动态导入，避免 require 破坏 tree-shaking
const reportWebVitals = async () => {
  try {
    const wv = await import("@/lib/web-vitals");
    wv.reportWebVitals();
  } catch {
    // web-vitals not available
  }
};

reportWebVitals();

function TrackerProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  useEffect(() => {
    initTracker();
  }, []);

  useEffect(() => {
    if (pathname) {
      trackPageView(pathname);
    }
  }, [pathname]);

  return <>{children}</>;
}

export function RootLayoutClient({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <TrackerProvider>{children}</TrackerProvider>
        <FeedbackWidget />
      </ToastProvider>
    </ErrorBoundary>
  );
}
