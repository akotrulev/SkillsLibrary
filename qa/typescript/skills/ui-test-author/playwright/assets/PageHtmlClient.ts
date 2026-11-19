import type { APIRequestContext } from '@playwright/test';

export type PageHtml = {
  readonly status: number;
  readonly cacheControl: string;
  readonly markup: string;
};

export class PageHtmlClient {
  constructor(private readonly request: APIRequestContext) {}

  async get(route: string): Promise<PageHtml> {
    const response = await this.request.get(route);
    const body = await response.text();
    return {
      status: response.status(),
      cacheControl: response.headers()['cache-control'] ?? '',
      markup: body.replace(/<script[\s\S]*?<\/script>/gi, ''),
    };
  }
}
