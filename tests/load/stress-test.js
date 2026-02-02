/**
 * k6 Stress Test
 *
 * システムの限界を見つけるためのストレステストです。
 *
 * 実行方法:
 *   k6 run tests/load/stress-test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },     // 50 VUsまでウォームアップ
    { duration: '2m', target: 100 },    // 100 VUsに増加
    { duration: '2m', target: 200 },    // 200 VUsに増加
    { duration: '2m', target: 300 },    // 300 VUsに増加（限界テスト）
    { duration: '2m', target: 400 },    // 400 VUsに増加
    { duration: '5m', target: 0 },      // ゆっくりクールダウン
  ],

  thresholds: {
    http_req_duration: ['p(95)<2000'],  // ストレス下でも95%が2秒以内
    http_req_failed: ['rate<0.20'],     // 20%まで失敗を許容
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost';

export default function() {
  const scenarios = [
    () => http.get(`${BASE_URL}/health`),
    () => http.get(`${BASE_URL}/api/costs/daily`),
    () => http.get(`${BASE_URL}/api/metrics/system`),
  ];

  const scenario = scenarios[Math.floor(Math.random() * scenarios.length)];
  const response = scenario();

  check(response, {
    'status is not 500': (r) => r.status !== 500,
  });

  sleep(Math.random());
}
