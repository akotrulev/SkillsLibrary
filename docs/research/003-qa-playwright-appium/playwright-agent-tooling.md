# Playwright for AI agents: MCP, Test Agents and CLI (research, 2026-10-10)

Primary sources were fetched on 2026-10-10. Where a claim comes from reading shipped code, the npm tarball file is cited: `playwright-core@1.64.0/lib/coreBundle.js`, `playwright@1.64.0/lib/...` and `@playwright/mcp@0.0.83/...`. Those tarballs were downloaded and grepped directly. A GitHub `src/` path that appears beside a claim is the path the bundle's own module comment names; it was not fetched on its own. **UNVERIFIED** marks anything no primary source confirmed.

---

## 0. Headline findings

- **None of the 14 Playwright MCP tool names the library grants have been removed.** `browser_generate_locator`, `browser_storage_state` and `browser_set_storage_state` still exist in @playwright/mcp 0.0.83 and Playwright 1.64.0. They are **opt-in**: `browser_generate_locator` needs `--caps=testing`, and the two storage tools need `--caps=storage`. The local server is registered as `npx -y @playwright/mcp@latest` with no args (`~/.claude.json` → `mcpServers.playwright`), so only the core tools appear. That is why those three names are missing here.
  Sources: https://github.com/microsoft/playwright-mcp/blob/main/README.md (Tools → "Storage (opt-in via --caps=storage)" and "Test assertions (opt-in via --caps=testing)"); `playwright-core@1.64.0/lib/coreBundle.js` (`filteredTools()`, which keeps a tool only if its capability starts with `core` or is listed in `config.capabilities`, then drops `skillOnly` tools).
- The tools and flags that were really renamed or removed in 2025–2026: `browser_tab_*` → `browser_tabs`, `browser_navigate_forward` (removed), `browser_install` (removed), `browser_run_code` → `browser_run_code_unsafe`, the `--caps=verify` and `--caps=tracing` groups, the `--save-trace` and `--save-video` flags, `--output-mode`, and `--snapshot-mode=incremental`. See §2.
- Microsoft's current guidance for **coding agents** is the **`playwright-cli` + SKILLS** route. MCP is kept for "specialized agentic loops … exploratory automation, self-healing tests, or long-running autonomous workflows" (https://github.com/microsoft/playwright-mcp/blob/main/README.md, section "Playwright MCP vs Playwright CLI"; https://playwright.dev/docs/getting-started-cli).

---

## 1. Versions (as of 2026-10-10)

| Package | Latest | Date | Source |
|---|---|---|---|
| `@playwright/mcp` | **0.0.83** (`next` = 0.0.79-alpha…) | 2026-09-28 | https://registry.npmjs.org/@playwright/mcp · https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.83 |
| `@playwright/mcp` 0.0.83 depends on | `playwright`/`playwright-core` `1.64.0-alpha-1790635538000` | | `@playwright/mcp@0.0.83/package.json` |
| `playwright` / `@playwright/test` | **1.64.0** | 2026-10-07 | https://github.com/microsoft/playwright/releases/tag/v1.64.0 · https://registry.npmjs.org/playwright-core |
| `@playwright/cli` (bin `playwright-cli`) | **0.1.22** | 2026-09-28 | https://registry.npmjs.org/@playwright/cli · https://www.npmjs.com/package/@playwright/cli |

- The MCP server code now lives in `microsoft/playwright` (`packages/playwright-core/src/tools/…`). `@playwright/mcp`'s `cli.js` is a thin wrapper that calls `tools.decorateMCPCommand` from `playwright-core/lib/coreBundle`. Source: `@playwright/mcp@0.0.83/cli.js`.
- Since **Playwright 1.62**, Playwright bundles the MCP server and `playwright-cli`, runnable as `npx playwright mcp` and `npx playwright cli`. Source: https://github.com/microsoft/playwright/releases/tag/v1.62.0 ("Command line & MCP").
- `npx @playwright/mcp install-browser [browser]` installs browsers. This subcommand replaced the old `browser_install` tool. Source: `@playwright/mcp@0.0.83/cli.js` (`process.argv.includes('install-browser')`); present since 0.0.69 (`@playwright/mcp@0.0.69/cli.js`).

---

## 2. Mapping: old tool and flag names → current names

### 2a. Names the library's agents grant today

Found by grepping `qa/*/agents/qa-ui-*.md`, `qa/*/agents/qa-bdd-*.md`, `qa/*/skills/page-objects-from-url/SKILL.md`, `frontend/*/agents/fe-*.md` and `design/agents/design-auditor.md`.

| Granted name (`mcp__playwright__…`) | Status in 0.0.83 / PW 1.64 | Capability flag needed | Source |
|---|---|---|---|
| `browser_navigate` | current | core (always on) | README Tools → Core automation |
| `browser_snapshot` | current. Params: `target`, `filename`, `depth`, `boxes` | core | README |
| `browser_evaluate` | current. Params: `function`, `target`, `element`, `filename`. Accepts plain expressions since 0.0.71 | core | README; https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.71 |
| `browser_click` | current. `target` = ref **or a CSS/text selector** (since 0.0.69); `doubleClick`, `button`, `modifiers` | core | README; https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.69 |
| `browser_type` | current. `target`, `text`, `submit`, `slowly` | core (`core-input`) | README |
| `browser_fill_form` | current (added 0.0.35) | core | README; https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.35 |
| `browser_select_option` | current | core | README |
| `browser_handle_dialog` | current. `accept`, `promptText` | core | README |
| `browser_wait_for` | current. `time` (≤30 s), `text`, `textGone` | core | README; https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.83 |
| `browser_take_screenshot` | current. `filename`, `type` (png/jpeg/webp), `fullPage`, `scale` (css/device), `target`, `element` | core | README; releases v0.0.77, v0.0.79 |
| `browser_resize` | current | core | README |
| `browser_generate_locator` | **current, opt-in.** Not removed | **`--caps=testing`** | README "Test assertions (opt-in via --caps=testing)"; `coreBundle.js` (`capability: "testing"`) |
| `browser_storage_state` | **current, opt-in.** Saves cookies and localStorage to `filename` (default `storage-state-{timestamp}.json` in the output dir) | **`--caps=storage`** | README "Storage (opt-in via --caps=storage)" |
| `browser_set_storage_state` | **current, opt-in.** Restores from `filename` and **clears existing cookies and localStorage first** | **`--caps=storage`** | README |

### 2b. Renames and removals, 2025-08 → 2026-10

