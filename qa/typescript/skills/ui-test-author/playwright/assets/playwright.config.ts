import { defineConfig, devices } from '@playwright/test';
import { authFile } from './fixtures';

const isCI = !!process.env.CI;

export default defineConfig({
  forbidOnly: isCI,
  fullyParallel: true,
  retries: 0,
  reporter: isCI
    ? [
        ['blob'],
        ['junit', { outputFile: 'test-results/junit.xml' }],
        ['allure-playwright', { resultsDir: 'allure-results' }],
      ]
    : [['html']],
  updateSnapshots: isCI ? 'none' : 'missing',
  use: {
    baseURL: process.env.BASE_URL,
    testIdAttribute: 'data-testid',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    screenshot: { mode: 'only-on-failure', fullPage: true },
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: authFile },
      dependencies: ['setup'],
    },
  ],
});
