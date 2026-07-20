// spike.js — 突发流量测试
// 目的：模拟热门帖子被推荐、邮件推送后用户同时涌入的瞬时高峰。
// 配置：10s 内冲到 500 VU → 保持 1m → 30s 降到 0，共 1m40s。
// 阈值：p(95)<5000ms、失败率<20%（突发流量允许较高失败率，验证是否优雅降级）。
// 前置：先执行 seed-test-users.js 注册 10 个 load1~load10@test.com 账号。
// 执行：k6 run spike.js
//
// 关注点：
//   - 是否有请求超时堆积（http_req_blocked 时长）
//   - 是否出现 5xx（服务崩溃）vs 429（限速降级，可接受）
//   - 恢复时间：降到 0 后后端是否快速恢复

import http from 'k6/http';
import { check, sleep, group } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 500 },   // 10 秒内冲到 500 VU（瞬时高峰）
    { duration: '1m', target: 500 },    // 保持 1 分钟
    { duration: '30s', target: 0 },     // 30 秒降到 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.20'],  // 突发流量允许 20% 失败（含 429 限速）
  },
};

const BASE = __ENV.BASE_URL || 'http://localhost:8000';

const TEST_USERS = [
  { email: 'load1@test.com', password: 'Test1234!' },
  { email: 'load2@test.com', password: 'Test1234!' },
  { email: 'load3@test.com', password: 'Test1234!' },
  { email: 'load4@test.com', password: 'Test1234!' },
  { email: 'load5@test.com', password: 'Test1234!' },
  { email: 'load6@test.com', password: 'Test1234!' },
  { email: 'load7@test.com', password: 'Test1234!' },
  { email: 'load8@test.com', password: 'Test1234!' },
  { email: 'load9@test.com', password: 'Test1234!' },
  { email: 'load10@test.com', password: 'Test1234!' },
];

export default function () {
  const rnd = Math.random();

  if (rnd < 0.6) {
    // 60% 匿名用户浏览公开内容（推送引流场景）
    group('公开浏览', () => {
      const postsRes = http.get(`${BASE}/api/posts/public?page=1&page_size=20`);
      check(postsRes, { 'posts 200': (r) => r.status === 200 });

      const schoolsRes = http.get(`${BASE}/api/employment/schools`);
      check(schoolsRes, { 'schools 200': (r) => r.status === 200 });

      const healthRes = http.get(`${BASE}/health`);
      check(healthRes, { 'health 200': (r) => r.status === 200 });
    });
  } else {
    // 40% 已注册用户登录看板
    const user = TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];
    group('登录用户', () => {
      const loginRes = http.post(`${BASE}/api/auth/login`, JSON.stringify(user), {
        headers: { 'Content-Type': 'application/json' },
      });
      check(loginRes, { 'login 200': (r) => r.status === 200 });

      if (loginRes.status === 200) {
        const token = loginRes.json('access_token');
        const dashRes = http.get(`${BASE}/api/dashboard/overview`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        check(dashRes, { 'dashboard 200': (r) => r.status === 200 });
      }
    });
  }

  sleep(Math.random() * 1 + 0.5); // 0.5-1.5s
}