| Old name | What happened | Current replacement | Source |
|---|---|---|---|
| `browser_tab_list`, `browser_tab_new`, `browser_tab_select`, `browser_tab_close` | merged into one tool in 0.0.35 (2025-08-24) | `browser_tabs` with `action` = list/new/close/select | `@playwright/mcp@0.0.34` README (old names); https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.35 ("merge tabs tool into one") |
| `browser_navigate_forward` | removed from MCP in 0.0.35 "due to low usage counts". Still exists in code as `skillOnly`, so it is CLI-only | MCP: none. CLI: `playwright-cli go-forward` | release v0.0.35; `coreBundle.js` (`skillOnly: true`) |
| `browser_install` | removed in 0.0.69 (2026-03-30). The "Browser installation" README section is now empty | `npx @playwright/mcp install-browser` / `npx playwright install` / `playwright-cli install-browser` | READMEs of 0.0.68 (present) and 0.0.69 (absent) on npm; `@playwright/mcp@0.0.83/cli.js` |
| `browser_verify_element_visible`, `browser_verify_list_visible`, `browser_verify_text_visible`, `browser_verify_value` | introduced 0.0.36 under `--caps=verify`. The group was renamed to **`--caps=testing`** by 0.0.47 | same names, `--caps=testing` | `@playwright/mcp@0.0.36` README ("Verify (opt-in via --caps=verify)"); 0.0.47 README ("Test assertions (opt-in via --caps=testing)") |
| `browser_generate_locator` | added by 0.0.47 under `--caps=testing`. **Still present** | same | 0.0.47 README; current README |
| `browser_start_tracing`, `browser_stop_tracing` | 0.0.40–0.0.58 under `--caps=tracing`. The section was empty in 0.0.62–0.0.68. Back under **`--caps=devtools`** since 0.0.69. `--caps=tracing` is still accepted and silently adds `devtools` | same names, `--caps=devtools` | 0.0.47 / 0.0.64 / 0.0.69 READMEs; `coreBundle.js` (`if (options.caps?.includes("tracing")) options.caps.push("devtools")`) |
| `browser_pdf_save` | unchanged | same, `--caps=pdf` | README "PDF generation (opt-in via --caps=pdf)" |
| `browser_run_code` | renamed in 0.0.72 (2026-04-30) | `browser_run_code_unsafe` ("RCE-equivalent") | https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.72 |
| `browser_network_requests` (one call returned everything) | 0.0.72: now returns a numbered list | `browser_network_requests` + `browser_network_request` (`index`, `part`, `filename`) | release v0.0.72 |
| `browser_webmcp_list`, `browser_webmcp_call` | added 0.0.81, dropped from MCP in 0.0.82 (now `skillOnly`, CLI-only) | dynamic MCP tools named `webmcp_<tool>` | https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.82 |
| `--save-trace` (boolean) | removed in 0.0.69. Not in the 1.64 option parser | `browser_start_tracing` / `browser_stop_tracing` (`--caps=devtools`) | 0.0.68 README (present) vs 0.0.69 (absent); `coreBundle.js` MCP option list |
| `--save-video=<WxH>` (e.g. `--save-video=800x600`, added 0.0.40) | removed in 0.0.69 | `browser_start_video` {`filename`, `size`:{`width`,`height`}, `fps`, `cursor`} / `browser_stop_video` (`--caps=devtools`) | https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.40; 0.0.69 README; current README |
| `--snapshot-mode=incremental` (the default from 0.0.51) | removed. Now only `full` (default) or `none` | `--snapshot-mode full\|none` | 0.0.64 README vs 0.0.69 README |
| `--output-mode file\|stdout` | removed in 0.0.79 | `filename` param on each tool; `--output-dir` | https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.79 |
| `--vision` | legacy; hidden; maps to `--caps=vision` with a deprecation warning | `--caps=vision` | `coreBundle.js` ("The --vision option is deprecated, use --caps=vision instead") |
| `--no-chromium-sandbox` | introduced 0.0.67, reverted in 0.0.68 | `--no-sandbox` | releases v0.0.67, v0.0.68 |

---

## 3. Playwright MCP: the complete current tool list (0.0.83 / PW 1.64)

Capability names come from `@playwright/mcp@0.0.83/config.d.ts`: `ToolCapability = 'config' | 'core' | 'core-navigation' | 'core-tabs' | 'core-input' | 'core-install' | 'network' | 'pdf' | 'storage' | 'testing' | 'vision' | 'devtools'`.
- Every capability starting with `core` is **always on**.
- The **opt-in values for `--caps=`** are `config, network, storage, testing, vision, pdf, devtools`. `--caps` is a plain comma-separated list with no validation (`commaSeparatedList`), and it is also settable through env `PLAYWRIGHT_MCP_CAPS` or config `capabilities: [...]`.
- **Doc defect:** the README's `--caps` row still says "possible values: vision, pdf, devtools", but the tool sections and the type list name config, network, storage and testing as well (README; `config.d.ts`; `coreBundle.js` `filteredTools`).

| Group | `--caps` | Tools (exact names) |
|---|---|---|
| Core automation | always on (`core`, `core-navigation`, `core-input`) | `browser_click`, `browser_close`, `browser_console_messages`, `browser_drag`, `browser_drop`, `browser_emulate_media`, `browser_evaluate`, `browser_file_upload`, `browser_fill_form`, `browser_find`, `browser_handle_dialog`, `browser_hover`, `browser_navigate`, `browser_navigate_back`, `browser_network_request`, `browser_network_requests`, `browser_press_key`, `browser_resize`, `browser_run_code_unsafe`, `browser_select_option`, `browser_snapshot`, `browser_take_screenshot`, `browser_type`, `browser_wait_for` |
| Tab management | always on (`core-tabs`) | `browser_tabs` |
| Browser installation | always on (`core-install`) | *(no tools; use `npx @playwright/mcp install-browser`)* |
| Configuration | `config` | `browser_get_config` |
| Network | `network` | `browser_network_state_set`, `browser_route`, `browser_route_list`, `browser_unroute` |
| Storage | `storage` | `browser_cookie_clear`, `browser_cookie_delete`, `browser_cookie_get`, `browser_cookie_list`, `browser_cookie_set`, `browser_localstorage_clear`, `browser_localstorage_delete`, `browser_localstorage_get`, `browser_localstorage_list`, `browser_localstorage_set`, `browser_sessionstorage_clear`, `browser_sessionstorage_delete`, `browser_sessionstorage_get`, `browser_sessionstorage_list`, `browser_sessionstorage_set`, `browser_set_storage_state`, `browser_storage_state` |
| DevTools (tracing, video, recording, debugging) | `devtools` (alias: `tracing`) | `browser_annotate`, `browser_hide_highlight`, `browser_highlight`, `browser_resume`, `browser_start_recording`, `browser_start_tracing`, `browser_start_video`, `browser_stop_recording`, `browser_stop_tracing`, `browser_stop_video`, `browser_video_chapter`, `browser_video_hide_actions`, `browser_video_show_actions` |
| Coordinate-based (vision) | `vision` | `browser_mouse_click_xy`, `browser_mouse_down`, `browser_mouse_drag_xy`, `browser_mouse_move_xy`, `browser_mouse_up`, `browser_mouse_wheel` |
| PDF | `pdf` | `browser_pdf_save` |
| Test assertions | `testing` | `browser_generate_locator`, `browser_verify_element_visible`, `browser_verify_list_visible`, `browser_verify_text_visible`, `browser_verify_value` |
| WebMCP (dynamic) | on by default; `--no-webmcp` turns it off | `webmcp_<sanitized page tool name>` (suffix `_2`, `_3`… on collisions), one per tool the current tab registers. Clients get a `tools/list_changed` notification when the set changes |

