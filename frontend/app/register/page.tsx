"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { GraduationCap } from "lucide-react";
import { authApi } from "@/lib/api";
import { registerSchema } from "@/lib/validations";
import { useAuthStore } from "@/stores/auth";
import { useToast } from "@/components/ui/toast";
import { Button, Field, FieldError, Input } from "@/components/ui/form-controls";

export default function RegisterPage() {
  const router = useRouter();
  const toast = useToast();
  const setToken = useAuthStore((s) => s.setToken);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const result = registerSchema.safeParse({ name, email, password });
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
      // 1. 注册（返回 UserResponse，无 token）
      await authApi.register({ name, email, password });
      // 2. 自动登录获取 token
      const tokenRes = await authApi.login({ email, password });
      setToken(tokenRes.access_token);
      const user = await fetchUser();
      if (!user) {
        toast.push("注册成功但登录失败，请手动登录", "error");
        setLoading(false);
        return;
      }
      toast.push("注册成功，欢迎加入 GradPath", "success");
      router.replace("/dashboard");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "注册失败", "error");
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
          <h1 className="mt-3 text-2xl font-bold text-slate-800">注册 GradPath</h1>
          <p className="text-sm text-slate-500">开启你的职业轨迹记录之旅</p>
        </div>

        <form onSubmit={onSubmit} className="card space-y-4">
          <Field label="昵称" required>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="你的昵称"
              aria-invalid={!!errors.name}
              required
            />
            <FieldError message={errors.name} />
          </Field>
          <Field label="邮箱" required>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              aria-invalid={!!errors.email}
              required
            />
            <FieldError message={errors.email} />
          </Field>
          <Field label="密码" required hint="至少 8 位">
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="至少 8 位"
              autoComplete="new-password"
              aria-invalid={!!errors.password}
              required
            />
            <FieldError message={errors.password} />
          </Field>
          <Button type="submit" loading={loading} className="w-full">
            注册并登录
          </Button>
          <p className="text-center text-sm text-slate-500">
            已有账号？{" "}
            <Link href="/login" className="text-brand-600 hover:underline font-medium">
              去登录
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
