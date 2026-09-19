/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // P2 功能合并：被折叠功能的旧路由 302 到新家（拍板见 docs/P2功能合并任务书-2026-09-06.md）
  // 链接不 404 是硬要求；permanent:false 保持 302，将来恢复入口无需浏览器缓存清理
  async redirects() {
    return [
      { source: "/career", destination: "/dashboard", permanent: false },
      { source: "/life-wheel", destination: "/self-discovery", permanent: false },
      { source: "/insights", destination: "/achievements", permanent: false },
      { source: "/decision-lab", destination: "/decision-center", permanent: false },
      { source: "/decision-engine", destination: "/decision-center", permanent: false },
      { source: "/war-room", destination: "/decision-center", permanent: false },
      { source: "/decisions", destination: "/decision-center", permanent: false },
      { source: "/plans", destination: "/study-plans", permanent: false },
      // 考研工具箱瘦身（docs/考研工具箱瘦身规格-2026-09-15.md W5）：已下线页面 302 兜底到 /kaoyan
      { source: "/kaoyan/predict", destination: "/kaoyan", permanent: false },
      { source: "/kaoyan/compare", destination: "/kaoyan", permanent: false },
      { source: "/kaoyan/strategy", destination: "/kaoyan", permanent: false },
      { source: "/kaoyan/schools", destination: "/kaoyan", permanent: false },
      { source: "/kaoyan/schools/:path*", destination: "/kaoyan", permanent: false },
      // 注意：/kaoyan/news 是 W8 新建的资讯中心，不得重定向（否则整页被 302 吃掉）
      { source: "/learning-resources", destination: "/study-plans", permanent: false },
      { source: "/civil-service/positions", destination: "/civil-service", permanent: false },
      // 09-12 战略转向：职位检索与免费可报性预览整体下架（计划书红线 1/2），页面薄壳只是兜底，
      // 公开页 /preview 会被静态预渲染吃掉页面级 redirect()，路由层 302 才是权威拦截
      { source: "/civil-service/province-positions", destination: "/civil-service", permanent: false },
      { source: "/civil-service/positions/compare", destination: "/civil-service", permanent: false },
      { source: "/preview", destination: "/", permanent: false },
      { source: "/failure-cases", destination: "/employment?tab=interview", permanent: false },
    ];
  },
  // 服务器构建提速：lint 已由 CI(github actions) 与本地 npm run lint 覆盖，
  // 2 核云服务器构建时重复跑全量 ESLint 只拖慢发布，不做质量兜底
  eslint: { ignoreDuringBuilds: true },
  // 将 /api/* 代理到后端，避免浏览器跨域（后端未启用 CORS）
  // 端口约定红线：本地后端固定 8001（Docker 部署时由 BACKEND_URL=http://backend:8000 覆盖）
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://localhost:8001";
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
    ];
  },
  experimental: {
    optimizePackageImports: [
      "lucide-react",
      "recharts",
      "react-markdown",
      "remark-gfm",
      "zod",
    ],
    // 允许 useSearchParams() 在无 Suspense boundary 时降级为 CSR，
    // 而非在 build 阶段抛出 prerender error。
    missingSuspenseWithCSRBailout: false,
  },
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.amazonaws.com",
      },
      {
        protocol: "https",
        hostname: "**.githubusercontent.com",
      },
      {
        protocol: "https",
        hostname: "avatars.githubusercontent.com",
      },
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
      },
    ],
    formats: ["image/avif", "image/webp"],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    minimumCacheTTL: 60 * 60 * 24 * 30,
  },
  poweredByHeader: false,
  compress: true,
  productionBrowserSourceMaps: false,
};

module.exports = nextConfig;
