// 报考身份包快照（W1-D3/D4）— 免费预览 → 注册/登录带回的桥梁。
//
// 预览表单每次判定时把身份字段写入 localStorage；
// 注册页拼进 RegisterRequest，登录页登录成功后 updateMe 保存，随后清空。
// 用 localStorage 而非 query string：不把身份暴露在 URL 里，同浏览器注册天然可达。

import type { IdentityPackage } from "@/types";

const SNAPSHOT_KEY = "gradpath_identity_snapshot";

export function saveIdentitySnapshot(identity: IdentityPackage): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(identity));
  } catch {
    // 存储不可用（隐私模式等）时静默跳过，不影响预览主流程
  }
}

export function loadIdentitySnapshot(): IdentityPackage | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(SNAPSHOT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as IdentityPackage;
    if (typeof parsed !== "object" || parsed === null) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearIdentitySnapshot(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(SNAPSHOT_KEY);
  } catch {
    // 同上，静默跳过
  }
}

/** 快照是否为空（所有身份字段都未填）— 空快照不值得带回。 */
export function isIdentitySnapshotEmpty(identity: IdentityPackage | null): boolean {
  if (!identity) return true;
  // has_grassroots 为 false 也算已填（用户明确选了「不满足」）
  const hasGrassroots = (identity.has_grassroots ?? null) !== null;
  return !(
    identity.fresh_status ||
    identity.party_status ||
    identity.education ||
    identity.gender ||
    hasGrassroots
  );
}
