"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { CheckCircle2, AlertCircle, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "info";
interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  push: (message: string, type?: ToastType) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // 在无 Provider 时降级为空操作，避免页面崩溃（不向 console 输出调试噪声）
    const fallbackPush = (_message: string, _type: ToastType = "info") => {};
    return {
      push: fallbackPush,
      success: (message: string) => fallbackPush(message, "success"),
      error: (message: string) => fallbackPush(message, "error"),
      info: (message: string) => fallbackPush(message, "info"),
    };
  }
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const timersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach((t) => clearTimeout(t));
      timers.clear();
    };
  }, []);

  const push = useCallback((message: string, type: ToastType = "info") => {
    const id = Date.now() + Math.random();
    setItems((prev) => [...prev, { id, message, type }]);
    const timer = setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id));
      timersRef.current.delete(id);
    }, 3500);
    timersRef.current.set(id, timer);
  }, []);

  const success = useCallback((message: string) => push(message, "success"), [push]);
  const error = useCallback((message: string) => push(message, "error"), [push]);
  const info = useCallback((message: string) => push(message, "info"), [push]);

  const remove = (id: number) => {
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
    setItems((prev) => prev.filter((t) => t.id !== id));
  };

  // 用 useMemo 稳定 context value，避免每次渲染创建新对象导致消费者无限重渲染
  const contextValue = useMemo<ToastContextValue>(() => ({
    push, success, error, info,
  }), [push, success, error, info]);

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-80 max-w-[90vw]">
        {items.map((t) => (
          <div
            key={t.id}
            className={cn(
              "flex items-start gap-2 rounded-lg border px-4 py-3 shadow-lg bg-white animate-in",
              t.type === "success" && "border-green-200",
              t.type === "error" && "border-red-200",
              t.type === "info" && "border-ink-200",
            )}
          >
            {t.type === "success" && (
              <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0" />
            )}
            {t.type === "error" && (
              <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
            )}
            <p className="text-sm text-ink-700 flex-1">{t.message}</p>
            <button
              onClick={() => remove(t.id)}
              className="text-ink-400 hover:text-ink-600"
              aria-label="关闭"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