Source for the table: README "Tools" section (generated by `update-readme.js`); `coreBundle.js` tool definitions (`capability:` per tool); release v0.0.82 for WebMCP.

**CLI-only tools.** These are marked `skillOnly: true`, so `filteredTools` never exposes them over `@playwright/mcp`. They exist only as `playwright-cli` commands:
- `browser_check`, `browser_uncheck`
- `browser_keydown`, `browser_keyup`, `browser_press_sequentially`
- `browser_navigate_forward`, `browser_reload`
- `browser_console_clear`, `browser_network_clear`
- `browser_webmcp_list`, `browser_webmcp_call`

Source: `playwright-core@1.64.0/lib/coreBundle.js`.

**Tools added since 2025-08** (from the releases):
- 0.0.69: `browser_network_state_set`, `browser_video_chapter`, plus the whole storage, network and config groups
- 0.0.71: `browser_drop`
- 0.0.72: `browser_network_request`
- 0.0.76: `browser_video_show_actions` / `browser_video_hide_actions`
- 0.0.78: `browser_find`
- 0.0.80: `browser_start_recording` / `browser_stop_recording`
- 0.0.82: `browser_emulate_media`

Sources: https://github.com/microsoft/playwright-mcp/releases.

### 3a. Config flags relevant to QA (exact syntax, 0.0.83)

All flags below come from the README "Configuration" table, generated from the option parser. Every flag also has a `PLAYWRIGHT_MCP_*` environment variable.

| Flag | Syntax / values | Notes |
|---|---|---|
| `--caps <caps>` | `--caps=testing,storage,devtools` | opt-in groups listed above |
| `--save-session` | boolean | saves the MCP session log into the output dir |
| `--save-trace` | **removed (0.0.69)** | use `browser_start_tracing` / `browser_stop_tracing` |
| `--save-video` | **removed (0.0.69)**; was `--save-video=800x600` | use `browser_start_video` (`size` object, `fps`, default 25) |
| `--output-dir <path>` | path | only for *auto-named* outputs. An explicit `filename` resolves against the **workspace root**. Videos went under `outputDir/videos` from 0.0.55 |
| `--output-max-size <bytes>` | number | evicts old output files |
| `--file-paths <mode>` | `relative` (default) \| `absolute` | added 0.0.82 |
| `--isolated` | boolean | in-memory profile. The default is a **persistent** per-workspace profile at `~/Library/Caches/ms-playwright/mcp-{channel}-{workspace-hash}` (macOS) |
| `--storage-state <path>` | path | "for isolated sessions", e.g. `--isolated --storage-state=auth.json` |
| `--user-data-dir <path>` | path | persistent profile location |
| `--device <device>` | e.g. `"iPhone 15"` | cannot be combined with `--mobile` |
| `--mobile` | boolean | generic Pixel 10 (Chromium) / iPhone 17 (WebKit); added 0.0.78 |
| `--viewport-size <size>` | `"1280x720"` | |
| `--test-id-attribute <attribute>` | default `data-testid` | added 0.0.42; drives `getByTestId` in generated code |
| `--codegen <lang>` | `typescript` (default) \| `python` \| `java` \| `csharp` \| `none` | languages beyond TS since 0.0.79; the default is inferred from the environment since 0.0.80 |
| `--snapshot-mode <mode>` | `full` (default) \| `none` | controls the auto-snapshot attached to tool responses |
| `--snapshot-boxes` | boolean | adds `[box=x,y,w,h]` to each element |
| `--image-responses <mode>` | `allow` (default) \| `omit` \| `only` | `only` added 0.0.81 |
| `--console-level <level>` | `error` \| `warning` \| `info` \| `debug` | |
| `--init-script <path...>` | JS file(s) run before page scripts | repeatable |
| `--init-page <path...>` | TS file evaluated on the Playwright `page` | |
| `--extension` | boolean | attach to a running Chrome/Edge through the "Playwright Extension" / "Playwright MCP Bridge" |
| `--endpoint <endpoint>` | bound browser name or endpoint | pairs with `browser.bind()` (PW 1.59) |
| `--secrets <path>` | dotenv file | replaces secret values in responses; "not a security feature" |
| `--timeout-action` / `--timeout-navigation` / `--timeout-settle` | ms; defaults 5000 / 60000 / 500 | |
| `--idle-timeout <ms>` | default 1 h for headless, never for headed; `0` disables | added 0.0.81 |
| `--no-webmcp` | boolean (env `PLAYWRIGHT_MCP_WEBMCP=false`) | opts out of `webmcp_*` tools |
| `--headless`, `--browser`, `--grant-permissions`, `--ignore-https-errors`, `--allowed-origins`, `--blocked-origins`, `--allow-unrestricted-file-access`, `--shared-browser-context`, `--port`, `--host`, `--config` | | see README |

### 3b. WebMCP

- **Supported.** The tools a page registers through the experimental WebMCP API become MCP tools named `webmcp_<tool>`. They carry the page's own input schema, and annotations map to `readOnlyHint` / `destructiveHint`. The list follows the current tab. Results are labeled page-provided and **untrusted**. It is on by default; opt out with `--no-webmcp`, config `webmcp: false` or env `PLAYWRIGHT_MCP_WEBMCP=false`.
  Sources: https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.82; https://github.com/microsoft/playwright/releases/tag/v1.64.0; README `--no-webmcp`.
