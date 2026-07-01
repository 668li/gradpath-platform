# GradPath Phase 10: 前端健壮性

## 概述

Phase 10 聚焦前端代码健壮性，消除 P0 用户体验阻断问题并补全 P1 体验改进。基于对前端 12 个维度的系统性审查，分两波实施。

## Wave A: P0 关键修复

### 1. Error Boundary
- `app/error.tsx`：App Router 级错误边界，捕获渲染异常，展示降级 UI（错误消息 + 重试按钮 + 返回首页）
- `app/global-error.tsx`：根 layout 级错误边界（含 `<html>`/`<body>`）
- 两个文件均为 `"use client"` 组件，提供 `reset()` 重置错误状态

### 2. API 超时 + 重试 + JSON 保护
修改 `lib/api.ts` 的 `request<T>()`：
- AbortController 30 秒超时
- 网络错误（status=0）自动重试 1 次，1 秒延迟
- JSON.parse 包裹 try/catch
- navigator.onLine 离线检测

### 3. Token 自动刷新
- 后端新增 `POST /api/auth/refresh`：接受 refresh_token，返回新 access_token
- 前端登录时存储 refresh_token
- request<T>() 遇 401 时先尝试刷新 token 并重试，promise 锁防并发

## Wave B: P1 体验改进

### 4. 表单 Schema 校验
- 安装 zod，创建 `lib/validations.ts`
- 表单组件用 zod.safeParse() 实时校验，字段下方行内错误 + aria-invalid

### 5. Modal 无障碍
- modal.tsx 添加 role="dialog"/aria-modal/aria-labelledby
- 焦点陷阱 + 焦点恢复

### 6. Skeleton 加载
- 创建 `components/ui/skeleton.tsx`
- 列表页用 Skeleton 替换 spinner

### 7. 分享页 SEO
- share/skills/[token]/page.tsx 添加 generateMetadata + OG 标签

## 验证
- `npx tsc --noEmit` 无错误
- `npm run build` 构建成功
- E2E：触发渲染错误 → 看到降级 UI；API 超时 → 看到超时提示；token 过期 → 自动刷新
