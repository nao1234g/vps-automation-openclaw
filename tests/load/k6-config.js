/**
 * k6 Load Testing Configuration
 *
 * このスクリプトは、OpenClaw VPSの負荷テストを実行します。
 *
 * 実行方法:
 *   k6 run tests/load/k6-config.js
 *
 * オプション:
 *   k6 run --vus 10 --duration 30s tests/load/k6-config.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// カスタムメトリクス
const errorRate = new Rate('errors');
const healthCheckDuration = new Trend('health_check_duration');
const apiCallDuration = new Trend('api_call_duration');
const totalRequests = new Counter('total_requests');

// 設定
export const options = {
  // ステージベースの負荷テスト
  stages: [
    { duration: '1m', target: 10 },   // Warm-up: 1分で10 VUsまで増加
    { duration: '3m', target: 10 },   // Stay: 10 VUsで3分間維持
    { duration: '1m', target: 50 },   // Ramp-up: 1分で50 VUsまで増加
    { duration: '5m', target: 50 },   // Peak: 50 VUsで5分間維持
    { duration: '2m', target: 100 },  // Spike: 2分で100 VUsまで増加
    { duration: '2m', target: 100 },  // Spike持続
    { duration: '2m', target: 0 },    // Cool-down: 2分で0まで減少
  ],

  // しきい値（これを超えるとテスト失敗）
  thresholds: {
    // HTTPリクエストの95%が500ms以内に完了
    http_req_duration: ['p(95)<500'],

    // HTTPリクエストの失敗率が1%未満
    http_req_failed: ['rate<0.01'],

    // エラー率が5%未満
    errors: ['rate<0.05'],

    // ヘルスチェックの95%が200ms以内
    health_check_duration: ['p(95)<200'],

    // APIコールの95%が1000ms以内
    api_call_duration: ['p(95)<1000'],
  },

  // タグ
  tags: {
    project: 'openclaw-vps',
    environment: 'load-test',
  },
};

// ベースURL（環境変数から取得）
const BASE_URL = __ENV.BASE_URL || 'http://localhost';

// テストシナリオ
export default function() {
  // シナリオをランダムに選択（実際のユーザー行動をシミュレート）
  const scenarios = [
    healthCheckScenario,
    apiUsageScenario,
    costTrackingScenario,
    metricsScenario,
  ];

  const scenario = scenarios[Math.floor(Math.random() * scenarios.length)];
  scenario();

  // ユーザーの操作間隔をシミュレート（1-3秒）
  sleep(Math.random() * 2 + 1);
}

/**
 * ヘルスチェックシナリオ
 */
function healthCheckScenario() {
  const startTime = Date.now();

  const response = http.get(`${BASE_URL}/health`, {
    tags: { scenario: 'health_check' },
  });

  const duration = Date.now() - startTime;
  healthCheckDuration.add(duration);
  totalRequests.add(1);

  const result = check(response, {
    'health check status is 200': (r) => r.status === 200,
    'health check has status field': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.status === 'ok';
      } catch (e) {
        return false;
      }
    },
    'health check response time < 200ms': (r) => r.timings.duration < 200,
  });

  if (!result) {
    errorRate.add(1);
  }
}

/**
 * API使用量取得シナリオ
 */
function apiUsageScenario() {
  const startTime = Date.now();

  const today = new Date().toISOString().split('T')[0];
  const response = http.get(`${BASE_URL}/api/costs/daily?date=${today}`, {
    tags: { scenario: 'api_usage' },
  });

  const duration = Date.now() - startTime;
  apiCallDuration.add(duration);
  totalRequests.add(1);

  const result = check(response, {
    'api usage status is 200': (r) => r.status === 200,
    'api usage has date field': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.date !== undefined;
      } catch (e) {
        return false;
      }
    },
    'api usage response time < 1000ms': (r) => r.timings.duration < 1000,
  });

  if (!result) {
    errorRate.add(1);
  }
}

/**
 * コスト追跡シナリオ
 */
