"use client";

import { useEffect, useState, type ReactNode } from "react";
import { AppNav } from "@/components/nav";
import { AuthGuard } from "@/components/auth-guard";
import { useAuthStore } from "@/stores/auth";

export default function AppLayout({ children }: { children: ReactNode }) {
  const fetchUser = useAuthStore((s) => s.fetchUser);
  const user = useAuthStore((s) => s.user);
  const [fetched, setFetched] = useState(false);

  // 首次进入受保护区域时拉取用户信息（若 store 中没有）
  useEffect(() => {
    if (!user && !fetched) {
      setFetched(true);
      fetchUser();
    }
  }, [user, fetched, fetchUser]);

  return (
    <AuthGuard>
      <div className="min-h-screen bg-paper-100">
        <AppNav />
        <main className="md:pl-64">
          <div className="mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-10">
            {children}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
