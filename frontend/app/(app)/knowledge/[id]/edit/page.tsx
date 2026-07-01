"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { knowledgeApi } from "@/lib/api";
import { KnowledgeEditor } from "@/components/knowledge-editor";
import { useAuthStore } from "@/stores/auth";
import type { KnowledgeArticle } from "@/types";

export default function EditKnowledgePage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
  const user = useAuthStore((s) => s.user);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  const [authChecked, setAuthChecked] = useState(false);
  const [article, setArticle] = useState<KnowledgeArticle | null>(null);
  const [loading, setLoading] = useState(true);

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

  useEffect(() => {
    if (authChecked && user?.is_admin && id) {
      knowledgeApi
        .get(id)
        .then((data) => setArticle(data))
        .catch(() => {
          // 文章不存在或加载失败
          router.replace("/knowledge");
        })
        .finally(() => setLoading(false));
    }
  }, [authChecked, user, id, router]);

  if (!authChecked || (authChecked && user && !user.is_admin)) {
    return (
      <div className="flex items-center justify-center py-12 text-slate-400">
        <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-brand-500" />
        <span className="ml-2 text-sm">加载中…</span>
      </div>
    );
  }

  return <KnowledgeEditor article={article} loading={loading} />;
}
