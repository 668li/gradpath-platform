// seed-test-users.js — 测试用户批量注册
// 目的：在执行 load/stress/spike/ai-endpoint 前，批量注册测试账号。
// 注册账号：
//   - load1@test.com ~ load{N}@test.com  （供 load/stress/spike 使用）
//   - test1@test.com ~ test{N}@test.com   （供 ai-endpoint 使用）
// 密码统一 Test1234!，name 为 TestUserX / LoadUserX。
//
// 执行：
//   k6 run seed-test-users.js                            # 默认注册 10 个 load + 10 个 test
//   k6 run -e USER_COUNT=50 seed-test-users.js           # 注册 50 个 load + 50 个 test
//   k6 run -e USER_COUNT=100 -e REGISTER_INTERVAL=1 seed-test-users.js  # 快速模式（需先调高限速）
//
// 注意：/api/auth/register 限速 3/min/IP。
//   - 默认 REGISTER_INTERVAL=22s，10 个账号约需 7 分钟。
//   - 100 个账号需 37 分钟，建议测试前临时调高
//     backend/app/api/auth.py 的 register 限速到 "200/minute"，
//     并设置 REGISTER_INTERVAL=1 加速。
//   - 已存在的账号会自动跳过（幂等），可重复执行。

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 1,           // 单 VU 串行注册，避免并发触发限速
  iterations: 1,    // setup 只执行一次
};

const BASE = __ENV.BASE_URL || 'http://localhost:8000';
const USER_COUNT = parseInt(__ENV.USER_COUNT || '10', 10);
const PASSWORD = 'Test1234!';
// 注册限速 3/min = 20s/次，保守用 22s
const REGISTER_INTERVAL = parseFloat(__ENV.REGISTER_INTERVAL || '22');

function registerOne(email, name) {
  const payload = JSON.stringify({
    email: email,
    password: PASSWORD,
    name: name,
    agree_terms: true,
  });

  const res = http.post(`${BASE}/api/auth/register`, payload, {
    headers: { 'Content-Type': 'application/json' },
  });

  if (res.status === 201) {
    console.log(`✓ 注册成功: ${email}`);
    return 'created';
  }

  // 409 冲突 / 400 已存在 / 422 已注册 —— 视为已存在，幂等跳过
  if (res.status === 409 || res.status === 400 || res.status === 422) {
    console.log(`→ 已存在跳过: ${email} (status=${res.status})`);
    return 'skipped';
  }

  if (res.status === 429) {
    // 限速，等待 60s 后重试一次
    console.log(`⚠ 限速 429，等待 60s 后重试: ${email}`);
    sleep(60);
    const retry = http.post(`${BASE}/api/auth/register`, payload, {
      headers: { 'Content-Type': 'application/json' },
    });
    if (retry.status === 201) {
      console.log(`✓ 重试成功: ${email}`);
      return 'created';
    }
    console.log(`✗ 重试失败: ${email} status=${retry.status} body=${retry.body}`);
    return 'failed';
  }

  console.log(`✗ 注册失败: ${email} status=${res.status} body=${res.body}`);
  return 'failed';
}

export function setup() {
  console.log(`\n===== 开始注册测试用户 =====`);
  console.log(`BASE_URL: ${BASE}`);
  console.log(`USER_COUNT: ${USER_COUNT}（load + test 各 ${USER_COUNT} 个）`);
  console.log(`REGISTER_INTERVAL: ${REGISTER_INTERVAL}s`);
  console.log(`预计耗时: ~${Math.ceil((USER_COUNT * 2 * REGISTER_INTERVAL) / 60)} 分钟\n`);

  const stats = { created: 0, skipped: 0, failed: 0 };
  const allEmails = [];

  // 注册 load1~loadN（供 load/stress/spike 使用）
  for (let i = 1; i <= USER_COUNT; i++) {
    const email = `load${i}@test.com`;
    const result = registerOne(email, `LoadUser${i}`);
    stats[result]++;
    allEmails.push(email);
    if (i < USER_COUNT) sleep(REGISTER_INTERVAL);
  }

  // 注册 test1~testN（供 ai-endpoint 使用）
  for (let i = 1; i <= USER_COUNT; i++) {
    const email = `test${i}@test.com`;
    const result = registerOne(email, `TestUser${i}`);
    stats[result]++;
    allEmails.push(email);
    if (i < USER_COUNT) sleep(REGISTER_INTERVAL);
  }

  console.log(`\n===== 注册汇总 =====`);
  console.log(`成功: ${stats.created}`);
  console.log(`跳过(已存在): ${stats.skipped}`);
  console.log(`失败: ${stats.failed}`);
  console.log(`总计: ${USER_COUNT * 2}`);
  console.log(`密码统一: ${PASSWORD}`);

  return { emails: allEmails, stats, password: PASSWORD };
}

export default function (data) {
  console.log(`\n注册流程完成。`);
  console.log(`成功 ${data.stats.created} / 跳过 ${data.stats.skipped} / 失败 ${data.stats.failed}`);
  console.log(`密码统一为: ${data.password}`);
  console.log(`\n下一步可执行: k6 run load.js`);
}
