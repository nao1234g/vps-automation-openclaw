/**
 * k6 Soak Test
 *
 * 長時間の負荷に対するシステムの安定性をテストします（メモリリーク等の検出）。
 *
 * 実行方法:
 *   k6 run tests/load/soak-test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '5m', target: 50 },     // ウォームアップ
    { duration: '2h', target: 50 },     // 2時間持続（ソークテスト）
    { duration: '5m', target: 0 },      // クールダウン
  ],

  thresholds: {
    http_req_duration: ['p(95)<500'],   // 長時間でもパフォーマンス維持
    http_req_failed: ['rate<0.01'],     // エラー率1%未満
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost';

export default function() {
  // 実際のユーザー行動をシミュレート

  // 1. ヘルスチェック
  let response = http.get(`${BASE_URL}/health`);
  check(response, { 'health check OK': (r) => r.status === 200 });
  sleep(2);

  // 2. コスト確認
  response = http.get(`${BASE_URL}/api/costs/daily`);
  check(response, { 'costs API OK': (r) => r.status === 200 });
  sleep(3);

  // 3. メトリクス確認
  response = http.get(`${BASE_URL}/api/metrics/system`);
  check(response, { 'metrics API OK': (r) => r.status === 200 });
  sleep(5);
}
