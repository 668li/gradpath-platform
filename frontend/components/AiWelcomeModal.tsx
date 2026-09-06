"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bot, KeyRound, Sparkles } from "lucide-react";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/form-controls";
import { userLlmConfigApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const LS_KEY = "ai-welcome-modal-next-show";
const RE_SHOW_DAYS = 30;

/**
 * 进站弹窗：AI 模型配置说明。
 * - 仅登录用户可见；平台状态获取失败（401/网络）一律不弹，不打扰
 * - 弹出即写 30 天免打扰标记（用户叉掉网页也算"已看过"，避免每次进站都弹）
 * - 平台已内置免费模型（platform-status enabled）→ 免费体验文案
 * - 平台未配免费模型 → 自带 Key 配置引导文案
 */
export function AiWelcomeModal() {
  const [open, setOpen] = useState(false);
  const [platformEnabled, setPlatformEnabled] = useState(false);
  const [platformModel, setPlatformModel] = useState("");
  const [dailyQuota, setDailyQuota] = useState(0);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    if (!user) return;
    const next = Number(localStorage.getItem(LS_KEY) || 0);
    if (Date.now() < next) return;
    // 稍作延迟，等首屏渲染稳定后再弹
    const t = setTimeout(async () => {
      try {
        const st = await userLlmConfigApi.getPlatformStatus();
        setPlatformEnabled(st.enabled);
        setPlatformModel(st.model);
        setDailyQuota(st.daily_quota);
      } catch {
        // 状态获取失败：不弹 BYOK 引导，静默跳过
        return;
      }
      localStorage.setItem(LS_KEY, String(Date.now() + RE_SHOW_DAYS * 86_400_000));
      setOpen(true);
    }, 1200);
    return () => clearTimeout(t);
  }, [user]);

  const dismiss = () => {
    setOpen(false);
    localStorage.setItem(LS_KEY, String(Date.now() + RE_SHOW_DAYS * 86_400_000));
  };

  return (
    <Modal
      open={open}
      onClose={dismiss}
      title={platformEnabled ? "AI 免费体验" : "AI 功能配置"}
    >
      <div className="space-y-4 text-sm text-ink-600">
        {platformEnabled ? (
          <p className="flex items-start gap-2">
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-brand-500" />
            <span>
              全站 AI 功能已内置免费模型 <strong>{platformModel}</strong>
              ，无需任何配置即可使用：AI 对话、导师人设、决策分析、成长洞察等（每用户每天{" "}
              {dailyQuota} 次）。使用平台免费模型时，对话内容由平台接入的大模型服务处理。
            </span>
          </p>
        ) : (
          <p className="flex items-start gap-2">
            <KeyRound className="mt-0.5 h-4 w-4 shrink-0 text-brand-500" />
            <span>
              全站 AI 功能（AI 对话、决策分析、导师人设等）支持接入你自己的大模型
              API Key，2 分钟即可启用，费用由你的供应商承担。平台免费模型上线后将自动对所有用户开放。
            </span>
          </p>
        )}
        <div className="flex flex-wrap items-center justify-end gap-3">
          <Button variant="secondary" onClick={dismiss}>
            稍后再说
          </Button>
          {platformEnabled ? (
            <Link
              href="/chat"
              onClick={dismiss}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-brand-500 px-4 text-sm font-medium text-white hover:bg-brand-600"
            >
              <Bot className="h-4 w-4" /> 体验 AI 对话
            </Link>
          ) : (
            <Link
              href="/settings"
              onClick={dismiss}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-brand-500 px-4 text-sm font-medium text-white hover:bg-brand-600"
            >
              <KeyRound className="h-4 w-4" /> 前往配置
            </Link>
          )}
        </div>
      </div>
    </Modal>
  );
}