- Playwright reads `document.modelContext ?? navigator.modelContext`, lists tools with `getTools()`, and calls them with `invokeTool()` / `executeTool()`. Source: `coreBundle.js` (generated `webMCPSource.ts`).
- **The browser must have WebMCP enabled.** Playwright throws `WebMCP is not enabled. Launch the browser with the "--enable-features=WebMCP" argument.` (Firefox needs `dom.modelcontext.enabled` and `dom.modelcontext.testing.enabled` prefs). WebKit is unsupported. The 1.64 bundle has **no code that adds `--enable-features=WebMCP` automatically**, so pass it through config `browser.launchOptions.args`. Chrome's own docs say to enable `chrome://flags/#enable-webmcp-testing`, with an origin trial from Chrome 149.
  Sources: `coreBundle.js` (`server/webmcp.ts` `assertBrowserSupport`); https://developer.chrome.com/docs/ai/webmcp.
- Whether stock Chrome 155+ has WebMCP on without a flag: **UNVERIFIED**.
- Test-runner API, new in 1.64: `page.webmcp.tools()` and `page.webmcp.callTool(name, args)`, plus the `frame.webmcp` equivalents. Source: https://github.com/microsoft/playwright/releases/tag/v1.64.0.

---

## 4. Playwright Test Agents (planner / generator / healer)

**Introduced in 1.56.0 (2025-10-06)** as "Playwright Agents", later renamed "test agents" (1.56.1). Sources: https://github.com/microsoft/playwright/releases/tag/v1.56.0 and https://github.com/microsoft/playwright/releases/tag/v1.56.1 ("rename agents to test agents"); docs https://playwright.dev/docs/test-agents.

### 4a. Command

```
npx playwright init-agents --loop=<claude|codex|copilot|opencode|vscode|vscode-legacy> [--project <name>] [-c <config>] [--prompts]
```

- `--loop` choices in 1.64: `claude, codex, copilot, opencode, vscode, vscode-legacy`. Source: `playwright@1.64.0/lib/program.js` `addInitAgentsCommand`.
- History of the choices:
  - 1.56: `vscode, claude, opencode`
  - 1.58: adds `copilot` and `vscode-legacy`
  - 1.61: adds `codex`

  Source: `program.js` in each npm version.
- With no `--loop`, or with `vscode`/`copilot`, it runs the Copilot generator and writes `.github/agents/*.agent.md`. `vscode-legacy` writes the old `.github/chatmodes/*.chatmode.md`. Source: `program.js`; `lib/agents/generateAgents.js`.
- Docs: "agent definitions should be regenerated whenever Playwright is updated to pick up new tools and instructions." Source: https://playwright.dev/docs/test-agents.

### 4b. What `--loop=claude` generates

Source for every path below: `playwright@1.64.0/lib/agents/generateAgents.js` (`ClaudeGenerator`, `initRepo`).

| File | Content |
|---|---|
| `.claude/agents/playwright-test-planner.md`, `.claude/agents/playwright-test-generator.md`, `.claude/agents/playwright-test-healer.md` | Claude subagents with frontmatter `name`, `description`, `tools`, `model: sonnet`, `color` |
| `.mcp.json` | `{"mcpServers":{"playwright-test":{"command":"npx","args":["playwright","run-test-mcp-server"]}}}` (on Windows: `cmd /c npx …`) |
| `specs/README.md` | created if `specs/` is missing ("This is a directory for test plans.") |
| `<testDir>/seed.spec.ts` | created if no file in the primary project has `seed` in its name. Default body: `test.describe('Test group', () => { test('seed', async ({ page }) => { // generate code here. }); });` (`lib/mcp/test/seed.js`) |
| `.claude/prompts/{playwright-test-plan,playwright-test-generate,playwright-test-heal,playwright-test-coverage}.md` | only with `--prompts` (prompt templates, added 1.58) |

Tool-name mapping in the generated frontmatter:
- `search` → `Glob, Grep, Read, LS`
- `edit` → `Edit, MultiEdit, Write`
- `playwright-test/<tool>` → `mcp__playwright-test__<tool>`

### 4c. Agents and their tools (1.64, verbatim from `lib/agents/*.agent.md`)

- **playwright-test-planner**
  - Tools: `search` plus `playwright-test/` `browser_click`, `browser_close`, `browser_console_messages`, `browser_drag`, `browser_evaluate`, `browser_file_upload`, `browser_handle_dialog`, `browser_hover`, `browser_navigate`, `browser_navigate_back`, `browser_network_request`, `browser_network_requests`, `browser_press_key`, `browser_run_code_unsafe`, `browser_select_option`, `browser_snapshot`, `browser_take_screenshot`, `browser_type`, `browser_wait_for`, `planner_setup_page`, `planner_save_plan`.
  - Workflow: call `planner_setup_page` once, explore through snapshots ("Do not take screenshots unless absolutely necessary"), write happy-path, edge and negative scenarios that assume a fresh state, then save the plan with `planner_save_plan`, e.g. `specs/<x>.md`.
- **playwright-test-generator**
  - Tools: `search` plus `browser_click`, `browser_drag`, `browser_evaluate`, `browser_file_upload`, `browser_handle_dialog`, `browser_hover`, `browser_navigate`, `browser_press_key`, `browser_select_option`, `browser_snapshot`, `browser_type`, `browser_verify_element_visible`, `browser_verify_list_visible`, `browser_verify_text_visible`, `browser_verify_value`, `browser_wait_for`, `generator_read_log`, `generator_setup_page`, `generator_write_test`.
  - Workflow: run `generator_setup_page`, then execute each plan step live, passing the step text as `intent`. Then call `generator_read_log` and immediately `generator_write_test`.
  - Output rules: one test per file; a `describe` matching the plan group; a `// N. step` comment before each step; a `// spec:` / `// seed:` header.
- **playwright-test-healer**
  - Tools: `search`, `edit` plus `browser_console_messages`, `browser_evaluate`, `browser_generate_locator`, `browser_network_request`, `browser_network_requests`, `browser_snapshot`, `test_debug`, `test_list`, `test_run`.
  - Workflow: `test_run`, then `test_debug` each failure (it pauses on the error), inspect with the browser tools, edit, and re-run. If the test is correct but the app is broken, mark it `test.fixme()` with a comment. Its rules include "Never wait for networkidle".
- Changes from 1.56 to 1.64 in the agents' tool lists:
  - the planner gained `browser_run_code_unsafe`, `browser_network_request` and `planner_save_plan`
  - the healer gained `browser_network_request`
  - agent files were renamed `playwright-test-*.agent.md` (1.58)

  Sources: `playwright@1.56.1/lib/agents/{planner,generator,healer}.md` vs `playwright@1.64.0/lib/agents/*.agent.md`.

