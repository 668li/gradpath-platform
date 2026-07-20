"use client";

import { Component, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/form-controls";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50/50 px-6 py-14 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-100">
            <AlertTriangle className="h-6 w-6 text-red-600" strokeWidth={1.5} />
          </div>
          <p className="mt-4 font-display text-base font-medium text-ink-900">
            页面加载失败
          </p>
          <p className="mt-1.5 text-sm text-ink-500 max-w-sm leading-relaxed">
            {this.state.error?.message || "发生了未知错误，请刷新页面重试"}
          </p>
          <div className="mt-5 flex gap-3">
            <Button variant="secondary" onClick={this.handleReset}>
              <RefreshCw className="h-4 w-4 mr-1.5" />
              重试
            </Button>
            <Button onClick={() => window.location.reload()}>
              刷新页面
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
