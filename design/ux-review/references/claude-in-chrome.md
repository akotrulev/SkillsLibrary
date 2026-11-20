# Driving Claude in Chrome

Read this before the first `mcp__claude-in-chrome__*` call. Claude in Chrome drives the user's real browser, with their session and data, so the read-only contract of an audit extends to all three.

1. Call `tabs_context_mcp`, then work only in a new tab (`tabs_create_mcp`), so the user's own tabs stay untouched. Carry no tab id from an earlier run.
2. Aim at a local or staging build. When production is the only target, say so once and treat it as a constraint.
3. Walk each state-changing flow (delete, send, pay, invite, publish) to its final control, capture it, and stop there.
4. Read the handler in source for any native `alert`, `confirm` or `prompt`; triggering one ends the session. A native `confirm()` guarding a reversible action is itself a finding.
5. Narrow the window with `resize_window` for the narrowest-width capture, and restore its size afterwards.
6. When a navigation is refused, the site is not permitted: say so, ask once, mark its screens Unverifiable and take nothing about them from source.
7. After two or three failed interactions on one screen, stop and report the screen as Unverifiable.

Done when every capture came from a tab you created, no state-changing control was activated, and the window is back at its original size.