### 4d. The test MCP server (`npx playwright run-test-mcp-server`)

- Hidden command. Options: `--headless`, `-c, --config <file>`, `--host`, `--port`. Server name "Playwright Test Runner". Source: `playwright@1.64.0/lib/program.js` `addTestMCPServerCommand`.
- Its own tools: `planner_setup_page`, `planner_submit_plan`, `planner_save_plan`, `generator_setup_page`, `generator_read_log`, `generator_write_test`, `test_list`, `test_run` (`locations[]`, `projects[]`), `test_debug` (`test.id`, `test.title`). Source: `lib/mcp/test/{plannerTools,generatorTools,testTools,testBackend}.js`.
- **It also exposes every `browser_*` tool, unfiltered.** That covers all capability groups, including `browser_generate_locator`, `browser_verify_*`, storage and devtools, and even the `skillOnly` tools; no `--caps` is needed. Action, input and assertion tools gain a required `intent` string. Every browser call is relayed to a paused test (`sendMessageToPausedTest`) and fails with "Must setup test before interacting with the page" until `planner_setup_page`, `generator_setup_page` or `test_debug` has paused a test. Source: `lib/mcp/test/testBackend.js` (`...tools.browserTools.map(wrapBrowserTool)`); `lib/mcp/test/testContext.js`.
- Plan format: `planner_submit_plan` takes the structure overview → suites[] {name, seedFile, tests[] {name, file, steps[] {perform, expect[]}}}. Source: `lib/mcp/test/plannerTools.js`.

### 4e. CLI-based plan → generate → heal (the newer route)

- The bundled `playwright-cli` skill has a reference `test-generation.md` covering the same three phases without MCP:
  - run `PLAYWRIGHT_HTML_OPEN=never npx playwright test tests/seed.spec.ts --debug=cli` in the background
  - wait for "Debugging Instructions" and the session `tw-XXXX`
  - `playwright-cli attach tw-XXXX`, then `resume` / `step-over` / `pause-at <file:line>`
  - every CLI action prints the equivalent Playwright TS
  - `playwright-cli --raw generate-locator e5` yields the assertion locator
  - specs go in `specs/<feature>.plan.md`

  Sources: `playwright-core@1.64.0/lib/tools/skills/playwright-cli/references/test-generation.md` and `references/playwright-tests.md`.

---

## 5. `playwright-cli` (`@playwright/cli`): the agent-oriented CLI

- **It exists.** Announced in @playwright/mcp 0.0.58/0.0.59 (2026-01-24/25) and in Playwright 1.58 ("Playwright CLI+SKILLs"). The repo is https://github.com/microsoft/playwright-cli, the npm package is `@playwright/cli` (bin `playwright-cli`, latest 0.1.22), and it has been bundled as `npx playwright cli` since 1.62.
  Sources: https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.59; https://github.com/microsoft/playwright/releases/tag/v1.58.0; https://registry.npmjs.org/@playwright/cli; release v1.62.0.
- **Install:**
  - global: `npm install -g @playwright/cli@latest`
  - local: `npm install -D @playwright/cli@latest`, then `npx playwright cli --help`

  Node 20+ per the docs page; the README says 18+. Sources: https://playwright.dev/docs/getting-started-cli; https://github.com/microsoft/playwright-cli/blob/main/README.md.
- **Skills into Claude Code:**
  - project scope: `playwright-cli install --skills`, which writes `.claude/skills/playwright-cli/`
  - user scope: `playwright-cli install --skills -g`, which writes `~/.claude/skills/playwright-cli/`
  - `--skills=agents` writes `.agents/skills` instead
  - **all three bundled skills** (`playwright-cli`, `playwright-component-testing`, `playwright-trace`): `npx playwright init-skills --loop=claude|agents` (1.62+)
  - trace skill only: `npx playwright trace install-skill`

  Sources: help.json `install`; https://playwright.dev/docs/getting-started-cli; `coreBundle.js` `installSkills`, which copies `lib/tools/skills/<skill>` to `<cwd or ~>/.<target>/skills/<skill>`; `playwright@1.64.0/lib/program.js` `addInitSkillsCommand`.
- Older install methods (Jan 2026, may be stale): `/plugin marketplace add microsoft/playwright-cli` then `/plugin install playwright-cli`, or `curl` the SKILL.md into `.claude/skills/playwright-cli/`. Source: release v0.0.59. Whether the plugin marketplace route still works today: **UNVERIFIED**.
- Skill frontmatter: `allowed-tools: Bash(playwright-cli:*) Bash(npx playwright:*) Bash(npx --no-install playwright:*)`. Source: `lib/tools/skills/playwright-cli/SKILL.md`.
- **Full command list**, verbatim from `playwright-core@1.64.0/lib/tools/cli-client/help.json`:
  - **Core:** `open [url]`, `attach [name]`, `close`, `detach`, `goto <url>`, `type <text>`, `click <target> [button]`, `dblclick`, `fill <target> <text>` (`--submit`), `drag`, `drop`, `hover`, `select`, `upload <files...>`, `check`, `uncheck`, `snapshot [target]` (`--filename`, `--depth`, `--boxes`), `find [text]` (`--regex`), `eval <func> [target]`, `dialog-accept [prompt]`, `dialog-dismiss`, `resize <w> <h>`, `delete-data`
  - **Navigation:** `go-back`, `go-forward`, `reload`
  - **Keyboard:** `press`, `keydown`, `keyup`
  - **Mouse:** `mousemove`, `mousedown`, `mouseup`, `mousewheel`
  - **Save as:** `screenshot [target]` (`--filename`, `--type png|jpeg|webp`, `--full-page`, `--hires`), `pdf`
  - **Tabs:** `tab-list`, `tab-new [url]`, `tab-close [index]`, `tab-select <index>`
  - **Storage:** `state-load <filename>`, `state-save [filename]`, `cookie-list|get|set|delete|clear`, `localstorage-list|get|set|delete|clear`, `sessionstorage-list|get|set|delete|clear`
  - **Emulation:** `set-color-scheme`, `set-reduced-motion`, `set-forced-colors`, `set-contrast`, `set-media`, and the matching `clear-*`
  - **Network:** `requests`, `request <index>`, `request-headers`, `request-body`, `response-headers`, `response-body`, `route <pattern>`, `route-list`, `unroute [pattern]`, `network-state-set <state>`
  - **DevTools:** `console [min-level]`, `run-code [code]`, `recording-start`, `recording-stop`, `tracing-start`, `tracing-stop`, `video-start [filename]` (`--size 800x600`, `--fps`, `--cursor`), `video-stop`, `video-chapter <title>`, `video-show-actions`, `video-hide-actions`, `show` (`--annotate`), `pause-at <location>`, `resume`, `step-over`, `generate-locator <target>`, `highlight [target]`
  - **WebMCP:** `webmcp-list`, `webmcp-call <name>`
  - **Install:** `install` (`--skills`, `--global`), `install-browser [browser]`
  - **Sessions:** `list`, `close-all`, `kill-all`
  - **Global:** `-s=<session>`, `--json`, `--raw`, `--help`, `--version`; env `PLAYWRIGHT_CLI_SESSION`
