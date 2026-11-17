import { describe, expect, it } from 'vitest';
import { createHealthClient } from '../../../clients/platform/healthClient.js';

describe('GET /health', () => {
  it('Should_ReportHealthy_When_ApiIsUp', async () => {
    const health = await createHealthClient('').getTyped(200);

    expect(health.status, 'health status').toBe('Healthy');
  });
});
