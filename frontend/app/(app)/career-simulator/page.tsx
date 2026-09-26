import Link from "next/link";

// 2026-09-26 用户拍板：考公线整体退役 / 模拟器整站隐藏（底座数据退役，见 docs/数据供给总纲）。
// 文件保留以便恢复，入口已全部摘除。
// force-dynamic + 明确退役说明页（R-07）：静态化会让旧壳被 ISR 缓存钉死一年，必须每次请求动态渲染。
export const dynamic = "force-dynamic";

export default function RetiredPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-20 text-center">
      <h1 className="text-2xl font-bold text-ink-800">路径模拟器已下线</h1>
      <p className="mt-3 text-sm leading-relaxed text-ink-500">
        路径模拟器底座数据已随考公路退役下线，此页面不再提供内容。
        考研与就业两条路的决策伴随请回工作台继续使用。
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
