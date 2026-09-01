"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { GraduationCap } from "lucide-react";
import { authApi, setRefreshToken } from "@/lib/api";
import { registerSchema } from "@/lib/validations";
import {
  clearIdentitySnapshot,
  isIdentitySnapshotEmpty,
  loadIdentitySnapshot,
} from "@/lib/identity-snapshot";
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
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  // 免费预览带回的身份快照（W1-D3/D4）：注册即落库，登录后自动预填
  const [identityHint, setIdentityHint] = useState(false);

  useEffect(() => {
    setIdentityHint(!isIdentitySnapshotEmpty(loadIdentitySnapshot()));
  }, []);

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
    // B3 合规：未勾选条款不允许注册（前端校验，后端另有 agree_terms 校验）
    if (!agreeTerms) {
      setErrors({ agree_terms: "请阅读并同意《隐私政策》和《用户协议》后再注册" });
      toast.push("请先勾选同意条款", "error");
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      // 1. 注册（返回 UserResponse，无 token）；显式传递 agree_terms 以满足后端合规校验。
      //    免费预览带回的身份快照（W1-D3/D4）一并落库，只带已填字段。
      const snap = loadIdentitySnapshot();
      const identityBody: Record<string, string | boolean> = {};
      if (snap && !isIdentitySnapshotEmpty(snap)) {
        if (snap.fresh_status) identityBody.fresh_status = snap.fresh_status;
        if (snap.party_status) identityBody.party_status = snap.party_status;
        if (snap.education) identityBody.education = snap.education;
        if (snap.gender) identityBody.gender = snap.gender;
        if (snap.has_grassroots !== null && snap.has_grassroots !== undefined) {
          identityBody.has_grassroots = snap.has_grassroots;
        }
      }
      await authApi.register({ name, email, password, agree_terms: true, ...identityBody });
      clearIdentitySnapshot();
      // 2. 自动登录获取 token
      const tokenRes = await authApi.login({ email, password });
      // 修复: REACT-AUTH-001 注册流程需与登录流程一致保存 refresh_token,
      // 否则注册会话无法在 access_token 过期后自动刷新, 导致用户被踢出
      setToken(tokenRes.access_token);
      setRefreshToken(tokenRes.refresh_token);
      const user = await fetchUser();
      if (!user) {
        toast.push("注册成功但登录失败，请手动登录", "error");
        setLoading(false);
        return;
      }
      toast.push("注册成功，欢迎加入 GradPath", "success");
      router.replace("/dashboard");
    } catch (err) {
      toast.push("注册失败,请稍后重试或检查邮箱格式", "error");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 to-ink-100 px-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 text-white shadow-lg">
            <GraduationCap className="h-7 w-7" />
          </div>
          <h1 className="mt-3 text-2xl font-bold text-ink-800">注册 GradPath</h1>
          <p className="text-sm text-ink-500">开启你的职业轨迹记录之旅</p>
        </div>

        <form onSubmit={onSubmit} noValidate className="card space-y-4">
          {identityHint && (
            <p className="rounded-md bg-brand-50 px-3 py-2 text-xs text-brand-700">
              已带上你在免费预览里填过的报考身份，注册后自动保存，无需重复填写。
            </p>
          )}
          <Field label="昵称" required>
            <Input
              name="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="你的昵称"
              aria-invalid={!!errors.name}
              data-testid="register-name-input"
              required
            />
            <FieldError message={errors.name} />
          </Field>
          <Field label="邮箱" required>
            <Input
              type="email"
              name="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              aria-invalid={!!errors.email}
              data-testid="register-email-input"
              required
            />
            <FieldError message={errors.email} />
          </Field>
          <Field label="密码" required hint="至少 8 位">
            <Input
              type="password"
              name="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="至少 8 位"
              autoComplete="new-password"
              aria-invalid={!!errors.password}
              data-testid="register-password-input"
              required
            />
            <FieldError message={errors.password} />
          </Field>
          {/* B3 合规：必须勾选同意条款才能注册 */}
          <div className="space-y-1">
            <label className="flex items-start gap-2 text-sm text-ink-600 cursor-pointer">
              <input
                type="checkbox"
                name="agree_terms"
                checked={agreeTerms}
                onChange={(e) => {
                  setAgreeTerms(e.target.checked);
                  if (e.target.checked && errors.agree_terms) {
                    setErrors((prev) => {
                      const next = { ...prev };
                      delete next.agree_terms;
                      return next;
                    });
                  }
                }}
                aria-invalid={!!errors.agree_terms}
                data-testid="agree-terms-checkbox"
                className="mt-0.5 h-4 w-4 rounded border-ink-300 text-brand-600 focus:ring-brand-500"
              />
              <span className="leading-relaxed">
                我已阅读并同意
                <Link
                  href="/legal/privacy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand-600 hover:underline font-medium"
                >
                  《隐私政策》
                </Link>
                和
                <Link
                  href="/legal/terms"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand-600 hover:underline font-medium"
                >
                  《用户协议》
                </Link>
              </span>
            </label>
            <FieldError message={errors.agree_terms} />
          </div>
          <Button type="submit" loading={loading} className="w-full" data-testid="register-submit-button">
            注册并登录
          </Button>
          <p className="text-center text-sm text-ink-500">
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
