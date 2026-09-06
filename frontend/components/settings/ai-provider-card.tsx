"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Bot,
  CheckCircle2,
  ExternalLink,
  KeyRound,
  Loader2,
  Save,
  Sparkles,
  Trash2,
  XCircle,
} from "lucide-react";
import { Button, Field, Input, Select } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { userLlmConfigApi } from "@/lib/api";
import type {
  PlatformLlmStatus,
  UserLlmConfigResponse,
} from "@/lib/api/user-llm-config";
import { cn } from "@/lib/utils";

/** OpenAI 兼容供应商标识与默认端点 */
const PROVIDERS: { value: string; label: string; baseUrl: string; model: string; keyUrl?: string }[] = [
  { value: "zhipu", label: "智谱 GLM", baseUrl: "https://open.bigmodel.cn/api/paas/v4/", model: "glm-4.7-flash", keyUrl: "https://open.bigmodel.cn/usercenter/apikeys" },
  { value: "deepseek", label: "DeepSeek", baseUrl: "https://api.deepseek.com/v1", model: "deepseek-chat", keyUrl: "https://platform.deepseek.com/api_keys" },
  { value: "moonshot", label: "月之暗面 Kimi", baseUrl: "https://api.moonshot.cn/v1", model: "moonshot-v1-8k", keyUrl: "https://platform.moonshot.cn/console/api-keys" },
  { value: "qwen", label: "阿里通义千问", baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus", keyUrl: "https://bailian.console.aliyun.com/?apiKey=1#/api-key" },
  { value: "openai", label: "OpenAI", baseUrl: "https://api.openai.com/v1", model: "gpt-4o-mini", keyUrl: "https://platform.openai.com/api-keys" },
  { value: "custom", label: "自定义（OpenAI 兼容）", baseUrl: "", model: "" },
];

/** 平台免费模型同款供应商作为自带 Key 的默认预选 */
const DEFAULT_PROVIDER = PROVIDERS.find((p) => p.value === "qwen") ?? PROVIDERS[0];

export function AiProviderCard() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [saved, setSaved] = useState<UserLlmConfigResponse | null>(null);
  const [platform, setPlatform] = useState<PlatformLlmStatus | null>(null);
  const [provider, setProvider] = useState(DEFAULT_PROVIDER.value);
  const [baseUrl, setBaseUrl] = useState(DEFAULT_PROVIDER.baseUrl);
  const [model, setModel] = useState(DEFAULT_PROVIDER.model);
  const [apiKey, setApiKey] = useState("");
  const [verifyResult, setVerifyResult] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    userLlmConfigApi
      .getConfig()
      .then((cfg) => {
        if (cfg) {
          setSaved(cfg);
          setProvider(cfg.provider);
          setBaseUrl(cfg.base_url);
          setModel(cfg.model);
        }
      })
      .catch(() => {});
    userLlmConfigApi
      .getPlatformStatus()
      .then(setPlatform)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleProviderChange = (value: string) => {
    setProvider(value);
    const preset = PROVIDERS.find((p) => p.value === value);
    if (preset && preset.baseUrl) {
      setBaseUrl(preset.baseUrl);
      setModel(preset.model);
    }
  };

  const buildBody = () => ({
    provider,
    base_url: baseUrl.trim(),
    model: model.trim(),
    api_key: apiKey.trim(),
    is_enabled: true,
  });

  const handleVerify = async () => {
    setVerifying(true);
    setVerifyResult(null);
    try {
      const res = await userLlmConfigApi.verifyConfig(buildBody());
      setVerifyResult({ ok: res.ok, message: res.latency_ms ? `${res.message}（${res.latency_ms}ms）` : res.message });
    } catch (e) {
      const err = e as { message?: string };
      setVerifyResult({ ok: false, message: err.message || "验证请求失败" });
    } finally {
      setVerifying(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const cfg = await userLlmConfigApi.saveConfig(buildBody());
      setSaved(cfg);
      setApiKey(""); // 保存后清空明文输入
      setVerifyResult(null);
      toast.success("AI 服务配置已保存");
    } catch (e) {
      const err = e as { message?: string };
      toast.error(err.message || "保存失败，请检查填写内容");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("确认删除已保存的 AI 服务配置？删除后将回退平台免费模型（平台未配置时 AI 对话不可用）。")) return;
    setDeleting(true);
    try {
      await userLlmConfigApi.deleteConfig();
      setSaved(null);
      setApiKey("");
      setVerifyResult(null);
      toast.success("已删除 AI 服务配置");
    } catch {
      toast.error("删除失败");
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <section className="card p-6">
        <div className="flex items-center gap-2 text-sm text-ink-400">
          <Loader2 className="h-4 w-4 animate-spin" /> 加载 AI 服务配置…
        </div>
      </section>
    );
  }

  return (
    <section className="card p-6 space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 font-display text-lg font-semibold text-ink-800">
            <KeyRound className="h-5 w-5 text-brand-500" /> AI 对话服务
          </h2>
          <p className="mt-1 text-sm text-ink-500">
            {platform?.enabled ? (
              <>
                平台已内置免费模型，全站 AI 功能开箱即用（每用户每天{" "}
                {platform.daily_quota} 次）。也可填入自己的 API Key 切换更强模型。
              </>
            ) : (
              <>
                填入你自己的大模型 API Key 即可启用全站 AI 功能：
                <Link href="/chat" className="text-brand-600 hover:underline">AI 对话</Link>
                、导师人设、决策分析、研招情报等。Key 加密存储，费用由你的供应商账户承担。
              </>
            )}
          </p>
        </div>
        {saved && saved.is_enabled && (
          <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-green-50 px-2.5 py-1 text-xs font-medium text-green-600">
            <CheckCircle2 className="h-3.5 w-3.5" />
            已启用 {saved.api_key_masked}
          </span>
        )}
      </div>

      {platform?.enabled && (
        <div className="flex items-start gap-2 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-xs text-green-700">
          <Sparkles className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            免费体验中：平台默认模型 <strong>{platform.model}</strong>
            （平台内置免费款，无需任何配置）。使用平台免费模型时，对话内容由平台接入的大模型服务处理；自带
            Key 后则由你自己的供应商处理。
          </span>
        </div>
      )}

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="供应商">
          <Select value={provider} onChange={(e) => handleProviderChange(e.target.value)}>
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="模型名称" hint="如 glm-4-flash / deepseek-chat / gpt-4o-mini">
          <Input value={model} onChange={(e) => setModel(e.target.value)} maxLength={100} />
        </Field>
      </div>

      <Field label="API 地址（Base URL）" hint="OpenAI 兼容接口根地址，一般以 /v1 或 /v4/ 结尾">
        <Input
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder={DEFAULT_PROVIDER.baseUrl}
          maxLength={500}
        />
      </Field>

      <Field
        label="API Key"
        hint={saved ? "留空表示沿用已保存的 Key（**** 掩码不可见）" : "在供应商控制台创建，仅用于你的对话请求"}
      >
        <Input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={saved ? `已保存 ${saved.api_key_masked}` : "sk-…"}
          maxLength={500}
          autoComplete="off"
        />
      </Field>

      {verifyResult && (
        <p
          className={cn(
            "flex items-center gap-1.5 text-xs",
            verifyResult.ok ? "text-green-600" : "text-red-500",
          )}
        >
          {verifyResult.ok ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
          {verifyResult.message}
        </p>
      )}

      <div className="flex flex-wrap justify-end gap-3">
        {saved && (
          <Button variant="secondary" loading={deleting} onClick={handleDelete}>
            <Trash2 className="h-4 w-4" /> 删除配置
          </Button>
        )}
        <Button variant="secondary" loading={verifying} onClick={handleVerify}>
          测试连接
        </Button>
        <Button onClick={handleSave} loading={saving}>
          <Save className="h-4 w-4" /> 保存配置
        </Button>
      </div>

      <p className="flex items-center gap-1 text-xs text-ink-400">
        <Bot className="h-3.5 w-3.5" />
        需要 OpenAI 兼容接口（绝大多数国内外供应商都支持）。
        {PROVIDERS.find((p) => p.value === provider)?.keyUrl ? (
          <a
            href={PROVIDERS.find((p) => p.value === provider)!.keyUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-0.5 text-brand-500 hover:underline"
          >
            {PROVIDERS.find((p) => p.value === provider)!.label} Key 获取 <ExternalLink className="h-3 w-3" />
          </a>
        ) : (
          <span>选中供应商后此处显示其 Key 获取入口</span>
        )}
      </p>
    </section>
  );
}
