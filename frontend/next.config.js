/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
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