- Targets can be snapshot refs (`e15`), CSS, or Playwright locators like `"getByTestId('submit-button')"`. Source: CLI README "Targeting elements".
- Snapshots are written to `.playwright-cli/page-*.yml` and **not inlined**, which is the main token saving. Traces go to `.playwright-cli/traces/`. The profile is **in-memory by default**; pass `--persistent` or `--profile=<path>`. A headless session auto-closes after 1 h. Sources: CLI README; `references/tracing.md`; https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.64.
- Doc defect: the CLI README's config schema and env table still list `saveVideo`, `outputMode` and `PLAYWRIGHT_MCP_SAVE_TRACE/SAVE_VIDEO`, which are stale next to MCP 0.0.83. Source: https://github.com/microsoft/playwright-cli/blob/main/README.md.
- **Microsoft's CLI vs MCP guidance** (verbatim gist):
  - "Modern coding agents increasingly favor CLI-based workflows exposed as SKILLs over MCP because CLI invocations are more token-efficient: they avoid loading large tool schemas and verbose accessibility trees into the model context …"
  - "MCP remains relevant for specialized agentic loops that benefit from persistent state, rich introspection, and iterative reasoning over page structure, such as exploratory automation, self-healing tests, or long-running autonomous workflows …"

  Sources: https://github.com/microsoft/playwright-mcp/blob/main/README.md; https://github.com/microsoft/playwright-cli/blob/main/README.md; https://playwright.dev/docs/getting-started-cli.
- Third-party benchmarks report roughly 4x fewer tokens with the CLI (about 27K vs about 114K per task). This is secondary and **UNVERIFIED**; Checkly argues the gap has narrowed. Sources: https://morphllm.com/playwright-mcp, https://www.checklyhq.com/blog/mcp-vs-cli-token-efficiency/, https://bug0.com/blog/playwright-cli-vs-playwright-mcp-ai-browser-testing-2026.

---

## 6. Agent-oriented Playwright features, 1.55 → 1.64

| Version | Feature | Source |
|---|---|---|
| 1.55 (2025-08-20) | Codegen can emit automatic `toBeVisible()` assertions | https://github.com/microsoft/playwright/releases/tag/v1.55.0 |
| 1.56 (2025-10-06) | Test Agents + `init-agents`; `page.consoleMessages()`, `page.pageErrors()`, `page.requests()`; HTML reporter option to disable the **"Copy prompt"** button (`noCopyPrompt` in `HtmlReporterOptions`) | release v1.56.0; `playwright@1.64.0/types/test.d.ts` |
| 1.57 | `locator.description()` returns the text set by `locator.describe()`, and `Locator.toString()` uses it | release v1.57.0 |
| 1.58 (2026-01-23) | Playwright CLI+SKILLs announced; `init-agents` gains `copilot` / `vscode-legacy` and prompt files | release v1.58.0; `program.js` |
| 1.59 (2026-04-01) | **`npx playwright test --debug=cli`** ("CLI debugger for agents", then `playwright-cli attach tw-…`, `step-over`); **`npx playwright trace open\|actions\|action\|requests\|console\|errors\|snapshot\|screenshot\|attachments\|close`** (trace analysis for agents); `page.screencast` (agentic video receipts: `start`, `showActions`, `showChapter`, `showOverlay`); `browser.bind()` so the CLI and MCP can attach to a test's browser (`@playwright/mcp --endpoint=<name>`); `page.ariaSnapshot()` with `depth` and `mode`; `locator.normalize()`; `page.pickLocator()`; `browserContext.setStorageState()`; `playwright-cli show` dashboard (`PLAYWRIGHT_DASHBOARD=1` for test browsers) | release v1.59.0 |
| 1.60 | `ariaSnapshot({ boxes })` "useful for AI consumption"; `expect(page).toMatchAriaSnapshot()`; `testInfoError.errorContext` (the aria snapshot at the time of an `expect` failure); `locator.drop()`; `getByRole({ description })` | release v1.60.0 |
| 1.61 | `browserContext.credentials` (passkeys); `page.localStorage` / `page.sessionStorage`; video modes matching trace modes | release v1.61.0 |
| 1.62 | MCP and CLI bundled (`npx playwright mcp`, `npx playwright cli`); `init-skills`; WebP screenshots; `AbortSignal` support | release v1.62.0; `program.js` |
| 1.63 | Aria and screen snapshots in traces (`trace: { snapshots: { dom, aria, screen } }`, plus a "Display Aria" view); `locator.ariaSnapshotJSON()` / `page.ariaSnapshotJSON()`; `locator.visible()`; `--add-reporter`; `perfetto` reporter; test `lock` | release v1.63.0 |
| 1.64 (2026-10-07) | `page.webmcp` / `frame.webmcp`; **`page.getByRef('e2')`**, which resolves refs from `ariaSnapshot({ mode: 'ai' })`; `locator.within()`; video `fps` and CSS `style`; `--shuffle`; `testProject.default` | release v1.64.0 |

Related details:
- `page.ariaSnapshot({ mode: 'ai' })` returns a snapshot "optimized for AI consumption: including element references like `[ref=e2]` and snapshots of `<iframe>`s"; `mode` is `"ai"|"default"`. `page.getByRef(ref).normalize()` followed by `.toString()` turns a ref into resilient locator code "the same way codegen does", "prioritizing test ids, aria roles, and other user-facing attributes over CSS selectors".
  Source: `playwright-core@1.64.0/types/types.d.ts`; https://playwright.dev/docs/api/class-page#page-aria-snapshot; https://playwright.dev/docs/api/class-locator#locator-normalize.
