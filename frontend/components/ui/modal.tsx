"use client";

import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  className?: string;
}

export function Modal({ open, onClose, title, children, className }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        className={cn(
          "relative z-10 w-full max-w-lg rounded-2xl bg-white shadow-xl border border-slate-200",
          className,
        )}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <h3 className="text-base font-semibold text-slate-800">{title}</h3>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600"
              aria-label="关闭"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        )}
        <div className="px-6 py-5 max-h-[70vh] overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
