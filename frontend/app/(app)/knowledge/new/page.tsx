"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { KnowledgeEditor } from "@/components/knowledge-editor";
import { useAuthStore } from "@/stores/auth";

export default function NewKnowledgePage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const fetchUser = useAuthStore((s) => s.fetchUser);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    if (!user) {
      fetchUser().then(() => setAuthChecked(true));
    } else {
      setAuthChecked(true);
    }
  }, [user, fetchUser]);

  useEffect(() => {
    if (authChecked && user && !user.is_admin) {
      router.replace("/dashboard");
    }
  }, [authChecked, user, router]);

  if (!authChecked || (authChecked && user && !user.is_admin)) {
    return (
      <div className="flex items-center justify-center py-12 text-slate-400">
        <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-brand-500" />
        <span className="ml-2 text-sm">加载中…</span>
      </div>
    );
  }

  return <KnowledgeEditor />;
}
