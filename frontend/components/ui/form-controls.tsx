"use client";

import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
  ReactNode,
} from "react";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";

const fieldBase =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50 disabled:text-slate-400";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input ref={ref} className={cn(fieldBase, className)} {...props} />
  ),
);
Input.displayName = "Input";

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea ref={ref} className={cn(fieldBase, "min-h-[80px]", className)} {...props} />
));
Textarea.displayName = "Textarea";

export const Select = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <select ref={ref} className={cn(fieldBase, "pr-8", className)} {...props}>
    {children}
  </select>
));
Select.displayName = "Select";

export function Field({
  label,
  required,
  children,
  hint,
}: {
  label: string;
  required?: boolean;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">
        {label}
        {required && <span className="ml-0.5 text-red-500">*</span>}
      </span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-400">{hint}</span>}
    </label>
  );
}

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const variantClass: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-600 text-white hover:bg-brand-700 disabled:bg-brand-300",
  secondary:
    "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 disabled:text-slate-400",
  ghost: "text-slate-600 hover:bg-slate-100 disabled:text-slate-400",
  danger: "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300",
};

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: ButtonVariant;
    loading?: boolean;
  }
>(({ className, variant = "primary", loading, disabled, children, ...props }, ref) => (
  <button
    ref={ref}
    disabled={disabled || loading}
    className={cn(
      "inline-flex items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed",
      variantClass[variant],
      className,
    )}
    {...props}
  >
    {loading && (
      <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
    )}
    {children}
  </button>
));
Button.displayName = "Button";

export function Badge({
  children,
  color = "slate",
}: {
  children: ReactNode;
  color?: "slate" | "green" | "amber" | "red" | "blue" | "purple";
}) {
  const colors: Record<string, string> = {
    slate: "bg-slate-100 text-slate-600",
    green: "bg-green-100 text-green-700",
    amber: "bg-amber-100 text-amber-700",
    red: "bg-red-100 text-red-700",
    blue: "bg-blue-100 text-blue-700",
    purple: "bg-purple-100 text-purple-700",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        colors[color],
      )}
    >
      {children}
    </span>
  );
}
