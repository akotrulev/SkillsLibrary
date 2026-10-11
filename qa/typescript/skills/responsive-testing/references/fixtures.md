# Responsive fixtures — page objects and the `Layout` measuring helper (TypeScript / Playwright 1.64)

`responsive.fixtures.ts` extends the writer's `fixtures.ts`
(`qa/typescript/skills/ui-test-author/playwright/assets/fixtures.ts`). Page objects expose variant intent
(`appShell.nav('Hamburger')`), never boxes. Geometry lives in `Layout`: it **measures and returns numbers**,
and the test asserts — no `expect` and no loop of assertions inside a helper, so a failure reports the measured
value. Test ids follow the frontend rule (PascalCase, dot-separated): the ids `fe-react`'s responsive-design
skill generates (`Nav.Desktop` / `Nav.Hamburger`).

```typescript
import type { Locator, Page } from '@playwright/test';
import { HEIGHT } from './breakpoints';
import { test as base } from './fixtures';

export type NavVariant = 'Desktop' | 'Hamburger';

type Box = { readonly x: number; readonly y: number; readonly width: number; readonly height: number };

export const TOLERANCE_PX = 1;

export class AppShell {
  constructor(private readonly page: Page) {}

  async open(): Promise<void> {
    await this.page.goto('/');
  }

  nav(variant: NavVariant): Locator {
    return this.page.getByTestId(`Nav.${variant}`);
  }
}

export class ProductsPage {
  readonly cards: Locator;
  readonly filters: Locator;
  readonly results: Locator;

  constructor(private readonly page: Page) {
    this.cards = page.getByTestId('ProductGrid.Card');
    this.filters = page.getByTestId('Products.Filters');
    this.results = page.getByTestId('Products.Results');
  }

  async open(): Promise<void> {
    await this.page.goto('/products');
  }
}

export class Layout {
  constructor(private readonly page: Page) {}

  async resizeTo(width: number): Promise<void> {
    await this.page.setViewportSize({ width, height: HEIGHT });
  }

  async horizontalOverflow(): Promise<number> {
    return this.page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  }

  async columnCount(cards: Locator): Promise<number> {
    const boxes = await Promise.all((await cards.all()).map((card) => this.box(card)));
    const firstRowY = Math.min(...boxes.map((box) => box.y));
    return boxes.filter((box) => Math.abs(box.y - firstRowY) <= TOLERANCE_PX).length;
  }

  async leftEdgeSpread(locators: readonly Locator[]): Promise<number> {
    const edges = await Promise.all(locators.map(async (locator) => (await this.box(locator)).x));
    return Math.max(...edges) - Math.min(...edges);
  }

  async overlapDepth(a: Locator, b: Locator): Promise<number> {
    const [first, second] = await Promise.all([this.box(a), this.box(b)]);
    const across = Math.min(first.x + first.width, second.x + second.width) - Math.max(first.x, second.x);
    const down = Math.min(first.y + first.height, second.y + second.height) - Math.max(first.y, second.y);
    return Math.max(0, Math.min(across, down));
  }

  private async box(locator: Locator): Promise<Box> {
    const box = await locator.boundingBox();
    if (box === null) {
      throw new Error(`${locator} has no bounding box: it is not rendered`);
    }
    return box;
  }
}

export const test = base.extend<{ appShell: AppShell; productsPage: ProductsPage; layout: Layout }>({
  appShell: async ({ page }, use) => {
    await use(new AppShell(page));
  },
  productsPage: async ({ page }, use) => {
    await use(new ProductsPage(page));
  },
  layout: async ({ page }, use) => {
    await use(new Layout(page));
  },
});

export { expect } from './fixtures';
```

| Member | Returns | Asserted as |
|---|---|---|
| `columnCount(cards)` | cards sharing the first row's `y` (± tolerance) | `expect.poll(…).toBe(row.columns)` |
| `horizontalOverflow()` | `scrollWidth - clientWidth` of the document; never below `0` | `expect.poll(…).toBe(0)` |
| `leftEdgeSpread([a, b, c])` | widest minus narrowest left edge | `expect.poll(…).toBeLessThanOrEqual(TOLERANCE_PX)` |
| `overlapDepth(a, b)` | how far two boxes overlap on their shallower axis — `0` apart, sub-pixel when they touch | `expect.poll(…).toBeLessThanOrEqual(TOLERANCE_PX)` |
| `resizeTo(width)` | — | live-resize specs only |

- `boundingBox()` returns `null` for an element that is not rendered; `box()` turns that into an error that
  names the locator (its `describe()` text when it has one [1.53]) instead of a `null` dereference.
- `${locator}` prints the locator's description [1.57], so name a locator with `.describe('…')` when its
  selector does not say what it is.
- `Layout` is the only place a responsive suite calls `page` directly; specs reach the page through these
  fixtures.
