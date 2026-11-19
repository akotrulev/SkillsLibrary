import { expect, test } from './fixtures';

test.describe('Orders rendering', { tag: '@regression' }, () => {
  test('Should_RenderOrdersGridInRawHtml_When_OrdersPageIsServerRendered', async ({ pageHtml }) => {
    const html = await pageHtml.get('/orders');

    expect(html.markup, 'raw HTML of /orders').toContain('data-testid="Orders.Grid"');
  });

  test('Should_MarkOrdersHtmlPrivate_When_OrdersPageIsPersonalised', async ({ pageHtml }) => {
    const html = await pageHtml.get('/orders');

    expect(html.cacheControl, 'Cache-Control of /orders').toContain('private');
  });
});
