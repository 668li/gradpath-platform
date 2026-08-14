"use client";

import { useCallback, useEffect, useState } from "react";
import { Ban, RefreshCw, ShieldCheck, Search, UserCheck } from "lucide-react";
import {
  Badge,
  Button,
  Field,
  Input,
  Select,
  Textarea,
} from "@/components/ui/form-controls";
import { Modal } from "@/components/ui/modal";
import { Pagination } from "@/components/ui/pagination";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { adminApi, type AdminUser } from "@/lib/api/admin";

const PAGE_SIZE = 20;

function formatTime(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate(),
  ).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(
    d.getMinutes(),
  ).padStart(2, "0")}`;
}

export default function AdminUsersPage() {
  const toast = useToast();

  const [items, setItems] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [actingId, setActingId] = useState<string | null>(null);

  // 封禁弹窗状态
  const [banTarget, setBanTarget] = useState<AdminUser | null>(null);
  const [banReason, setBanReason] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.listUsers({
        keyword: keyword.trim() || undefined,
        status: statusFilter || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载用户列表失败", "error");
    } finally {
      setLoading(false);
    }
  }, [page, keyword, statusFilter, toast]);

  useEffect(() => {
    setPage(1);
  }, [keyword, statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const handleBan = async () => {
    if (!banTarget) return;
    if (!banReason.trim()) {
      toast.push("封禁原因必填", "error");
      return;
    }
    setActingId(banTarget.id);
    try {
      await adminApi.banUser(banTarget.id, banReason.trim());
      toast.push("用户已封禁（立即生效）", "success");
      setBanTarget(null);
      setBanReason("");
      load();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "封禁失败", "error");
    } finally {
      setActingId(null);
    }
  };

  const handleUnban = async (user: AdminUser) => {
    setActingId(user.id);
    try {
      await adminApi.unbanUser(user.id);
      toast.push("用户已解封", "success");
      load();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "解封失败", "error");
    } finally {
      setActingId(null);
    }
  };

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-xl font-semibold text-ink-800 tracking-tight">
            用户管理
          </h1>
          <p className="mt-0.5 text-sm text-ink-500">
            搜索用户、封禁违规账号或解封恢复（封禁即时生效）
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={load}>
          <RefreshCw className="h-3.5 w-3.5" />
          刷新
        </Button>
      </div>

      {/* 搜索 + 筛选 */}
      <form
        className="flex flex-wrap gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setPage(1);
          load();
        }}
      >
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
          <Input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="搜索邮箱 / 昵称 / 姓名"
            className="w-64 pl-9"
          />
        </div>
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="w-36"
          aria-label="按账户状态筛选"
        >
          <option value="">全部状态</option>
          <option value="active">正常</option>
          <option value="banned">已封禁</option>
        </Select>
        <Button type="submit" variant="secondary" size="md">
          搜索
        </Button>
      </form>

      {loading ? (
        <LoadingState text="加载中…" />
      ) : items.length === 0 ? (
        <EmptyState
          title="未找到用户"
          description={keyword ? "试试其他关键词" : "暂无用户"}
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-paper-300 bg-white shadow-sm">
          <ul className="divide-y divide-paper-200">
            {items.map((user) => {
              const banned = user.status === "banned";
              return (
                <li key={user.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-500/15 text-sm font-semibold text-brand-600">
                      {(user.nickname ?? user.name)?.[0] ?? "U"}
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate text-sm font-medium text-ink-800">
                          {user.nickname ?? user.name}
                        </p>
                        {user.is_admin && <Badge color="purple">管理员</Badge>}
                        <Badge color={banned ? "red" : "green"}>
                          {banned ? "已封禁" : "正常"}
                        </Badge>
                      </div>
                      <p className="mt-0.5 truncate text-xs text-ink-400">
                        {user.email}
                        {user.school ? ` ｜ ${user.school}` : ""}
                        {user.major ? ` · ${user.major}` : ""}
                        {user.graduation_year ? `（${user.graduation_year} 届）` : ""}
                      </p>
                      {banned && user.ban_reason && (
                        <p className="mt-0.5 text-xs text-red-500">
                          封禁原因：{user.ban_reason}
                          {user.banned_at ? `（${formatTime(user.banned_at)}）` : ""}
                        </p>
                      )}
                      <p className="mt-0.5 text-xs text-ink-300">
                        注册于 {formatTime(user.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {banned ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        loading={actingId === user.id}
                        onClick={() => handleUnban(user)}
                      >
                        <UserCheck className="h-3.5 w-3.5" />
                        解封
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="danger"
                        disabled={user.is_admin}
                        loading={actingId === user.id}
                        onClick={() => {
                          setBanTarget(user);
                          setBanReason("");
                        }}
                        title={user.is_admin ? "不能封禁管理员" : undefined}
                      >
                        <Ban className="h-3.5 w-3.5" />
                        封禁
                      </Button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="border-t border-paper-200 px-5 py-3">
            <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
          </div>
        </div>
      )}

      {/* 封禁弹窗 */}
      <Modal
        open={!!banTarget}
        onClose={() => setBanTarget(null)}
        title="封禁用户"
      >
        {banTarget && (
          <div className="space-y-4">
            <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
              将封禁 <b>{banTarget.nickname ?? banTarget.name}</b>（{banTarget.email}）。
              封禁后该用户将无法登录，其历史内容保留但处于下架状态。
            </p>
            <Field label="封禁原因" hint="必填，会展示给被封禁用户" required>
              <Textarea
                rows={3}
                value={banReason}
                onChange={(e) => setBanReason(e.target.value)}
                placeholder="如：发布违规内容、人身攻击、广告骚扰…"
                maxLength={500}
              />
            </Field>
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="ghost" onClick={() => setBanTarget(null)}>
                取消
              </Button>
              <Button
                variant="danger"
                loading={actingId === banTarget.id}
                onClick={handleBan}
              >
                <ShieldCheck className="h-4 w-4" />
                确认封禁
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
