import { expect } from 'vitest';
import { createBaseClient, parseBody, type ApiResponse } from '../baseClient.js';
import { getTestEnvironment } from '../../config/environment.js';
import { HealthSchema, type HealthDto } from '../../models/platform/health/health.types.js';

const GET_PATH = '/health';

export function createHealthClient(jwt: string) {
  const env = getTestEnvironment();
  const { execute } = createBaseClient({ baseUrl: env.apiUri, authToken: jwt });

  async function get(): Promise<ApiResponse> {
    return execute({ method: 'GET', path: GET_PATH });
  }

  async function getTyped(expectedStatus: number): Promise<HealthDto> {
    const response = await get();
    expect(response.status, `GET ${GET_PATH}: ${response.bodyText}`).toBe(expectedStatus);
    return parseBody(HealthSchema, response);
  }

  return { get, getTyped } as const;
}

export type HealthClient = ReturnType<typeof createHealthClient>;