function costTrackingScenario() {
  const startTime = Date.now();

  // 月次コスト取得
  const monthlyResponse = http.get(`${BASE_URL}/api/costs/monthly`, {
    tags: { scenario: 'cost_tracking' },
  });

  totalRequests.add(1);

  let result = check(monthlyResponse, {
    'monthly costs status is 200': (r) => r.status === 200,
    'monthly costs has total_cost': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.total_cost !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  if (!result) {
    errorRate.add(1);
  }

  sleep(0.5);

  // 予測取得
  const forecastResponse = http.get(`${BASE_URL}/api/costs/forecast`, {
    tags: { scenario: 'cost_tracking' },
  });

  const duration = Date.now() - startTime;
  apiCallDuration.add(duration);
  totalRequests.add(1);

  result = check(forecastResponse, {
    'forecast status is 200': (r) => r.status === 200,
    'forecast has prediction': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.forecast_month_end !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  if (!result) {
    errorRate.add(1);
  }
}

/**
 * システムメトリクスシナリオ
 */
function metricsScenario() {
  const startTime = Date.now();

  // システムリソース取得
  const systemResponse = http.get(`${BASE_URL}/api/metrics/system`, {
    tags: { scenario: 'metrics' },
  });

  totalRequests.add(1);

  let result = check(systemResponse, {
    'system metrics status is 200': (r) => r.status === 200,
    'system metrics has cpu': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.cpu !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  if (!result) {
    errorRate.add(1);
  }

  sleep(0.3);

  // コンテナメトリクス取得
  const containersResponse = http.get(`${BASE_URL}/api/metrics/containers`, {
    tags: { scenario: 'metrics' },
  });

  const duration = Date.now() - startTime;
  apiCallDuration.add(duration);
  totalRequests.add(1);

  result = check(containersResponse, {
    'container metrics status is 200': (r) => r.status === 200,
    'container metrics has containers': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.containers);
      } catch (e) {
        return false;
      }
    },
  });

  if (!result) {
    errorRate.add(1);
  }
}

/**
 * セットアップ（テスト開始前に1回実行）
 */
export function setup() {
  console.log('Starting load test...');
  console.log(`Base URL: ${BASE_URL}`);
  console.log('Test scenarios: health_check, api_usage, cost_tracking, metrics');

  // サーバーが起動しているか確認
  const response = http.get(`${BASE_URL}/health`);
  if (response.status !== 200) {
    throw new Error(`Server is not healthy. Status: ${response.status}`);
  }

  return { startTime: new Date() };
}

/**
 * ティアダウン（テスト終了後に1回実行）
 */
export function teardown(data) {
  const endTime = new Date();
  const duration = (endTime - data.startTime) / 1000;

  console.log('Load test completed!');
  console.log(`Duration: ${duration.toFixed(2)} seconds`);
  console.log('Check the results summary below.');
}

/**
 * サマリーレポート生成
 */
export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'tests/load/results/summary.json': JSON.stringify(data, null, 2),
    'tests/load/results/summary.html': htmlReport(data),
  };
}

// テキストサマリー生成
function textSummary(data, options) {
  const indent = options.indent || '';
  const colors = options.enableColors;

  let output = '\n';
  output += `${indent}========================================\n`;
  output += `${indent}  Load Test Summary\n`;
  output += `${indent}========================================\n\n`;

  // メトリクスサマリー
  const metrics = data.metrics;

  output += `${indent}Total Requests: ${metrics.total_requests?.values.count || 0}\n`;
  output += `${indent}Error Rate: ${((metrics.errors?.values.rate || 0) * 100).toFixed(2)}%\n`;
  output += `${indent}Failed Requests: ${((metrics.http_req_failed?.values.rate || 0) * 100).toFixed(2)}%\n\n`;

  output += `${indent}Response Times:\n`;
  output += `${indent}  Avg: ${(metrics.http_req_duration?.values.avg || 0).toFixed(2)}ms\n`;
  output += `${indent}  Min: ${(metrics.http_req_duration?.values.min || 0).toFixed(2)}ms\n`;
  output += `${indent}  Max: ${(metrics.http_req_duration?.values.max || 0).toFixed(2)}ms\n`;
  output += `${indent}  p(50): ${(metrics.http_req_duration?.values['p(50)'] || 0).toFixed(2)}ms\n`;
  output += `${indent}  p(90): ${(metrics.http_req_duration?.values['p(90)'] || 0).toFixed(2)}ms\n`;
  output += `${indent}  p(95): ${(metrics.http_req_duration?.values['p(95)'] || 0).toFixed(2)}ms\n`;
  output += `${indent}  p(99): ${(metrics.http_req_duration?.values['p(99)'] || 0).toFixed(2)}ms\n\n`;

  output += `${indent}Health Check Duration:\n`;
  output += `${indent}  Avg: ${(metrics.health_check_duration?.values.avg || 0).toFixed(2)}ms\n`;
  output += `${indent}  p(95): ${(metrics.health_check_duration?.values['p(95)'] || 0).toFixed(2)}ms\n\n`;

  output += `${indent}API Call Duration:\n`;
  output += `${indent}  Avg: ${(metrics.api_call_duration?.values.avg || 0).toFixed(2)}ms\n`;
  output += `${indent}  p(95): ${(metrics.api_call_duration?.values['p(95)'] || 0).toFixed(2)}ms\n\n`;

  output += `${indent}========================================\n`;

  return output;
}

// HTMLレポート生成
function htmlReport(data) {
  return `
<!DOCTYPE html>
<html>
<head>
  <title>Load Test Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
    .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
    .metric { margin: 20px 0; padding: 15px; background: #f9f9f9; border-left: 4px solid #4CAF50; }
    .metric-name { font-weight: bold; color: #555; }
    .metric-value { font-size: 24px; color: #4CAF50; margin: 10px 0; }
    .pass { color: #4CAF50; }
    .fail { color: #f44336; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Load Test Report</h1>
    <p>Generated: ${new Date().toISOString()}</p>

    <div class="metric">
      <div class="metric-name">Total Requests</div>
      <div class="metric-value">${data.metrics.total_requests?.values.count || 0}</div>
    </div>

    <div class="metric">
      <div class="metric-name">Error Rate</div>
      <div class="metric-value ${(data.metrics.errors?.values.rate || 0) < 0.05 ? 'pass' : 'fail'}">
        ${((data.metrics.errors?.values.rate || 0) * 100).toFixed(2)}%
      </div>
    </div>

    <div class="metric">
      <div class="metric-name">Average Response Time</div>
      <div class="metric-value">${(data.metrics.http_req_duration?.values.avg || 0).toFixed(2)}ms</div>
    </div>

    <div class="metric">
      <div class="metric-name">95th Percentile Response Time</div>
      <div class="metric-value ${(data.metrics.http_req_duration?.values['p(95)'] || 0) < 500 ? 'pass' : 'fail'}">
        ${(data.metrics.http_req_duration?.values['p(95)'] || 0).toFixed(2)}ms
      </div>
    </div>
  </div>
</body>
</html>
  `;
}
