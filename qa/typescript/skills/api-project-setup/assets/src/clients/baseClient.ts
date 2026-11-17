import type { z } from 'zod';
import { newTraceparent } from '../support/testTrace.js';

export type ApiResponse = {
  readonly status: number;
  readonly headers: Headers;
  readonly bodyText: string;
  readonly bodyJson: unknown;
};

export type ApiRequest = {
  readonly method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  readonly path: string;
  readonly query?: Readonly<Record<string, string | number | boolean | undefined>>;
  readonly jsonBody?: unknown;
  readonly rawBody?: string;
  readonly contentType?: string;
};

type BaseClientOptions = {
  readonly baseUrl: string;
  readonly authToken: string;
};

export function createBaseClient({ baseUrl, authToken }: BaseClientOptions) {
  async function execute(request: ApiRequest): Promise<ApiResponse> {
    const url = new URL(`${baseUrl.replace(/\/+$/, '')}${request.path}`);
    for (const [key, value] of Object.entries(request.query ?? {})) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
    const body = request.rawBody ?? (request.jsonBody === undefined ? undefined : JSON.stringify(request.jsonBody));
    const headers: Record<string, string> = {
      accept: 'application/json',
      traceparent: newTraceparent(),
      ...(authToken ? { authorization: `Bearer ${authToken}` } : {}),
      ...(body === undefined ? {} : { 'content-type': request.contentType ?? 'application/json' }),
    };
    const response = await fetch(url, { method: request.method, headers, body });
    const bodyText = await response.text();
    return {
      status: response.status,
      headers: response.headers,
      bodyText,
      bodyJson: readJson(bodyText, response.headers, `${request.method} ${request.path}`),
    };
  }

  return { execute } as const;
}

export function parseBody<T>(schema: z.ZodType<T>, response: ApiResponse): T {
  const result = schema.safeParse(response.bodyJson);
  if (!result.success) {
    const issues = result.error.issues.map((issue) => `${issue.path.map(String).join('.') || '<root>'} ${issue.code}: ${issue.message}`);
    throw new Error(`Response body does not match the schema: ${issues.join('; ')}. Body: ${response.bodyText}`);
  }
  return result.data;
}

function readJson(bodyText: string, headers: Headers, call: string): unknown {
  if (bodyText === '' || !headers.get('content-type')?.includes('json')) {
    return undefined;
  }
  try {
    return JSON.parse(bodyText);
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new Error(`${call} returned a JSON content type with a body that does not parse: ${bodyText}`);
    }
    throw error;
  }
}
