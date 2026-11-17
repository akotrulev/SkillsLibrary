# Recommended package layouts — page objects (Java)

The trees `page-object-design` designs toward. Pages, region and control components, and flows sit in the
packages shown; the rules are `qa-java-page-objects.md`.

## Playwright Java (single web app)

```
src/test/java/com/{org}/uitests/
├── support/
│   ├── BaseTest.java               ← the one lifecycle (ui-test-author/playwright assets)
│   └── AuthSetup.java              ← signed-in state, once per suite run
├── pages/
│   ├── LoginPage.java
│   ├── catalog/
│   │   ├── ProductListPage.java
│   │   └── ProductCard.java        ← component, takes Locator parent
│   └── checkout/
│       ├── InformationPage.java
│       ├── OverviewPage.java
│       └── CompletePage.java
├── components/
│   ├── NavigationMenu.java         ← region component on every page
│   └── controls/                   ← design-system widgets, at first use
│       ├── DatePicker.java
│       ├── Dropdown.java
│       ├── DataGrid.java
│       ├── GridRow.java
│       └── Toast.java
├── flows/
│   └── CheckoutFlow.java           ← takes its pages in the constructor
└── tests/
    └── CheckoutTest.java           ← seeds its data in its own @BeforeMethod
```

## Selenium Java / Appium Java (multi-platform)

```
src/test/java/com/{org}/uitests/
├── BaseTest.java
├── driver/
│   ├── DriverFactory.java          ← ThreadLocal<WebDriver>
│   └── AppiumDriverFactory.java
├── pom/
│   ├── BasePage.java
│   ├── web/
│   │   ├── LoginPage.java
│   │   └── …
│   └── mobile/
│       ├── BaseAppiumPage.java
│       ├── LoginPage.java
│       └── …
├── components/
│   ├── ProductCard.java            ← region component, root WebElement
│   └── controls/
│       └── Dropdown.java           ← wraps Selenium's Select
└── flows/
    └── CheckoutFlow.java
```
