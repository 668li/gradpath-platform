import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Cookie 政策 | GradPath",
  description: "GradPath Cookie 与本地存储使用说明",
};

export default function CookiePage() {
  return (
    <main className="min-h-screen bg-paper-50">
      <article className="mx-auto max-w-3xl px-4 py-12 md:py-20 prose prose-slate">
        <Link href="/legal" className="text-sm text-brand-600 hover:underline">
          ← 返回法律文件
        </Link>
        <h1 className="font-display text-3xl md:text-4xl font-semibold text-ink-900 tracking-tight mt-4">
          Cookie 政策
        </h1>
        <p className="text-sm text-ink-400 mt-2">最后更新：2026 年 7 月 20 日</p>

        <section className="mt-10 space-y-4 text-ink-700 leading-relaxed">
          <p>
            本政策说明 GradPath 如何使用 Cookie 与浏览器本地存储（localStorage）。Cookie 是网站存储在你浏览器中的小型文本文件；localStorage 是浏览器提供的本地键值存储。两者均不会执行代码，也不会主动收集你设备上的其他信息。
          </p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">1. 我们使用的 Cookie / 本地存储</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm border border-paper-300 rounded-lg">
              <thead className="bg-paper-100 text-ink-700">
                <tr>
                  <th className="text-left p-3 font-medium">名称</th>
                  <th className="text-left p-3 font-medium">类型</th>
                  <th className="text-left p-3 font-medium">用途</th>
                  <th className="text-left p-3 font-medium">保留期</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-200">
                <tr>
                  <td className="p-3 font-mono">gradpath_token</td>
                  <td className="p-3">Cookie</td>
                  <td className="p-3">保存 access_token 副本，供 Edge Middleware 在服务端做路由守卫（区分登录 / 未登录页面）</td>
                  <td className="p-3">30 天</td>
                </tr>
                <tr>
                  <td className="p-3 font-mono">gradpath_access_token</td>
                  <td className="p-3">localStorage</td>
                  <td className="p-3">客户端 API 请求时携带的 access_token，刷新页面后保持登录态</td>
                  <td className="p-3">随 token 过期清除</td>
                </tr>
                <tr>
                  <td className="p-3 font-mono">gradpath_refresh_token</td>
                  <td className="p-3">localStorage</td>
                  <td className="p-3">access_token 过期后用于换取新 token，避免频繁登录</td>
                  <td className="p-3">7 天</td>
                </tr>
                <tr>
                  <td className="p-3 font-mono">sessionId</td>
                  <td className="p-3">内存 / 埋点</td>
                  <td className="p-3">埋点系统生成的会话 ID，用于聚合用户行为</td>
                  <td className="p-3">关闭页面后失效</td>
                </tr>
              </tbody>
            </table>
          </div>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">2. Cookie 分类</h2>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>
              <strong>必要 Cookie</strong>：用于认证与路由守卫，缺少则无法登录使用服务。无法通过设置关闭。
            </li>
            <li>
              <strong>偏好 / 功能 Cookie</strong>：保存主题、语言等用户偏好（如有）。
            </li>
            <li>
              <strong>分析 Cookie</strong>：聚合分析使用行为，用于产品改进。可在设置中关闭。
            </li>
          </ul>
          <p>GradPath <strong>不</strong>使用第三方广告 Cookie，<strong>不</strong>跨站追踪用户。</p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">3. 如何管理 Cookie</h2>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>浏览器设置：大多数浏览器允许你查看、拦截或删除 Cookie。可在浏览器隐私设置中调整。</li>
            <li>退出登录：在个人中心点击"退出登录"会清除 localStorage 中的 token，但 Cookie 会在 30 天内自动过期。</li>
            <li>注销账号：注销后所有相关数据将被清除。</li>
          </ul>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">4. 第三方服务</h2>
          <p>
            我们调用的第三方大语言模型（LLM）服务在请求过程中可能记录必要的请求元数据，但不通过我们的页面设置 Cookie。Sentry（错误监控）会设置匿名追踪 Cookie，可在浏览器设置中拦截。
          </p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">5. 政策更新</h2>
          <p>
            如新增 Cookie 类型或调整用途，我们将更新本政策并通过站内通知提醒。
          </p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">6. 联系方式</h2>
          <p>
            邮箱：<span className="font-mono text-brand-700">legal@gradpath.example.com</span>
          </p>
        </section>
      </article>
    </main>
  );
}
