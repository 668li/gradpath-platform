// ai-endpoint.js — AI 端点专项压测
// 目的：单独压测 POST /api/ai/decision-advice，验证 LLM 调用链路稳定性。
// 配置：20 VU × 2m（VU 数刻意压低，避免打爆 LLM 配额）。
// 阈值：p(95)<30s（AI 调用慢，5-15s 是常态）、失败率<30%（考虑熔断器/配额限速）。
// 前置：先执行 seed-test-users.js 注册测试账号，并确保 LLM_API_KEY 已配置。
// 执行：k6 run ai-endpoint.js
//
// 设计要点：
//   1. AI 端点限速 10/min/用户 —— 单账号会被限速，用 __VU 轮换 20 个账号
//      （需注册 test1~test20@test.com，或复用 load1~load10 + test1~test10）。
//   2. LLM 调用慢，单请求 timeout 设为 60s（k6 默认 60s）。
//   3. 429（配额）/503（熔断）视为预期行为，不算 hard failure，但仍计入
//      http_req_failed（k6 默认非 2xx 算 failed）。阈值 rate<0.30 容忍这些。
//   4. 迭代间 sleep 2s，避免单 VU 持续打满 10/min 配额。

import http from 'k6/http';
import { check, sleep, group } from 'k6';

export const options = {
  vus: 20,
  duration: '2m',
  thresholds: {
    http_req_duration: ['p(95)<30000'],  // AI 调用慢，30s
    http_req_failed: ['rate<0.30'],      // 允许 30% 失败（熔断/配额）
  },
};

const BASE = __ENV.BASE_URL || 'http://localhost:8000';

// 用 __VU 轮换账号，避免单账号触发 10/min 限速
// 优先用 load1~load10，再用 test1~test10（共 20 个，与 VU 数匹配）
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
  { email: 'test1@test.com', password: 'Test1234!' },
  { email: 'test2@test.com', password: 'Test1234!' },
  { email: 'test3@test.com', password: 'Test1234!' },
  { email: 'test4@test.com', password: 'Test1234!' },
  { email: 'test5@test.com', password: 'Test1234!' },
  { email: 'test6@test.com', password: 'Test1234!' },
  { email: 'test7@test.com', password: 'Test1234!' },
  { email: 'test8@test.com', password: 'Test1234!' },
  { email: 'test9@test.com', password: 'Test1234!' },
  { email: 'test10@test.com', password: 'Test1234!' },
];

// AI 决策指导请求体（符合 DecisionAdviceRequest schema）
const ADVICE_BODIES = [
  { destination_type: 'employment', company: '字节跳动', position: '后端工程师', city: '北京', expected_salary: '25k_50k' },
  { destination_type: 'employment', company: '腾讯', position: '产品经理', city: '深圳', expected_salary: '20k_40k' },
  { destination_type: 'employment', company: '阿里巴巴', position: '算法工程师', city: '杭州', expected_salary: '30k_60k' },
  { destination_type: 'postgrad', company: null, position: null, city: '北京', expected_salary: null },
  { destination_type: 'abroad', company: null, position: null, city: '硅谷', expected_salary: null },
  { destination_type: 'employment', company: '美团', position: '前端工程师', city: '北京', expected_salary: '22k_45k' },
  { destination_type: 'civil_servant', company: null, position: '选调生', city: '成都', expected_salary: null },
];

export default function () {
  // __VU 从 1 开始，取模映射到用户池
  const user = TEST_USERS[(__VU - 1) % TEST_USERS.length];
  const body = ADVICE_BODIES[Math.floor(Math.random() * ADVICE_BODIES.length)];

  group('AI 决策指导', () => {
    // 先登录获取 token
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

      // AI 决策指导，单请求超时 60s（k6 默认）
      const adviceRes = http.post(
        `${BASE}/api/ai/decision-advice`,
        JSON.stringify(body),
        { headers: authHeaders, timeout: '60s' }
      );

      // 200 成功 / 429 配额限速 / 503 熔断 / 504 超时 —— 后三者视为预期降级
      const isAccepted =
        adviceRes.status === 200 ||
        adviceRes.status === 429 ||
        adviceRes.status === 503 ||
        adviceRes.status === 504;

      check(adviceRes, {
        'advice completed or degraded': (r) => isAccepted,
        'advice 200': (r) => r.status === 200,
      });
    }
  });

  sleep(2); // AI 调用本身慢，减少迭代频率避免打满配额
}
