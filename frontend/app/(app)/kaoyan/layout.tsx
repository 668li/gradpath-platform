import { ReactNode } from "react";
import { ErrorBoundary } from "@/components/error-boundary";

export default function KaoyanLayout({ children }: { children: ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>;
}
