// stress.js — 极限压测
// 目的：逐步加压到 1000 VU，找出系统瓶颈（吞吐拐点、错误率飙升点）。
// 配置：2m→200 VU，2m→500 VU，2m→1000 VU，3m 保持 1000 VU，2m→0，共 11 分钟。
// 阈值：分组 P95（Dashboard<3s、院校搜索<2s、公司情报<5s），失败率<10%。
// 前置：先执行 seed-test-users.js 注册 10 个 load1~load10@test.com 账号。
// 执行：k6 run stress.js
//
// 注意：
//   1. 登录限速 5/min/IP —— 1000 VU 并发登录必然大量 429。建议测试前临时
//      调高 backend/app/api/auth.py 的 login 限速到 "5000/minute"，或注释掉。
//   2. group 阈值用 k6 的 {group:::GroupName} 语法，group 名必须与
//      group('Dashboard', ...) 完全一致（含中文）。
//   3. 1000 VU 会打满数据库连接池，观察 DB 连接数、CPU、内存。

import http from 'k6/http';
import { check, sleep, group } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 200 },   // 2 分钟加到 200 VU
    { duration: '2m', target: 500 },   // 2 分钟加到 500 VU
    { duration: '2m', target: 1000 },  // 2 分钟加到 1000 VU（目标峰值）
    { duration: '3m', target: 1000 },  // 3 分钟保持 1000 VU
    { duration: '2m', target: 0 },     // 2 分钟降到 0
  ],
  thresholds: {
    // 嵌套 group 的 tag 值为 :::Dashboard（顶层 group），中文 group 同理
    'http_req_duration{group:::Dashboard}': ['p(95)<3000'],
    'http_req_duration{group:::院校搜索}': ['p(95)<2000'],
    'http_req_duration{group:::公司情报}': ['p(95)<5000'],  // 涉及 DB 查询
    http_req_failed: ['rate<0.10'],  // 1000 VU 下允许 10% 失败
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

const CITIES = ['北京', '上海', '深圳', '杭州', '广州', '成都'];

export default function () {
  const user = TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];
  const city = CITIES[Math.floor(Math.random() * CITIES.length)];

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

    group('Dashboard', () => {
      const dashRes = http.get(`${BASE}/api/dashboard/overview`, { headers: authHeaders });
      check(dashRes, { 'dashboard 200': (r) => r.status === 200 });
    });

    group('院校搜索', () => {
      const schoolsRes = http.get(`${BASE}/api/employment/schools`, { headers: authHeaders });
      check(schoolsRes, { 'schools 200': (r) => r.status === 200 });
    });

    group('公司情报', () => {
      // 增加随机性：模拟不同城市查询
      const intelRes = http.get(`${BASE}/api/career-intel/intel/list`, { headers: authHeaders });
      check(intelRes, { 'intel 200': (r) => r.status === 200 });
    });

    // 额外压测决策列表端点
    group('决策列表', () => {
      const decRes = http.get(`${BASE}/api/decisions?page=1&page_size=10`, { headers: authHeaders });
      check(decRes, { 'decisions 200': (r) => r.status === 200 });
    });
  }

  sleep(Math.random() * 1.5 + 0.5); // 0.5-2s 思考时间（高压下更短）
}
