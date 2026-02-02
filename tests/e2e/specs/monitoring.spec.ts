import { test, expect } from '@playwright/test';

/**
 * Monitoring and Alerting Tests
 *
 * Verify that monitoring systems are functioning correctly.
 */

test.describe('Prometheus Monitoring', () => {
  test('Prometheus should be collecting metrics', async ({ request }) => {
    const response = await request.get('/prometheus/api/v1/query?query=up');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('status', 'success');
    expect(body).toHaveProperty('data');
    expect(body.data).toHaveProperty('result');
    expect(Array.isArray(body.data.result)).toBeTruthy();
    expect(body.data.result.length).toBeGreaterThan(0);
  });

  test('All critical services should be up', async ({ request }) => {
    const services = ['openclaw', 'postgres', 'n8n', 'nginx'];

    for (const service of services) {
      const response = await request.get(
        `/prometheus/api/v1/query?query=up{job="${service}"}`
      );

      expect(response.ok()).toBeTruthy();

      const body = await response.json();
      const result = body.data?.result?.[0];

      if (result) {
        const value = parseInt(result.value[1]);
        expect(value).toBe(1); // 1 = up, 0 = down
      }
    }
  });

  test('CPU usage metrics should be available', async ({ request }) => {
    const response = await request.get(
      '/prometheus/api/v1/query?query=node_cpu_seconds_total'
    );

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.status).toBe('success');
    expect(body.data.result.length).toBeGreaterThan(0);
  });

  test('Memory usage metrics should be available', async ({ request }) => {
    const response = await request.get(
      '/prometheus/api/v1/query?query=node_memory_MemAvailable_bytes'
    );

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.status).toBe('success');
    expect(body.data.result.length).toBeGreaterThan(0);
  });

  test('Container metrics should be available', async ({ request }) => {
    const response = await request.get(
      '/prometheus/api/v1/query?query=container_cpu_usage_seconds_total'
    );

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.status).toBe('success');
    expect(body.data.result.length).toBeGreaterThan(0);
  });
});

test.describe('Alertmanager', () => {
  test('Alertmanager should be accessible', async ({ request }) => {
    const response = await request.get('/alertmanager/api/v2/status');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('cluster');
    expect(body).toHaveProperty('versionInfo');
  });

  test('Alert groups should be queryable', async ({ request }) => {
    const response = await request.get('/alertmanager/api/v2/alerts/groups');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(Array.isArray(body)).toBeTruthy();
  });

  test('Silences should be manageable', async ({ request }) => {
    const response = await request.get('/alertmanager/api/v2/silences');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(Array.isArray(body)).toBeTruthy();
  });
});

test.describe('Grafana Dashboards', () => {
  test('Grafana API should be accessible', async ({ request }) => {
    const response = await request.get('/grafana/api/health');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('database', 'ok');
    expect(body).toHaveProperty('version');
  });

  test('Dashboards should be queryable', async ({ request }) => {
    // Note: This requires authentication
    const response = await request.get('/grafana/api/search?type=dash-db');

    // May return 401 if not authenticated, which is expected
    if (response.ok()) {
      const body = await response.json();
      expect(Array.isArray(body)).toBeTruthy();
    }
  });

  test('Datasources should be configured', async ({ request }) => {
    // Note: This requires authentication
    const response = await request.get('/grafana/api/datasources');

    // May return 401 if not authenticated, which is expected
    if (response.ok()) {
      const body = await response.json();
      expect(Array.isArray(body)).toBeTruthy();

      // Should have Prometheus datasource
      const hasPrometheus = body.some(
        (ds: any) => ds.type === 'prometheus'
      );
      expect(hasPrometheus).toBeTruthy();
    }
  });
});

test.describe('Alert Rules', () => {
  test('Prometheus alert rules should be loaded', async ({ request }) => {
    const response = await request.get('/prometheus/api/v1/rules');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.status).toBe('success');
    expect(body.data).toHaveProperty('groups');
    expect(Array.isArray(body.data.groups)).toBeTruthy();

    // Should have at least one rule group
    expect(body.data.groups.length).toBeGreaterThan(0);
  });

  test('Alert rules should be valid', async ({ request }) => {
    const response = await request.get('/prometheus/api/v1/rules');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    const groups = body.data.groups;

    for (const group of groups) {
      expect(group).toHaveProperty('name');
      expect(group).toHaveProperty('rules');
      expect(Array.isArray(group.rules)).toBeTruthy();

      for (const rule of group.rules) {
        expect(rule).toHaveProperty('name');
        expect(rule).toHaveProperty('query');
        expect(rule).toHaveProperty('health', 'ok');
      }
    }
  });
});