- The "Copy prompt" / fix-with-AI context comes from `buildErrorContext`. It assembles "# Instructions — Following Playwright test failed. Explain why… Provide a snippet of code with the fix", then the test info, the error details and the page snapshot. Source: `playwright@1.64.0/lib/errorContext.js`. The version in which "Copy prompt" first shipped (before 1.55) is **UNVERIFIED**.
- `--run-agents <missing|all|none>` ("Run agents to generate the code for page.perform") shows up in `npx playwright test` options from 1.59. But `page.perform` is **not** in the 1.64 public `types.d.ts`, so treat it as hidden or experimental (**UNVERIFIED**, undocumented). Source: `program.js` testOptions.
- MCP inside a paused test happens in two ways:
  - the `run-test-mcp-server` relays `browser_*` calls into a test paused by `test_debug`, `planner_setup_page` or `generator_setup_page` (§4d)
  - with `--caps=devtools`, `browser_resume` {`step`, `location: "file.spec.ts:42"`} steps a paused script in `@playwright/mcp`

  Sources: README DevTools section; `testBackend.js`.

---

## 7. Recommended ways for a Claude Code subagent (current names)

### 7a. Explore a live page to build a Page Object

1. Navigate with `browser_navigate` {url}.
2. Take an inventory with `browser_snapshot`. Use {`depth`} or {`target`: ref/selector} to scope it, and {`filename`} to keep it out of context. For one element, `browser_find` {text|regex} is cheaper than a full snapshot.
   Source: README (`browser_snapshot` params; `browser_find` "cheaper than capturing the whole snapshot").
3. Harvest test ids explicitly with `browser_evaluate`. The snapshot does **not** expose `id`, `class` or `data-*`, and the CLI skill's own reference says to use `eval "el => el.getAttribute('data-testid')" e7`.
   Source: `lib/tools/skills/playwright-cli/references/element-attributes.md`.
4. Get the canonical locator per ref with `browser_generate_locator` {target: "e12"} (**`--caps=testing`**). It returns the resolved locator string (`tab.targetLocator(params)` → `resolved`).
   - Start the server with `--test-id-attribute=<attr>` if the app does not use `data-testid`.
   - That it uses the same best-practice generator as `locator.normalize()` (test id → role → …) is consistent with the code path but **UNVERIFIED** in the docs.

   Source: README; `coreBundle.js`.
5. Optionally assert while exploring with `browser_verify_element_visible` {role, accessibleName}, `browser_verify_text_visible`, `browser_verify_value` (**`--caps=testing`**).
6. Generated code: every action's response carries Playwright code in the `--codegen` language. Use `typescript`, `java` or `csharp` to match the qa-ui-* stack. Source: README `--codegen`; release v0.0.79.

### 7b. Generate a stable locator for one element

- MCP: `browser_snapshot` or `browser_find` to get the ref, then `browser_generate_locator` {target}.
- CLI: `playwright-cli --raw generate-locator e5` prints e.g. `getByRole('button', { name: 'Submit' })`.
- Test code: `await page.getByRef('e5').normalize()` (PW 1.64, after `ariaSnapshot({ mode: 'ai' })`).

Sources: README; `references/test-generation.md`; types.d.ts.

### 7c. Capture evidence of an exploratory session

- **Screenshot.** `browser_take_screenshot` {`filename`: "evidence/login-error.png", `fullPage`: true, `type`: "png", `scale`: "css"}.
  - With `filename` set, the base64 image is skipped (0.0.74) and the path resolves against the workspace root.
  - The tool description says not to act on screenshots; use the snapshot for that.

  Sources: README; release v0.0.74.
- **Video** (**`--caps=devtools`**):
  1. `browser_start_video` {`filename`: "evidence/flow.webm", `size`: {width:1280, height:720}, `fps`: 25, `cursor`: false}
  2. optionally `browser_video_chapter` {title} and `browser_video_show_actions`
  3. run the actions
  4. `browser_stop_video`

  Output is WebM; VP9 since 1.64. Sources: README; release v0.0.82; release v1.64.0.
- **Trace** (**`--caps=devtools`**):
  1. `browser_start_tracing`
  2. run the actions
  3. `browser_stop_tracing`, which returns links to the trace files
  4. inspect with `npx playwright show-trace` or the agent-friendly `npx playwright trace open <zip>` / `trace actions` / `trace action <id>`

  Sources: README; release v1.59.0 ("CLI trace analysis for agents").
- The session-wide `--save-trace` / `--save-video` flags **no longer exist** (removed 0.0.69). `--save-session` (session log) remains. Source: §2b.
- CLI equivalents: `tracing-start` / `tracing-stop`, `video-start f.webm --size=1280x720 --fps=60 --cursor` / `video-stop`, `screenshot --filename=f.png --full-page`. Source: help.json.

### 7d. Save and restore auth storage state

- Save after logging in once: `browser_storage_state` {filename: "playwright/.auth/user.json"} (**`--caps=storage`**). It holds cookies and localStorage.
- Restore inside a session: `browser_set_storage_state` {filename} (**`--caps=storage`**). It clears existing cookies and localStorage first, then navigates.
- Restore at server start: `--isolated --storage-state=playwright/.auth/user.json`. With the default persistent profile, login also survives between sessions on its own (per-workspace profile dir).

Sources: README "User profile", "Initial state", Storage tools.

- CLI equivalents: `state-save auth.json` / `state-load auth.json`. Source: help.json; `references/storage-state.md`.
- sessionStorage is **not** in the storage-state file per the tool description ("cookies, local storage"). Use `browser_sessionstorage_*` (`--caps=storage`) if the app keeps its token there. Source: README.
- Test-runner side: `browserContext.storageState()`, `setStorageState()` (1.59), and the new `credentials` (1.62) and `opfs` (1.63) storage-state options. Sources: releases v1.59.0, v1.62.0, v1.63.0.

---

## 8. Proposal: frontmatter `tools` for a UI QA agent (qa-ui-typescript / qa-ui-java / qa-ui-dotnet)

### 8a. Server registration this frontmatter assumes

Use user or project scope; the server must be named `playwright`:

```bash
claude mcp add playwright -- npx @playwright/mcp@latest --caps=testing,storage,devtools --isolated --output-dir=.playwright-mcp
# add --test-id-attribute=<attr> only if the app does not use data-testid
# add --codegen=java | --codegen=csharp for the Java / .NET agents (default is typescript)
```

- The `--` placement follows Claude Code's documented syntax: `claude mcp add [options] <name> -- <command> [args...]`, where "Everything after `--` is passed to the server untouched." Source: https://code.claude.com/docs/en/mcp.
- The repo's `page-objects-from-url` skills currently say `claude mcp add playwright npx @playwright/mcp@latest -- --caps=testing,storage`. That puts `--` after the package, so the documented form above is preferred. Whether the repo's form also works is **UNVERIFIED**.
- If the server is shipped inside a plugin's `.mcp.json`, tool names become `mcp__plugin_<plugin-name>_<server-name>__<tool>` and the frontmatter must use that form. Source: https://code.claude.com/docs/en/mcp.
- **Plugin subagents ignore the `mcpServers` frontmatter field**, so a plugin agent cannot declare its own `--caps` inline. The caps have to be on the user, project or plugin-level server. Source: https://code.claude.com/docs/en/sub-agents.

