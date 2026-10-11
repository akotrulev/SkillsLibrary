---
name: qa-python-web-testing
description: Use when driving a locally running web app through Playwright from Python to verify frontend behavior interactively — browser screenshots, console logs, ad-hoc UI debugging. qa's one Python-based skill. Triggers "open the local app and check X", "screenshot this page", "what is the browser console showing", "debug this UI behavior with Python". Not for authoring a maintained UI suite, page objects, or a POM from a URL (`ui-test-author/playwright`, `page-objects-from-url`).
---

# Web Application Testing (Python / Playwright 1.63)

> **Scope / when to use this vs the stack-native Playwright skills.** This is a **Python** toolkit for *ad-hoc,
> throwaway* browser automation — quickly driving a local web app to verify frontend behavior, debug UI, capture
> screenshots, or read browser logs *inside a Claude session*. It is **not** the way to author a maintained UI
> test suite. For a project's regression/E2E suite, use the **stack-native** skills, which produce page objects,
> fixtures and CI-runnable tests in the project's own language and runner:
> - `qa/typescript/skills/ui-test-author/playwright` · `qa/dotnet/skills/ui-test-author/playwright` ·
>   `qa/java/skills/ui-test-author/playwright` — the maintained web UI suites (owned by the `qa-ui-{stack}`
>   agents), plus `page-object-design` / `page-objects-from-url` for POMs.
>
> **Rule of thumb:** reach for *this* skill when Claude needs to poke a running app once and report back; reach
> for the stack skill when the tests live in the repo and run in the pipeline.

## Versions

| Package | Pin | Note |
|---|---|---|
| `playwright` | `playwright==1.63.0` | Python 1.64 is not on PyPI yet; stay on 1.63 until it is |
| `pytest-playwright` | `pytest-playwright==0.10.0` | only when a script becomes a pytest check (below) |
| Python | **3.10 or newer** | required since Playwright 1.61 (PyPI `requires_python`); the docs page that still says 3.8 is stale |
| Docker image | `mcr.microsoft.com/playwright/python:v1.63.0-noble` | the tag always equals the package version |

```bash
python -m pip install playwright==1.63.0
python -m playwright install --with-deps chromium
```

A 1.64-only API (`locator.within(...)`, `page.get_by_ref(...)`, video `fps`) does not exist on 1.63 — trust the
installed version over the docs page.

**Helper script**: `scripts/with_server.py` manages server lifecycle (one or more servers). **Run it with
`--help` first** and call it as a black box; read the source only if `--help` shows a customized solution is
needed.

## The house rules for these scripts

These scripts are throwaway, but they follow the same wait and locator rules as every suite in this library — a
script that sleeps or waits for the network gives a wrong answer as easily as a test does.

| Never | Instead |
|---|---|
| `page.wait_for_load_state('networkidle')` | `expect(locator).to_be_visible()` on the element that proves the page rendered. `networkidle` is discouraged by Playwright: polling, analytics and websockets keep the network busy (it hangs) or idle too early (it races) |
| `page.wait_for_timeout(1000)` | `expect(...)` on the state the action should produce — it waits exactly as long as needed and fails with the locator it waited for |
| `page.wait_for_selector('.x')` | a locator plus `expect(locator).to_be_visible()` / `.to_have_text(...)` / `.to_have_count(...)` |
| `page.click('text=Dashboard')`, `page.fill('#name', ...)` | locator actions: `page.get_by_role("link", name="Dashboard").click()`, `page.get_by_label("Name").fill(...)` |
| `:visible` in a selector | `locator.filter(visible=True)` |
| Writing to `/tmp` or `/mnt/user-data/outputs` | files **under the project**: `evidence/<YYYY-MM-DD>-<topic>/` (create it with `Path.mkdir(parents=True, exist_ok=True)`). `evidence/` is git-ignored — screenshots and traces can carry tokens |

**Locator order**: `get_by_test_id` → `get_by_role` (with `name`) → `get_by_label` → `get_by_placeholder` →
`get_by_text` → `get_by_alt_text` / `get_by_title` → CSS as the last resort.

## Decision tree: choosing your approach

```
User task → Is it static HTML?
    ├─ Yes → Read the HTML file to pick locators (labels, roles, test ids)
    │         ├─ Success → Write a Playwright script with those locators
    │         └─ Fails/incomplete → Treat as dynamic (below)
    │
    └─ No (dynamic webapp) → Is the server already running?
        ├─ No → python scripts/with_server.py --help
        │        then run your script through the helper
        │
        └─ Yes → Reconnaissance-then-action:
            1. Navigate, then expect(<ready element>).to_be_visible()
            2. Take a screenshot or list roles/test ids
            3. Pick locators from the rendered state
            4. Act with those locators; expect(...) the result of each step
```

## Example: using `with_server.py`

```bash
python scripts/with_server.py --server "npm run dev" --port 5173 -- python your_automation.py
```

```bash
python scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python your_automation.py
```

The servers' output goes to `evidence/servers/server-<n>.log`. The automation script holds only Playwright logic —
the helper has already waited for every port:

```python
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

OUTPUT = Path("evidence") / "2026-10-11-checkout"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page()
    page.goto("http://localhost:5173")
    expect(page.get_by_role("main")).to_be_visible()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=OUTPUT / "home.png", full_page=True)
    browser.close()
```

`chromium.launch()` is headless by default. Replace `get_by_role("main")` with whatever element proves *your*
page rendered — a heading, a test id, the first row of a list.

## Reconnaissance-then-action

1. **Inspect the rendered page** once its ready element is visible: a full-page screenshot into the evidence
   folder, `page.get_by_role("button").all_inner_texts()`, or `page.locator("body").aria_snapshot()` for the
   accessible tree (roles and names are the locators you will use).
2. **Pick locators** from what you saw, in the locator order above.
3. **Act**, and after each action `expect(...)` the state it should produce before the next one.

## From a script to a check (pytest-playwright 0.10.0)

When the same verification will be run again, make it a pytest file and let the plugin keep the evidence:

```ini
[pytest]
addopts = --tracing=retain-on-failure --video=retain-on-failure --screenshot=only-on-failure --full-page-screenshot --output=test-results
```

- `--tracing` and `--video` take only `on`, `off` or `retain-on-failure` in 0.10.0; `--screenshot` takes `on`,
  `off` or `only-on-failure`. Kept files land under `test-results/` per test.
- Open a kept trace with `playwright show-trace test-results/<test>/trace.zip`, or drop it on
  https://trace.playwright.dev, which loads it in the browser without uploading it.
- A check that must run in a pipeline is no longer ad hoc: move it to the stack-native skill.

## Reference files

- `examples/element_discovery.py` — lists the visible buttons, links and form fields after the page is ready,
  and saves a full-page screenshot under `evidence/`.
- `examples/static_html_automation.py` — drives a local HTML file through `Path.as_uri()`, fills a form with
  label locators, and waits for the result before the second screenshot.
- `examples/console_logging.py` — records console messages while it navigates, waits for the dashboard heading
  instead of a timeout, and writes the log under `evidence/`.

Each example names its own ready and result locators (`get_by_role("main")`, `get_by_role("status")`, the
"Dashboard" heading); change them to the elements your page shows.
