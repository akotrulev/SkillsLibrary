# The prototype file: contract and skeleton

`docs/prototypes/<slug>/index.html` is one file that opens from disk, with nothing to install or serve. This is its contract, then a skeleton of the wiring to start from.

## File contract

- **Self-contained.** CSS in one `<style>`, JS in one `<script>`, data inline. The only network request is Google Fonts, and only when the language's type is a web font; native targets use the system font stack and load none.
- **Three record lines at the top**, as `<meta>` tags in `<head>`: `prototype-plan` (the plan line from step 1), `prototype-language` (the sources of the design-language block, on one line), `prototype-verdict` (empty until step 6).
- **Tokens are custom properties on `:root`**, named after the project's own tokens when it has them, so a reader can trace each value. A second theme overrides them under `:root[data-theme="dark"]`. A language with one theme has one block, and the theme control is left out.
- **One `<section data-variant="A">` per variant**, keys `A` to `E`, each with an `aria-label` naming its idea ("A, table by day"). Variants reuse the tokens and may share small markup; each owns its layout.
- **Every data region in every state**: `loaded`, `loading`, `empty`, `failed`, as sibling children marked `data-state`. Loading reserves the loaded layout's space (a skeleton, not a spinner over blank). Empty says what is missing and offers the next action. Failed swaps only the response-dependent subtree: the toolbar, search and headers keep rendering. A failure also raises the persistent notification the target's rules require: top-right on the web, a banner inside the safe area on mobile, an inline banner or `InfoBar` in a desktop window. It closes only on its close button.
- **Realistic data**, from the sources in SKILL.md's Rules, with real lengths: the longest name, a two-line title, a zero, a large count.
- **A switcher bar**, fixed at the bottom centre, styled apart from the design (a dark, high-contrast pill) so it never reads as part of a variant. It holds the variant, state, theme and viewport controls, each a labelled `<select>`.
- **Viewports resize a frame, not the window.** `desktop`, `tablet` and `phone` set the width of `.frame`; a mobile target swaps them for phone and tablet device frames with a safe area, a desktop target for a window frame. Responsive rules inside variants use `@container` queries on `.frame`, because a `@media` query sees the browser window and never fires when only the frame narrows.
- **Keyboard**: `1`–`5` pick a variant, `s` cycles the states. Keys typed into a field or a `<select>` are left alone.
- **The URL round-trips.** `?variant=B&state=failed&theme=dark&viewport=phone` opens on that view, and every change rewrites the query with `history.replaceState`, so a copied URL reproduces what the person saw. An unknown value falls back to the first option.
- **Semantic HTML and contrast.** Landmarks, headings in order, real buttons and links, labelled controls, `prefers-reduced-motion` honoured. Every text and background token pair meets the corpus contrast rule (`search.py "color contrast text" --domain ux`): 4.5:1 for body text, 3:1 for large text and controls, in each theme. A pair the project's own tokens fail is reported, not changed.

## Done when

- [ ] the file opens from disk with no console error, and makes no request beyond Google Fonts
- [ ] the three record lines are present
- [ ] every variant renders in every state, theme and viewport, with the failure notification in the failed state
- [ ] no two variants share a layout and a primary affordance
- [ ] `1`–`5`, `s` and each control work, and a reload keeps the view
- [ ] the contrast pairs are checked in each theme, and any failure is reported

## Skeleton

The wiring for two variants and one region; repeat the region pattern for every data region, and each variant's layout is yours to write. The script reads the variant keys from the sections, so adding a section and its `<option>` is all a new variant needs.

