const { withSentryConfig } = require("@sentry/nextjs");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 将 /api/* 代理到后端，避免浏览器跨域（后端未启用 CORS）
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
    ];
  },
  experimental: {
    optimizePackageImports: ["lucide-react", "recharts"],
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
  bundleAnalyzer: { enabled: process.env.ANALYZE === "true" },
  poweredByHeader: false,
  compress: true,
  productionBrowserSourceMaps: false,
};

// B5: Sentry webpack 包装 — 仅在 SENTRY_DSN / NEXT_PUBLIC_SENTRY_DSN 配置时启用 source map 上传。
// 本地未配置时 withSentryConfig 仍可正常工作，仅跳过上传。
module.exports = withSentryConfig(
  nextConfig,
  {
    // 静默 Sentry logger 噪声
    silent: true,
    // 生产构建时禁用 source map 上传到 Sentry（如需启用请配置 SENTRY_AUTH_TOKEN）
    // https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/
    org: process.env.SENTRY_ORG,
    project: process.env.SENTRY_PROJECT,
    // 不在构建时上传 sourcemap（避免 CI 缺少 token 导致 build 失败）
    sourcemaps: {
      disable: true,
    },
    // 不自动插入 React Component Stack（生产环境会暴露源码）
    reactComponentAnnotation: {
      enabled: false,
    },
    // 树摇未使用的 Sentry 代码
    treeShaking: true,
  },
);
