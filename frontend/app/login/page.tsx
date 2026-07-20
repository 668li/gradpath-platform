"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { GraduationCap } from "lucide-react";
import { authApi, setRefreshToken } from "@/lib/api";
import { loginSchema } from "@/lib/validations";
import { useAuthStore } from "@/stores/auth";
import { useToast } from "@/components/ui/toast";
import { Button, Field, FieldError, Input } from "@/components/ui/form-controls";

export default function LoginPage() {
  const router = useRouter();
  const toast = useToast();
  const setToken = useAuthStore((s) => s.setToken);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const result = loginSchema.safeParse({ email, password });
    if (!result.success) {
      const fieldErrors: Record<string, string> = {};
      Object.entries(result.error.flatten().fieldErrors).forEach(
        ([key, msgs]) => {
          if (msgs && msgs.length > 0) fieldErrors[key] = msgs[0];
        },
      );
      setErrors(fieldErrors);
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      const tokenRes = await authApi.login({ email, password });
      setToken(tokenRes.access_token);
      setRefreshToken(tokenRes.refresh_token);
      const user = await fetchUser();
      if (!user) {
        toast.push("登录成功但获取用户信息失败", "error");
        setLoading(false);
        return;
      }
      toast.push("登录成功", "success");
      router.replace("/dashboard");
    } catch (err) {
      toast.push("登录失败,请检查邮箱和密码是否正确", "error");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper-100 px-4">
      <div className="w-full max-w-md animate-slide-up">
        <div className="flex flex-col items-center mb-8">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-brand">
            <GraduationCap className="h-7 w-7" strokeWidth={2.2} />
          </div>
          <h1 className="mt-4 font-display text-3xl font-semibold text-ink-800 tracking-tight">
            登录 GradPath
          </h1>
          <p className="mt-1.5 text-sm text-ink-500">记录你的职业轨迹，规划下一步方向</p>
        </div>

        <form
          onSubmit={onSubmit}
          className="card space-y-5"
        >
          <Field label="邮箱" required>
            <Input
              type="email"
              name="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              aria-invalid={!!errors.email}
              data-testid="login-email-input"
              required
            />
            <FieldError message={errors.email} />
          </Field>
          <Field label="密码" required>
            <Input
              type="password"
              name="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="至少 8 位"
              autoComplete="current-password"
              aria-invalid={!!errors.password}
              data-testid="login-password-input"
              required
            />
            <FieldError message={errors.password} />
          </Field>
          <Button type="submit" loading={loading} className="w-full" data-testid="login-submit-button">
            登录
          </Button>
          <p className="text-center text-sm text-ink-400">
            还没有账号？{" "}
            <Link href="/register" className="text-brand-600 hover:text-brand-700 hover:underline font-medium transition-colors">
              立即注册
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