```html
<!doctype html>
<html lang="en" data-theme="light" data-viewport="desktop">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="prototype-plan" content="Three variants of the booking list, states loaded / loading / empty / failed, desktop and phone.">
<meta name="prototype-language" content="app/globals.css:4-58 (palette, radius); tailwind.config.ts (type, spacing); lucide-react (icons)">
<meta name="prototype-verdict" content="">
<title>Prototype: booking list</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root { --background: #fafaf9; --foreground: #1c1917; --muted-foreground: #57534e; --border: #e7e5e4;
  --accent: #2563eb; --on-accent: #fff; --destructive: #b91c1c; --radius: 0.5rem; --space: 4px;
  --font: "Inter", system-ui, sans-serif; }
:root[data-theme="dark"] { --background: #1c1917; --foreground: #fafaf9; --muted-foreground: #a8a29e;
  --border: #44403c; --accent: #60a5fa; --on-accent: #0c0a09; --destructive: #f87171; }
body { margin: 0; background: #d6d3d1; font-family: var(--font); }
.frame { position: relative; container-type: inline-size; margin: 0 auto; min-height: 100vh;
  background: var(--background); color: var(--foreground); }
[data-viewport="desktop"] .frame { max-width: 1440px; }
[data-viewport="tablet"] .frame { max-width: 834px; }
[data-viewport="phone"] .frame { max-width: 390px; }
[hidden] { display: none !important; }
.notice { position: absolute; top: calc(var(--space) * 4); right: calc(var(--space) * 4);
  border: 1px solid var(--destructive); border-radius: var(--radius); background: var(--background);
  padding: calc(var(--space) * 3); }
.skeleton-row { height: 44px; border-radius: var(--radius); background: var(--border); margin-block: 8px; }
.switcher { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%); display: flex; gap: 12px;
  padding: 8px 16px; border-radius: 999px; background: #111; color: #fff; font: 13px system-ui, sans-serif;
  box-shadow: 0 4px 16px rgb(0 0 0 / 0.3); }
@container (max-width: 600px) { .variant-a table { font-size: 14px; } }
@media (prefers-reduced-motion: no-preference) { .skeleton-row { animation: pulse 1.2s ease-in-out infinite; } }
@keyframes pulse { 50% { opacity: 0.5; } }
</style>
</head>
<body>
<div class="frame">
  <section data-variant="A" class="variant-a" aria-label="A, table by day">
    <header><h1>Bookings</h1><input type="search" aria-label="Search bookings"></header>
    <div data-state="loaded"><table><caption>Today, 20 November</caption><tbody>
      <tr><td>07:30</td><td>Vinyasa Flow, Studio 2</td><td>Maria Petrova</td><td><button>Reschedule</button></td></tr>
    </tbody></table></div>
    <div data-state="loading" aria-busy="true"><div class="skeleton-row"></div><div class="skeleton-row"></div></div>
    <div data-state="empty"><p>No bookings today.</p><a href="#schedule">Open the class schedule</a></div>
    <div data-state="failed"><p>Bookings could not be loaded.</p><button>Try again</button></div>
  </section>
  <section data-variant="B" aria-label="B, week calendar with a detail sheet">
    <header><h1>Bookings</h1></header>
    <div data-state="loaded"><p>Week grid; a booking opens the detail sheet.</p></div>
    <div data-state="loading" aria-busy="true"><div class="skeleton-row"></div></div>
    <div data-state="empty"><p>No bookings this week.</p></div>
    <div data-state="failed"><p>Bookings could not be loaded.</p><button>Try again</button></div>
  </section>
  <div class="notice" role="alert" data-state="failed">
    <p>We could not load your bookings. Your existing bookings are unchanged.</p>
    <button data-dismiss aria-label="Close notification">Close</button>
  </div>
</div>
<nav class="switcher" aria-label="Prototype controls">
  <label>Variant <select data-control="variant"><option>A</option><option>B</option></select></label>
  <label>State <select data-control="state"><option>loaded</option><option>loading</option>
    <option>empty</option><option>failed</option></select></label>
  <label>Theme <select data-control="theme"><option>light</option><option>dark</option></select></label>
  <label>Viewport <select data-control="viewport"><option>desktop</option><option>tablet</option>
    <option>phone</option></select></label>
</nav>
<script>
const variants = [...document.querySelectorAll("[data-variant]")].map((section) => section.dataset.variant);
const states = ["loaded", "loading", "empty", "failed"];
const themes = ["light", "dark"];
const viewports = ["desktop", "tablet", "phone"];
const params = new URLSearchParams(location.search);
const pick = (value, allowed) => (allowed.includes(value) ? value : allowed[0]);
const view = {
  variant: pick(params.get("variant"), variants),
  state: pick(params.get("state"), states),
  theme: pick(params.get("theme"), themes),
  viewport: pick(params.get("viewport"), viewports),
};

function render() {
  document.querySelectorAll("[data-variant]").forEach((el) => { el.hidden = el.dataset.variant !== view.variant; });
  document.querySelectorAll("[data-state]").forEach((el) => { el.hidden = el.dataset.state !== view.state; });
  document.documentElement.dataset.theme = view.theme;
  document.documentElement.dataset.viewport = view.viewport;
  document.querySelectorAll("[data-control]").forEach((control) => { control.value = view[control.dataset.control]; });
  history.replaceState(null, "", `?${new URLSearchParams(view)}`);
}

function cycleState() {
  view.state = states[(states.indexOf(view.state) + 1) % states.length];
  render();
}

document.querySelectorAll("[data-control]").forEach((control) => {
  control.addEventListener("change", () => { view[control.dataset.control] = control.value; render(); });
});
document.querySelectorAll("[data-dismiss]").forEach((button) => {
  button.addEventListener("click", () => { button.closest("[role=alert]").hidden = true; });
});
document.addEventListener("keydown", (event) => {
  const typing = event.target.closest("input, textarea, select, [contenteditable]");
  const chosen = variants[Number(event.key) - 1];
  if (typing || event.metaKey || event.ctrlKey || event.altKey) return;
  if (chosen) { view.variant = chosen; render(); }
  if (event.key === "s") cycleState();
});
render();
</script>
</body>
</html>
```

## Screenshots, on request

One image per variant × state, per theme and viewport the user asked for, with the Playwright CLI (`--color-scheme` is not needed; the theme travels in the URL):

```bash
npx playwright screenshot --full-page --viewport-size=1440,900 \
  "file://$PWD/docs/prototypes/<slug>/index.html?variant=B&state=failed&theme=dark&viewport=desktop" \
  "docs/prototypes/<slug>/screenshots/B-failed-dark-desktop.png"
```

Use `--viewport-size=390,844` for `phone` and `834,1112` for `tablet`. With the Playwright MCP tools in the session, navigate to the same URLs and take the screenshots there instead.
