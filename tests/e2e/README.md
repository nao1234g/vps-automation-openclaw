# E2E Testing with Playwright

## Overview

This directory contains end-to-end (E2E) tests for the OpenClaw VPS deployment using Playwright.

## Test Coverage

### Health Checks (`specs/health-checks.spec.ts`)
- ✅ Service health endpoints (OpenClaw, N8N, Grafana, Prometheus)
- ✅ Database connection health
- ✅ Security headers validation
- ✅ Rate limiting enforcement

### API Endpoints (`specs/api-endpoints.spec.ts`)
- ✅ Cost tracking API (daily, monthly, forecast, alerts)
- ✅ System metrics API (resources, containers)
- ✅ Error handling (400, 401, 404 responses)
- ✅ Response time validation

### Monitoring (`specs/monitoring.spec.ts`)
- ✅ Prometheus metrics collection
- ✅ Service availability monitoring
- ✅ Alertmanager configuration
- ✅ Grafana dashboards
- ✅ Alert rules validation

## Setup

### 1. Install Dependencies

```bash
cd tests/e2e
npm install
npm run install-deps
```

### 2. Configure Environment

Set the base URL for testing:

```bash
export BASE_URL=http://localhost
# or for production
export BASE_URL=https://your-domain.com
```

### 3. Ensure Services are Running

```bash
# Start all services
docker compose -f docker-compose.production.yml up -d

# Verify services are healthy
./scripts/health_check.sh
```

## Running Tests

### Run All Tests

```bash
npm test
```

### Run in UI Mode (Interactive)

```bash
npm run test:ui
```

### Run in Headed Mode (See Browser)

```bash
npm run test:headed
```

### Run Specific Test Suite

```bash
npm run test:health      # Health checks only
npm run test:api         # API endpoint tests only
npm run test:monitoring  # Monitoring tests only
```

### Run on Specific Browser

```bash
npm run test:chromium    # Chromium only
npm run test:firefox     # Firefox only
npm run test:mobile      # Mobile Chrome
```

### Debug Tests

```bash
npm run test:debug
```

## Test Results

### View HTML Report

```bash
npm run report
```

### Test Artifacts

Test artifacts are saved in `test-results/`:
- Screenshots (on failure)
- Videos (on failure)
- Traces (on retry)
- JSON report
- JUnit XML

## CI/CD Integration

Tests run automatically on:
- Pull requests
- Pushes to main branch
- Scheduled runs (daily at 2 AM)

See `.github/workflows/e2e-tests.yml` for configuration.

## Writing New Tests

### Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test('should do something', async ({ request }) => {
    const response = await request.get('/endpoint');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('field');
  });
});
```

### Best Practices

1. **Use Descriptive Names**: Test names should clearly describe what they're testing
2. **Test Isolation**: Each test should be independent
3. **Use Page Object Model**: For UI tests (not API tests)
4. **Assert Meaningful Errors**: Use specific assertions
5. **Handle Flaky Tests**: Use retries and proper waits
6. **Clean Up**: Remove test data after tests

### Testing Checklist

- [ ] Test passes consistently (run 10 times)
- [ ] Test has clear, descriptive name
- [ ] Test assertions are specific and meaningful
- [ ] Test handles edge cases
- [ ] Test is independent (no shared state)
- [ ] Test documentation is clear

## Troubleshooting

### Tests Failing Due to Services Not Ready

Increase timeout or add wait:

```typescript
await page.waitForLoadState('networkidle');
```

### Flaky Tests

1. Increase timeout
2. Add explicit waits
3. Use retry strategy
4. Check for race conditions

### Screenshots Not Captured

Ensure `screenshot: 'only-on-failure'` in config.

### Cannot Connect to Services

1. Check Docker containers are running
2. Verify BASE_URL is correct
3. Check firewall rules
4. Verify network connectivity

## Performance Benchmarks

Target response times:
- Health checks: < 200ms
- API endpoints: < 1000ms
- Database queries: < 100ms
- Page loads: < 3000ms

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [API Testing](https://playwright.dev/docs/api-testing)
- [Debugging](https://playwright.dev/docs/debug)
