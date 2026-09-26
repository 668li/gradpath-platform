import Link from "next/link";

// 2026-09-26 考公线退役：本页随线隐藏（见 docs/数据供给总纲-爬取跟随决策-2026-09-26.md）。
// force-dynamic + 明确退役说明页（R-07）：静态化会让旧壳被 ISR 缓存钉死一年，必须每次请求动态渲染。
export const dynamic = "force-dynamic";

export default function RetiredPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-20 text-center">
      <h1 className="text-2xl font-bold text-ink-800">该功能已随考公路退役</h1>
      <p className="mt-3 text-sm leading-relaxed text-ink-500">
        考公线已于 2026-09 退役，此页面不再提供内容。考研与就业两条路的决策伴随
        （决策引擎、时间线、情报）请回工作台继续使用。
      </p>
      <Link
        href="/dashboard"
        className="mt-6 inline-block rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
      >
        返回工作台
      </Link>
    </div>
  );
}
