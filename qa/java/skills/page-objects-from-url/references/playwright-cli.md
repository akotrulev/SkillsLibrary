# The `playwright-cli` route — page-objects-from-url (Java)

Use it when MCP is not connected, or when a long extraction — a big page, many states — would flood the
context: the CLI writes snapshots to `.playwright-cli/page-*.yml` and you `Read` only what you need. Run it
through `Bash`; install with `npm i -g @playwright/cli@latest` (it needs Node, not the Java project). Same
procedure, same rules; only the calls change:

| Step | MCP tool | `playwright-cli` |
|---|---|---|
| Open, navigate, back | `browser_navigate`, `browser_navigate_back` | `open <url>`, `goto <url>`, `go-back` |
| Snapshot | `browser_snapshot` | `snapshot [target] --filename=<f> --depth=<n>` |
| Find one element | `browser_find` | `find <text>` (`--regex`) |
| Test-id harvest | `browser_evaluate` | `eval "<function>"`; one element: `eval "el => el.getAttribute('data-testid')" e7` |
| Canonical locator | `browser_generate_locator` | `--raw generate-locator e5` (JavaScript syntax — translate it) |
| Click, fill, hover, key | `browser_click`, `browser_fill_form`, `browser_hover`, `browser_press_key` | `click e3`, `fill e4 "<text>"`, `hover e3`, `press Escape` |
| Tabs, dialogs | `browser_tabs`, `browser_handle_dialog` | `tab-list`, `tab-new [url]`, `tab-select <i>`; `dialog-accept`, `dialog-dismiss` |
| Save / load auth | `browser_storage_state`, `browser_set_storage_state` | `state-save <f>`, `state-load <f>` |
| Screenshot, trace, video | `browser_take_screenshot`, `browser_start_tracing`…, `browser_start_video`… | `screenshot --filename=<f> --full-page`, `tracing-start`/`tracing-stop`, `video-start <f>`/`video-stop` |

The CLI has no tool allowlist, so hold its rules by hand: never `run-code` or `webmcp-call`, and `close`
the session at the end (a headless one closes itself after an hour). On an attribute other than
`data-testid`, check `generate-locator`'s first output against the harvest before trusting it.
