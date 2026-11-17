import { expect, test as base } from './fixtures';
import { ProductPage } from './ProductPage';

const addToCart = 'add_to_cart';
const sku = 'sku-123';
const timeout = 10_000;

const test = base.extend<{ productPage: ProductPage }>({
  productPage: async ({ page }, use) => {
    const productPage = new ProductPage(page);
    await productPage.goto(sku);
    await expect
      .poll(() => productPage.toolNames(timeout), { timeout, message: `${addToCart} registered on the product page` })
      .toContain(addToCart);
    await use(productPage);
  },
});

test.use({ launchOptions: { args: ['--enable-features=WebMCP'] } });

test.describe('WebMCP add_to_cart', { tag: '@webmcp' }, () => {
  test('Should_DeclareAnObjectSchema_When_AddToCartIsRegistered', async ({ productPage }) => {
    const tool = await productPage.tool(addToCart, timeout);

    expect(tool?.inputSchema, `${addToCart} inputSchema`).toMatchObject({ type: 'object', required: ['sku', 'quantity'] });
  });

  test('Should_MarkAddToCartConsequential_When_AddToCartIsRegistered', async ({ productPage }) => {
    const tool = await productPage.tool(addToCart, timeout);

    expect(tool?.annotations, `${addToCart} annotations`).toMatchObject({ consequential: true });
  });

  test('Should_UpdateCartBadge_When_AddToCartIsCalledWithValidInput', async ({ productPage }) => {
    await productPage.callTool(addToCart, { sku, quantity: 2 }, timeout);

    await expect(productPage.cartBadge, `cart badge after ${addToCart}`).toHaveText('2');
  });

  test('Should_ReturnIsError_When_QuantityIsNegative', async ({ productPage }) => {
    const result = await productPage.callTool(addToCart, { sku, quantity: -1 }, timeout);

    expect(result, `${addToCart} result for quantity -1`).toMatchObject({ isError: true });
  });

  test('Should_DropAddToCart_When_UserLeavesTheProductPage', async ({ productPage, homePage }) => {
    await homePage.goto();

    await expect
      .poll(() => productPage.toolNames(timeout), { timeout, message: 'tools after leaving the product page' })
      .not.toContain(addToCart);
  });
});
