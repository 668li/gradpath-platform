// smoke.js — 冒烟测试
// 目的：快速验证后端服务可用、公开端点正常响应。
// 配置：3 VU × 30s，阈值 p(95)<500ms、失败率<1%。
// 执行：k6 run smoke.js
//       k6 run -e BASE_URL=http://localhost:8000 smoke.js

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 3,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // 健康检查
  const healthRes = http.get(`${BASE}/health`);
  check(healthRes, {
    'health 200': (r) => r.status === 200,
    'health body ok': (r) => {
      try {
        const body = r.json();
        return body && (body.status === 'ok' || body.status === 'healthy' || r.body.includes('ok'));
      } catch (e) {
        return r.body && r.body.length > 0;
      }
    },
  });

  // 公开端点：就业院校数据（GET /api/employment/schools）
  const schoolsRes = http.get(`${BASE}/api/employment/schools`);
  check(schoolsRes, {
    'schools 200': (r) => r.status === 200,
  });

  // 公开端点：社区帖子（GET /api/posts/public?page=1&page_size=10）
  const postsRes = http.get(`${BASE}/api/posts/public?page=1&page_size=10`);
  check(postsRes, {
    'posts 200': (r) => r.status === 200,
  });

  sleep(1);
}
