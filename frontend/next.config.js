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
};

module.exports = nextConfig;
