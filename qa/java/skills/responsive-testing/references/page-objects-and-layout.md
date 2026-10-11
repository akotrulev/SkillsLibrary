# Page objects and the `Layout` helper — `qa-java:responsive-testing`

The responsive tests in `SKILL.md` reach the page only through these classes, built in the test class's own
`@BeforeMethod` after `BaseTest` has opened the page (`ui-test-author/playwright/references/lifecycle.md` §2).
Page objects expose **variant intent and locators**, never boxes. `Layout` **measures and returns numbers**; it
never asserts, so a failing test prints the measured value.

## `Breakpoints` — the one place widths live

A mirror of the app's own breakpoint source (Tailwind `screens` / `@theme`, the MUI theme, Bootstrap's
`$grid-breakpoints`, or the tokens file). Update it when design moves a breakpoint; no test holds a width literal.

```java
package com.example.uitests.responsive;

public final class Breakpoints {
    public static final int SM = 640;
    public static final int MD = 768;
    public static final int LG = 1024;
    public static final int XL = 1280;
    public static final int HEIGHT = 720;

    private Breakpoints() {
    }
}
```

## Page objects

The test ids are the PascalCase, variant-suffixed ids the frontend's responsive-design skill generates
(`frontend/react/skills/responsive-design`): `Nav.Desktop` / `Nav.Hamburger`. Each page object's `open()`
returns once its ready signal is visible — a wait, not an assertion — so a measurement taken after it reads a
rendered page.

```java
package com.example.uitests.responsive;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.AriaRole;

public final class AppShell {
    private final Page page;
    private final Locator main;

    public AppShell(Page page) {
        this.page = page;
        this.main = page.getByRole(AriaRole.MAIN);
    }

    public void open() {
        page.navigate("/");
        main.waitFor();
    }

    public Locator nav(NavVariant variant) {
        return page.getByTestId(variant.testId()).describe(variant.testId() + " navigation");
    }

    public enum NavVariant {
        DESKTOP("Nav.Desktop"),
        HAMBURGER("Nav.Hamburger");

        private final String testId;

        NavVariant(String testId) {
            this.testId = testId;
        }

        public String testId() {
            return testId;
        }
    }
}
```

```java
package com.example.uitests.responsive;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;

public final class ProductsPage {
    private final Page page;
    private final Locator cards;
    private final Locator filters;
    private final Locator results;

    public ProductsPage(Page page) {
        this.page = page;
        this.cards = page.getByTestId("ProductGrid.Card").describe("Product cards");
        this.filters = page.getByTestId("Products.Filters").describe("Filters panel");
        this.results = page.getByTestId("Products.Results").describe("Results panel");
    }

    public void open() {
        page.navigate("/products");
        cards.first().waitFor();
    }

    public Locator cards() {
        return cards;
    }

    public Locator filters() {
        return filters;
    }

    public Locator results() {
        return results;
    }
}
```

## `Layout` — measure, never assert

```java
package com.example.uitests.responsive;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.BoundingBox;

import java.util.List;

public final class Layout {
    public static final double TOLERANCE_PX = 1.0;

    private final Page page;

    public Layout(Page page) {
        this.page = page;
    }

    public void resizeTo(int width) {
        page.setViewportSize(width, Breakpoints.HEIGHT);
    }

    public int horizontalOverflow() {
        return ((Number) page.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")).intValue();
    }

    public long columnCount(Locator cards) {
        List<BoundingBox> boxes = cards.all().stream().map(Locator::boundingBox).toList();
        double firstRowTop = boxes.stream().mapToDouble(box -> box.y).min().orElseThrow();
        return boxes.stream().filter(box -> Math.abs(box.y - firstRowTop) <= TOLERANCE_PX).count();
    }

    public double leftEdgeSpread(List<Locator> elements) {
        List<Double> edges = elements.stream().map(element -> element.boundingBox().x).toList();
        return edges.stream().mapToDouble(Double::doubleValue).max().orElseThrow()
                - edges.stream().mapToDouble(Double::doubleValue).min().orElseThrow();
    }

    public double overlapDepth(Locator first, Locator second) {
        BoundingBox a = first.boundingBox();
        BoundingBox b = second.boundingBox();
        double horizontal = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
        double vertical = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
        return Math.max(0, Math.min(horizontal, vertical));
    }
}
```

- `boundingBox()` returns `null` for an element that is not visible; `open()` waits for the content first, and
  the tests assert a variant marker visible before measuring after a resize.
- `overlapDepth` is `0` when the boxes are separated, so the expected value is `≤ TOLERANCE_PX` (sub-pixel
  rendering), never an exact coordinate.
- `scrollWidth` is never below `clientWidth`, so `horizontalOverflow()` has one expected value: `0`.
