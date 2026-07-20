import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "用户协议 | GradPath",
  description: "GradPath 用户协议 — 服务条款、用户义务与争议解决",
};

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-paper-50">
      <article className="mx-auto max-w-3xl px-4 py-12 md:py-20 prose prose-slate">
        <Link href="/legal" className="text-sm text-brand-600 hover:underline">
          ← 返回法律文件
        </Link>
        <h1 className="font-display text-3xl md:text-4xl font-semibold text-ink-900 tracking-tight mt-4">
          用户协议
        </h1>
        <p className="text-sm text-ink-400 mt-2">最后更新：2026 年 7 月 20 日</p>

        <section className="mt-10 space-y-4 text-ink-700 leading-relaxed">
          <p>本协议是你（以下简称"用户"）与 GradPath（以下简称"我们"）之间就使用 GradPath 平台服务所订立的协议。注册账号或使用服务即视为你已阅读并同意本协议。</p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">1. 服务说明</h2>
          <p>
            GradPath 提供职业轨迹记录、去向决策分析、考研 / 考公 / 就业情报、AI 助手对话、社区交流等功能。具体功能可能随产品迭代调整，我们保留新增、修改、停止某项功能的权利。
          </p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">2. 账号注册与使用</h2>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>用户需使用真实邮箱注册，并对账号与密码的安全负责；</li>
            <li>禁止将账号出售、出借或以其他方式转让给第三方；</li>
            <li>如发现账号被盗用，应立即通过设置页修改密码或联系客服；</li>
            <li>注册时需勾选"我已阅读并同意《隐私政策》《用户协议》"，未同意者无法完成注册。</li>
          </ul>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">3. 用户行为规范</h2>
          <p>用户在使用本服务时，应遵守中华人民共和国法律法规，不得利用本服务从事以下行为：</p>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>发布违法、淫秽、暴力、歧视或侵害他人合法权益的内容；</li>
            <li>冒充他人或虚构身份；</li>
            <li>对导师、公司、院校进行恶意诽谤或不实评价；</li>
            <li>刷评、灌水、自动化批量注册、滥用 LLM 配额或攻击服务接口；</li>
            <li>反向工程、爬取非公开数据或绕过限流与认证；</li>
            <li>以任何方式干扰服务正常运行或侵害第三方权益。</li>
          </ul>
          <p>违反上述规定者，我们有权采取内容删除、账号封禁、限制功能等措施，并保留追究法律责任的权利。</p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">4. 内容授权</h2>
          <p>
            用户在 GradPath 发布的经验帖、问答、评论、导师评价等内容，著作权归用户所有。用户在发布时即授予 GradPath 一项非排他、免费、全球范围内、可转授权的许可，用于在本服务内展示、推荐、搜索、聚合分析与改进推荐算法。我们不会将你的内容授权给第三方用于商业推广，除非获得你的单独同意。
          </p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">5. AI 生成内容声明</h2>
          <p>
            GradPath 的 AI 助手、决策建议、成长洞察等功能由第三方大语言模型提供。AI 生成内容可能存在错误、偏见或过时信息，<strong>不构成</strong>专业职业咨询、法律意见或投资建议。用户应自行判断并承担依据 AI 内容做出决策的风险。
          </p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">6. 知识产权</h2>
          <p>
            本平台的代码、设计、文案、数据可视化、院校情报数据库等知识产权归 GradPath 或其权利人所有，未经书面授权不得复制、转载、爬取或商用。爬虫管理后台仅用于内部数据采集，不对外开放。
          </p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">7. 服务变更与终止</h2>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>我们可能因业务调整、维护、不可抗力等原因暂停或停止服务，并提前公告；</li>
            <li>用户可随时通过"注销账号"功能终止账号；</li>
            <li>账号注销后，备份数据将在 30 天保留期内清除；</li>
            <li>违反本协议的账号我们有权单方终止服务。</li>
          </ul>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">8. 免责声明</h2>
          <p>
            在法律允许的范围内，GradPath 不对以下事项承担责任：因网络中断、服务器故障、第三方服务（LLM、CDN）不可用导致的损失；用户依据 AI 内容或社区评价做出的决策损失；用户自行泄露密码导致的账号损失。
          </p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">9. 争议解决</h2>
          <p>
            本协议适用中华人民共和国法律。因本协议或本服务产生的争议，双方应友好协商解决；协商不成的，任何一方可向我们注册地有管辖权的人民法院提起诉讼。
          </p>

          <h2 className="font-display text-xl font-semibold text-ink-900 mt-8">10. 联系方式</h2>
          <p>
            邮箱：<span className="font-mono text-brand-700">legal@gradpath.example.com</span>
          </p>
        </section>
      </article>
    </main>
  );
}
