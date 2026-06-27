"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
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
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // 在无 Provider 时降级为 console，避免页面崩溃
    return {
      push: (message: string, type: ToastType = "info") => {
        // eslint-disable-next-line no-console
        console.log(`[toast:${type}]`, message);
      },
    };
  }
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const push = useCallback((message: string, type: ToastType = "info") => {
    const id = Date.now() + Math.random();
    setItems((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  const remove = (id: number) =>
    setItems((prev) => prev.filter((t) => t.id !== id));

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-80 max-w-[90vw]">
        {items.map((t) => (
          <div
            key={t.id}
            className={cn(
              "flex items-start gap-2 rounded-lg border px-4 py-3 shadow-lg bg-white animate-in",
              t.type === "success" && "border-green-200",
              t.type === "error" && "border-red-200",
              t.type === "info" && "border-slate-200",
            )}
          >
            {t.type === "success" && (
              <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0" />
            )}
            {t.type === "error" && (
              <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
            )}
            <p className="text-sm text-slate-700 flex-1">{t.message}</p>
            <button
              onClick={() => remove(t.id)}
              className="text-slate-400 hover:text-slate-600"
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
