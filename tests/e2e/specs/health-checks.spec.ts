import { test, expect } from '@playwright/test';

/**
 * Health Check Tests
 *
 * Verify that all critical services are running and responding correctly.
 */

test.describe('Service Health Checks', () => {
  test('OpenClaw health endpoint should return OK', async ({ request }) => {
    const response = await request.get('/health');

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty('status', 'ok');
    expect(body).toHaveProperty('uptime');
  });

  test('N8N health endpoint should return OK', async ({ request }) => {
    const response = await request.get('/n8n/healthz');

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty('status', 'ok');
  });

  test('Grafana should be accessible', async ({ request }) => {
    const response = await request.get('/grafana/api/health');

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty('database', 'ok');
  });

  test('Prometheus metrics endpoint should be accessible', async ({ request }) => {
    const response = await request.get('/prometheus/metrics');

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const text = await response.text();
    expect(text).toContain('# HELP');
    expect(text).toContain('# TYPE');
  });
});

test.describe('Database Health Checks', () => {
  test('Database connection should be healthy', async ({ request }) => {
    const response = await request.get('/api/health/database');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('database');
    expect(body.database).toHaveProperty('status', 'healthy');
    expect(body.database).toHaveProperty('response_time');

    // Response time should be under 100ms
    expect(body.database.response_time).toBeLessThan(100);
  });
});

test.describe('Security Headers', () => {
  test('Should include security headers', async ({ request }) => {
    const response = await request.get('/');

    const headers = response.headers();

    // Check for critical security headers
    expect(headers['x-content-type-options']).toBe('nosniff');
    expect(headers['x-frame-options']).toBe('DENY');
    expect(headers['x-xss-protection']).toBe('1; mode=block');
    expect(headers['strict-transport-security']).toContain('max-age=');
  });
});

test.describe('Rate Limiting', () => {
  test('Should enforce rate limits', async ({ request }) => {
    const endpoint = '/api/test-rate-limit';

    // Make multiple requests quickly
    const requests = Array(15).fill(null).map(() =>
      request.get(endpoint).catch(() => null)
    );

    const responses = await Promise.all(requests);
    const rateLimited = responses.some(r => r?.status() === 429);

    // At least one request should be rate limited
    expect(rateLimited).toBeTruthy();
  });
});
