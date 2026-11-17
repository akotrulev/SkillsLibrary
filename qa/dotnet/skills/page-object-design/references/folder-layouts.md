# Folder layouts — `qa-dotnet:page-object-design`

The recommended trees the architecture sketch starts from; `SKILL.md` § Core decisions says what goes in each folder.

## Playwright .NET (single web app)

```
UiTests/
├── UiTests.csproj
├── ui.runsettings               ← browser, headless, expect timeout, test-id attribute
├── AuthSetup.cs                 ← root namespace: signed-in state, once per run
├── Support/
│   └── BaseTest.cs              ← the one lifecycle (ui-test-author/playwright assets)
├── Pages/
│   ├── LoginPage.cs
│   ├── Catalog/
│   │   ├── ProductListPage.cs
│   │   └── ProductCard.cs       ← component, takes ILocator parent
│   └── Checkout/
│       ├── InformationPage.cs
│       ├── OverviewPage.cs
│       └── CompletePage.cs
├── Components/                  ← region components shared across features
│   ├── NavigationMenu.cs
│   └── Controls/                ← design-system widgets, at first use
│       ├── DatePicker.cs
│       ├── Dropdown.cs
│       ├── DataGrid.cs
│       ├── GridRow.cs
│       └── Toast.cs
├── Flows/
│   └── CheckoutFlow.cs
└── Tests/
    └── CheckoutTests.cs         ← seeds its data in its own [SetUp]
```

Configuration lives in the `.runsettings`; there is no `playwright.config.ts` in a .NET project.

## Selenium .NET / Appium .NET (multi-platform)

```
UiTests/
├── BaseTest.cs
├── Driver/
│   ├── DriverFactory.cs         ← AsyncLocal<IWebDriver>
│   └── AppiumDriverFactory.cs
├── Pages/
│   ├── BasePage.cs
│   ├── Web/
│   │   ├── LoginPage.cs
│   │   └── …
│   └── Mobile/
│       ├── BaseAppiumPage.cs
│       ├── LoginPage.cs
│       └── …
├── Components/
│   └── Controls/
└── Flows/
    └── CheckoutFlow.cs
```