### 8b. Explicit allowlist (recommended: excludes RCE and vision tools)

```yaml
tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch,
  # core (always available)
  mcp__playwright__browser_navigate, mcp__playwright__browser_navigate_back,
  mcp__playwright__browser_snapshot, mcp__playwright__browser_find,
  mcp__playwright__browser_click, mcp__playwright__browser_type, mcp__playwright__browser_fill_form,
  mcp__playwright__browser_select_option, mcp__playwright__browser_press_key, mcp__playwright__browser_hover,
  mcp__playwright__browser_file_upload, mcp__playwright__browser_handle_dialog,
  mcp__playwright__browser_wait_for, mcp__playwright__browser_evaluate,
  mcp__playwright__browser_take_screenshot, mcp__playwright__browser_resize, mcp__playwright__browser_emulate_media,
  mcp__playwright__browser_console_messages, mcp__playwright__browser_network_requests, mcp__playwright__browser_network_request,
  mcp__playwright__browser_tabs, mcp__playwright__browser_close,
  # --caps=testing
  mcp__playwright__browser_generate_locator, mcp__playwright__browser_verify_element_visible,
  mcp__playwright__browser_verify_text_visible, mcp__playwright__browser_verify_value, mcp__playwright__browser_verify_list_visible,
  # --caps=storage
  mcp__playwright__browser_storage_state, mcp__playwright__browser_set_storage_state,
  # --caps=devtools (evidence capture)
  mcp__playwright__browser_start_tracing, mcp__playwright__browser_stop_tracing,
  mcp__playwright__browser_start_video, mcp__playwright__browser_stop_video
```

(Comments are shown for the reader only. The real frontmatter is one comma-separated line or a YAML list; the docs allow either.) Source: https://code.claude.com/docs/en/sub-agents ("comma-separated string … or a YAML list").

- **Deliberately left out:**
  - `browser_run_code_unsafe` (README: "RCE-equivalent")
  - `--caps=vision` mouse-xy tools (only needed for canvas)
  - `browser_pdf_save`
  - cookie, localStorage and sessionStorage granular tools (add `browser_sessionstorage_*` if auth lives in sessionStorage)
  - `browser_route*` (`--caps=network`, worth adding only for error-state exploration)
  - `browser_start_recording` / `browser_stop_recording` (needs a human to demonstrate)
- Backward compatibility: every name the agents grant today is in this list, so no grant has to be removed. The change is to **turn on caps** and **add** `browser_find`, `browser_navigate_back`, `browser_press_key`, `browser_hover`, `browser_file_upload`, the network/console readers, `browser_verify_*`, tracing and video.
- **Simpler alternative:** `tools: …, mcp__playwright`. Claude Code accepts server-level `mcp__<server>` or `mcp__<server>__*` in `tools`. It grants every enabled tool, including `browser_run_code_unsafe`; that is the trade-off. Source: https://code.claude.com/docs/en/sub-agents.
- **Healer-style agents:** to repair existing specs, grant the test MCP server instead (`mcp__playwright-test__test_run`, `mcp__playwright-test__test_debug`, `mcp__playwright-test__test_list`, `mcp__playwright-test__browser_snapshot`, `mcp__playwright-test__browser_generate_locator`, …). Register it with `npx playwright run-test-mcp-server`. It exposes all `browser_*` tools without `--caps`, but only works inside a TS Playwright Test project (§4d).
- **CLI alternative** (Microsoft's recommendation for coding agents):
  - grant `Bash(playwright-cli:*)` and `Bash(npx playwright:*)`
  - install the skill: `playwright-cli install --skills` or `npx playwright init-skills`
  - command map: `snapshot`, `eval … e7` for data-testid, `generate-locator`, `state-save` / `state-load`, `tracing-start/stop`, `video-start/stop`, `screenshot`

  Source: §5.
- Mobile agents: Playwright MCP covers **mobile-web emulation only**, through `--device="iPhone 15"` or `--mobile`. Native app automation stays with Appium; no Playwright MCP tool covers native apps. Source: README flags.

---

## 9. Evidence index (primary sources fetched 2026-10-10)

- Playwright MCP README (main): https://github.com/microsoft/playwright-mcp/blob/main/README.md (raw: https://raw.githubusercontent.com/microsoft/playwright-mcp/main/README.md), identical in tool/flag content to the npm `@playwright/mcp@0.0.83/README.md`
- Playwright MCP releases v0.0.33 → v0.0.83: https://github.com/microsoft/playwright-mcp/releases
- npm metadata: https://registry.npmjs.org/@playwright/mcp, https://registry.npmjs.org/@playwright/cli, https://registry.npmjs.org/playwright-core
- `@playwright/mcp@0.0.83` tarball: `cli.js`, `config.d.ts` (ToolCapability), `package.json`
- Historical READMEs from npm tarballs `@playwright/mcp@0.0.34/36/40/47/52/55/58/62/64/67/68/69/72/74/76/78/79/80/81/82` (presence or absence of each tool and flag)
- `playwright-core@1.64.0` tarball: `lib/coreBundle.js` (tool defs, capabilities, `filteredTools`, `skillOnly`, WebMCP, option parser, `installSkills`), `lib/tools/cli-client/help.json`, `lib/tools/skills/playwright-cli/SKILL.md` + `references/*.md`, `types/types.d.ts`
- `playwright@1.64.0` tarball: `lib/program.js`, `lib/agents/*.agent.md`, `lib/agents/generateAgents.js`, `lib/mcp/test/*.js`, `lib/errorContext.js`, `types/test.d.ts`; plus `playwright@1.56.1…1.63.0` `program.js` and agents for history
- Playwright releases v1.55.0 → v1.64.0: https://github.com/microsoft/playwright/releases
- playwright.dev: https://playwright.dev/docs/test-agents, https://playwright.dev/docs/getting-started-cli, https://playwright.dev/docs/getting-started-mcp
- playwright-cli README: https://github.com/microsoft/playwright-cli/blob/main/README.md
- Claude Code docs: https://code.claude.com/docs/en/mcp, https://code.claude.com/docs/en/sub-agents
- Chrome WebMCP: https://developer.chrome.com/docs/ai/webmcp
- Local config check: `~/.claude.json` → `mcpServers.playwright = {"command":"npx","args":["-y","@playwright/mcp@latest"]}` (no `--caps`)
