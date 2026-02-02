/**
 * k6 Spike Test
 *
 * 突然の負荷急増に対するシステムの耐性をテストします。
 *
 * 実行方法:
 *   k6 run tests/load/spike-test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 10 },    // 準備
    { duration: '10s', target: 200 },   // 急激な負荷増加（スパイク）
    { duration: '1m', target: 200 },    // スパイク持続
    { duration: '30s', target: 10 },    // 通常レベルに戻る
    { duration: '30s', target: 0 },     // クールダウン
  ],

  thresholds: {
    http_req_duration: ['p(95)<1000'],  // スパイク時も95%が1秒以内
    http_req_failed: ['rate<0.10'],     // スパイク時は10%まで許容
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost';

export default function() {
  const response = http.get(`${BASE_URL}/health`);

  check(response, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(0.5);
}
