import { test, expect } from '@playwright/test';

/**
 * API Endpoint Tests
 *
 * Test critical API endpoints for correct responses and error handling.
 */

test.describe('Cost Tracking API', () => {
  test('Daily costs endpoint should return data', async ({ request }) => {
    const today = new Date().toISOString().split('T')[0];
    const response = await request.get(`/api/costs/daily?date=${today}`);

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('date');
    expect(body).toHaveProperty('api_calls');
    expect(body).toHaveProperty('tokens');
    expect(body).toHaveProperty('cost');
  });

  test('Monthly costs summary should return data', async ({ request }) => {
    const response = await request.get('/api/costs/monthly');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('month');
    expect(body).toHaveProperty('total_api_calls');
    expect(body).toHaveProperty('total_cost');
    expect(body).toHaveProperty('budget');
  });

  test('Cost forecast should return predictions', async ({ request }) => {
    const response = await request.get('/api/costs/forecast');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('current_month_cost');
    expect(body).toHaveProperty('forecast_month_end');
    expect(body).toHaveProperty('days_remaining');
    expect(body).toHaveProperty('daily_average');
  });

  test('Budget alerts should return current status', async ({ request }) => {
    const response = await request.get('/api/costs/alerts');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('alerts');
    expect(Array.isArray(body.alerts)).toBeTruthy();
  });
});

test.describe('System Metrics API', () => {
  test('System resources should return current usage', async ({ request }) => {
    const response = await request.get('/api/metrics/system');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('cpu');
    expect(body).toHaveProperty('memory');
    expect(body).toHaveProperty('disk');
    expect(body.cpu).toHaveProperty('usage_percent');
    expect(body.memory).toHaveProperty('used_percent');
  });

  test('Docker containers status should return container info', async ({ request }) => {
    const response = await request.get('/api/metrics/containers');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('containers');
    expect(Array.isArray(body.containers)).toBeTruthy();

    if (body.containers.length > 0) {
      const container = body.containers[0];
      expect(container).toHaveProperty('name');
      expect(container).toHaveProperty('status');
      expect(container).toHaveProperty('cpu_percent');
      expect(container).toHaveProperty('memory_usage');
    }
  });
});

test.describe('Error Handling', () => {
  test('Invalid date should return 400', async ({ request }) => {
    const response = await request.get('/api/costs/daily?date=invalid-date');

    expect(response.status()).toBe(400);

    const body = await response.json();
    expect(body).toHaveProperty('error');
  });

  test('Missing required parameters should return 400', async ({ request }) => {
    const response = await request.post('/api/usage', {
      data: {}, // Empty body
    });

    expect(response.status()).toBe(400);

    const body = await response.json();
    expect(body).toHaveProperty('error');
  });

  test('Non-existent endpoint should return 404', async ({ request }) => {
    const response = await request.get('/api/nonexistent-endpoint');

    expect(response.status()).toBe(404);
  });

  test('Unauthorized access should return 401', async ({ request }) => {
    const response = await request.get('/api/admin/protected', {
      headers: {
        // No authorization header
      },
    });

    expect(response.status()).toBe(401);
  });
});

test.describe('Response Times', () => {
  test('Health check should respond within 200ms', async ({ request }) => {
    const start = Date.now();
    const response = await request.get('/health');
    const duration = Date.now() - start;

    expect(response.ok()).toBeTruthy();
    expect(duration).toBeLessThan(200);
  });

  test('API endpoints should respond within 1 second', async ({ request }) => {
    const start = Date.now();
    const response = await request.get('/api/costs/daily');
    const duration = Date.now() - start;

    expect(response.ok()).toBeTruthy();
    expect(duration).toBeLessThan(1000);
  });
});
