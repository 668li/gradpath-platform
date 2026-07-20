// load.js — 负载测试
// 目的：模拟日常峰值流量，验证系统在 50→200 VU 下的稳定性。
// 配置：1m 加压到 50 VU → 3m 加压到 200 VU → 1m 降到 0，共 5 分钟。
// 阈值：p(95)<2000ms、p(99)<5000ms、失败率<5%。
// 前置：先执行 seed-test-users.js 注册 10 个 load1~load10@test.com 账号。
// 执行：k6 run load.js
//
// 注意：/api/auth/login 限速 5/min/IP。200 VU 并发登录会触发 429。
//   若要测试后端纯吞吐能力（排除限速），请在测试环境临时调高
//   backend/app/api/auth.py 的 login 限速（如改为 "1000/minute"）。
//   否则 login 200 的 check 通过率会较低，属预期行为。

import http from 'k6/http';
import { check, sleep, group } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },   // 1 分钟加到 50 VU
    { duration: '3m', target: 200 },  // 3 分钟加到 200 VU
    { duration: '1m', target: 0 },    // 1 分钟降到 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000', 'p(99)<5000'],
    http_req_failed: ['rate<0.05'],
  },
};

const BASE = __ENV.BASE_URL || 'http://localhost:8000';

// 测试用户池（需先用 seed-test-users.js 注册）
// 命名约定：load1@test.com ~ load10@test.com，密码统一 Test1234!
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
  const user = TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];

  // 登录（不放进 group，避免污染子 group 的阈值统计）
  const loginRes = http.post(`${BASE}/api/auth/login`, JSON.stringify(user), {
    headers: { 'Content-Type': 'application/json' },
  });
  check(loginRes, { 'login 200': (r) => r.status === 200 });

  if (loginRes.status === 200) {
    const token = loginRes.json('access_token');
    const authHeaders = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    // 实际端点：GET /api/dashboard/overview（任务框架写的是 /api/dashboard，已修正）
    group('Dashboard', () => {
      const dashRes = http.get(`${BASE}/api/dashboard/overview`, { headers: authHeaders });
      check(dashRes, { 'dashboard 200': (r) => r.status === 200 });
    });

    // 实际端点：GET /api/employment/schools（不接受 limit 参数，已去掉）
    group('院校搜索', () => {
      const schoolsRes = http.get(`${BASE}/api/employment/schools`, { headers: authHeaders });
      check(schoolsRes, { 'schools 200': (r) => r.status === 200 });
    });

    // 实际端点：GET /api/career-intel/intel/list（任务框架写的是 /intel，已修正）
    group('公司情报', () => {
      const intelRes = http.get(`${BASE}/api/career-intel/intel/list`, { headers: authHeaders });
      check(intelRes, { 'intel 200': (r) => r.status === 200 });
    });
  }

  sleep(Math.random() * 2 + 1); // 1-3s 思考时间
}
