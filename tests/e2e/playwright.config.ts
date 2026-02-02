import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E Testing Configuration
 *
 * Tests critical user flows:
 * - Application health checks
 * - API endpoint responses
 * - N8N workflow triggers
 * - Monitoring dashboard access
 */

export default defineConfig({
  testDir: './specs',

  // Maximum time one test can run
  timeout: 30 * 1000,

  // Test artifacts
  outputDir: './test-results',

  // Run tests in files in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,

  // Reporter to use
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],

  use: {
    // Base URL for tests
    baseURL: process.env.BASE_URL || 'http://localhost',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',

    // Maximum time each action can take
    actionTimeout: 10 * 1000,

    // Timeout for navigation
    navigationTimeout: 15 * 1000,
  },

  // Projects for different scenarios
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  // Web Server configuration (if needed)
  webServer: process.env.CI ? undefined : {
    command: 'docker compose -f docker-compose.production.yml up -d',
    url: 'http://localhost/health',
    timeout: 120 * 1000,
    reuseExistingServer: true,
  },
});
