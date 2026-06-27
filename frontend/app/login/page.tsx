"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { GraduationCap } from "lucide-react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useToast } from "@/components/ui/toast";
import { Button, Field, Input } from "@/components/ui/form-controls";

export default function LoginPage() {
  const router = useRouter();
  const toast = useToast();
  const setToken = useAuthStore((s) => s.setToken);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      toast.push("请填写邮箱和密码", "error");
      return;
    }
    setLoading(true);
    try {
      const tokenRes = await authApi.login({ email, password });
      setToken(tokenRes.access_token);
      const user = await fetchUser();
      if (!user) {
        toast.push("登录成功但获取用户信息失败", "error");
        setLoading(false);
        return;
      }
      toast.push("登录成功", "success");
      router.replace("/dashboard");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "登录失败", "error");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 to-slate-100 px-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 text-white shadow-lg">
            <GraduationCap className="h-7 w-7" />
          </div>
          <h1 className="mt-3 text-2xl font-bold text-slate-800">登录 GradPath</h1>
          <p className="text-sm text-slate-500">记录你的职业轨迹，规划下一步方向</p>
        </div>

        <form
          onSubmit={onSubmit}
          className="card space-y-4"
        >
          <Field label="邮箱" required>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
            />
          </Field>
          <Field label="密码" required>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="至少 8 位"
              autoComplete="current-password"
              required
            />
          </Field>
          <Button type="submit" loading={loading} className="w-full">
            登录
          </Button>
          <p className="text-center text-sm text-slate-500">
            还没有账号？{" "}
            <Link href="/register" className="text-brand-600 hover:underline font-medium">
              立即注册
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
