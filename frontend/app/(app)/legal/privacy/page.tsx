import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "隐私政策 | GradPath",
  description: "GradPath 隐私政策 — 数据收集、用途、存储与用户权利",
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-paper-50">
      <article className="mx-auto max-w-3xl px-4 py-12 md:py-20 prose prose-slate">
        <Link href="/legal" className="text-sm text-brand-600 hover:underline">
          ← 返回法律文件
        </Link>
        <h1 className="font-display text-3xl md:text-4xl font-semibold text-ink-900 tracking-tight mt-4">
          隐私政策
        </h1>
        <p className="text-sm text-ink-400 mt-2">最后更新：2026 年 7 月 20 日</p>

        <section className="mt-10 space-y-4 text-ink-700 leading-relaxed">
          <p>
            GradPath（以下简称"我们"）重视用户隐私。本政策说明我们在你使用 GradPath 服务时收集、使用、存储、共享个人信息的方式，以及你所享有的权利。注册账号或使用服务即视为你已阅读并同意本政策。
          </p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">1. 我们收集的数据</h2>
          <p>为提供职业规划服务，我们会收集以下类型的数据：</p>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>
              <strong>账号信息</strong>：邮箱、昵称、加密存储的密码哈希、可选的学校 / 专业 / 毕业年份等画像字段。
            </li>
            <li>
              <strong>决策与职业数据</strong>：你在平台创建的去向决策、决策分析、职业事件、技能树、阶段复盘、职业规划方案等。
            </li>
            <li>
              <strong>AI 对话记录</strong>：你与 AI 助手的对话消息、上下文快照、AI 生成的建议与分析结果。
            </li>
            <li>
              <strong>使用行为数据</strong>：页面访问、点击事件（带 <code>data-track-id</code> 标识）、Web Vitals 性能指标、设备类型与浏览器信息。
            </li>
            <li>
              <strong>社区内容</strong>：你发布的经验帖、问答、评论、导师评价等公开内容。
            </li>
          </ul>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">2. 数据用途</h2>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>提供个性化推荐（院校推荐、岗位推荐、暗知识推送等）；</li>
            <li>调用第三方大语言模型（LLM）生成 AI 对话、决策建议与成长洞察；</li>
            <li>
              <strong>AI 训练（opt-in）</strong>：默认情况下，你的对话内容<strong>不会</strong>用于模型训练。如未来开放 opt-in 训练计划，我们会单独征求你的明示同意。
            </li>
            <li>产品改进：聚合分析使用行为与性能指标，识别功能瓶颈与体验问题；</li>
            <li>安全与风控：检测异常请求、防刷评、防滥用 LLM 配额；</li>
            <li>法律义务：在法律法规要求时披露必要信息。</li>
          </ul>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">3. 数据存储与保护</h2>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>
              <strong>数据库</strong>：用户数据存储于 PostgreSQL，密码以 bcrypt 哈希存储，绝不存明文。
            </li>
            <li>
              <strong>缓存</strong>：Redis 用于会话、限流计数与查询缓存，不存储敏感明文。
            </li>
            <li>
              <strong>传输加密</strong>：生产环境强制 HTTPS，所有 API 通信经 TLS 加密。
            </li>
            <li>
              <strong>JWT Token</strong>：access_token 短时有效（30 分钟），refresh_token 7 天，签名密钥由环境变量注入。
            </li>
            <li>
              <strong>第三方 LLM 调用</strong>：当你使用 AI 功能时，相关的对话上下文与提示词会发送给大模型服务商（如智谱 AI）以生成响应。我们仅传输必要上下文，不传输你的密码、token 等认证信息。具体处理请参阅服务商隐私政策。
            </li>
            <li>
              <strong>日志</strong>：服务日志记录请求方法、路径、状态码与耗时，<strong>不</strong>记录请求体或响应体；审计日志单独记录登录、注册等关键事件。
            </li>
            <li>
              <strong>访问控制</strong>：生产数据库与 Redis 不暴露公网，仅容器内网通信；管理员账号需显式授权。
            </li>
          </ul>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">4. 用户权利</h2>
          <p>你对自己的个人信息享有以下权利：</p>
          <ul className="list-disc pl-6 space-y-1.5">
            <li><strong>查询权</strong>：通过个人中心查看你的账号信息与决策数据；</li>
            <li><strong>更正权</strong>：在个人中心修改昵称、学校、专业等画像字段；</li>
            <li><strong>删除权</strong>：可通过"注销账号"功能发起删除请求，我们将在 15 个工作日内处理；</li>
            <li><strong>导出权</strong>：在个人中心发起数据导出，获取你的决策、事件、技能等数据的 JSON / PDF 副本；</li>
            <li><strong>注销权</strong>：注销后账号将停用，敏感数据将在备份保留期（30 天）后清除；</li>
            <li><strong>撤回同意权</strong>：可随时在设置中关闭非必要 Cookie、行为埋点与 AI 训练 opt-in；</li>
            <li><strong>投诉权</strong>：如对我们的处理不满，可向 legal@gradpath.example.com 投诉，或向有权管辖的个人信息保护机构反映。</li>
          </ul>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">5. 数据共享</h2>
          <p>除以下情形外，我们不会向第三方共享你的个人信息：</p>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>获得你的单独同意；</li>
            <li>为提供服务必须（如调用 LLM、邮件投递、CDN 加速）；</li>
            <li>法律法规要求或行政、司法机关合法要求。</li>
          </ul>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">6. 未成年人保护</h2>
          <p>
            GradPath 面向大学生与职场新人，不主动面向 14 周岁以下未成年人提供服务。如你在注册时声明未满 14 周岁，我们将拒绝创建账号。若我们发现未经监护人同意收集了未成年人个人信息，将主动删除相关数据。监护人发现其被监护人未经同意使用本服务的，可联系 legal@gradpath.example.com 申请删除。
          </p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">7. 政策更新</h2>
          <p>
            本政策可能因业务调整或法规变化而更新。重大变更时我们将通过站内通知与登录后弹窗提醒。继续使用服务即视为你接受更新后的政策。
          </p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">8. 联系我们</h2>
          <p>
            数据保护负责人邮箱：<span className="font-mono text-brand-700">legal@gradpath.example.com</span>
          </p>
        </section>
      </article>
    </main>
  );
}
