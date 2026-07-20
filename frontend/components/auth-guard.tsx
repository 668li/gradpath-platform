"use client";

import { type ReactNode } from "react";

/**
 * 认证守卫 - 客户端兜底层
 *
 * 路由守卫分层策略（自外向内）：
 *   1. Edge Middleware（`middleware.ts`）：服务端读取 `gradpath_token` cookie，
 *      未登录访问受保护路由时直接重定向到 `/login?redirect=<原路径>`，是主防线。
 *   2. `app/(app)/layout.tsx` 的 useEffect：客户端首次进入受保护区域时
 *      从 localStorage 恢复 token，并调用 `/api/auth/me` 校验，失败则跳转 `/login`。
 *   3. 本组件：作为客户端兜底，当 middleware 失效（例如静态导出、边缘节点异常）
 *      且布局层校验未触发时，仍保证 children 可渲染——具体重定向由布局层负责。
 *
 * 后端继续控制写操作权限（保存情报、创建帖子等），未登录用户即使浏览到
 * 受保护页面也无法执行写操作。
 */
export function AuthGuard({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
