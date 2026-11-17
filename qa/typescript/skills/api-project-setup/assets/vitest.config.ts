import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['src/specs/**/*.spec.ts'],
    reporters: [
      'default',
      ['junit', { outputFile: 'test-results/junit.xml' }],
      ['allure-vitest/reporter', { resultsDir: 'allure-results' }],
    ],
  },
});
