# Driving and probes — how the checks are run

The tool calls and snippets behind `checks.md`. A probe returns **candidates**: read the result, look at the screenshot, and raise a finding only for what is really wrong.

## 1. Driving a web app

**Primary: the Playwright MCP server**, registered by the user (an agent cannot set server flags on itself):

```bash
claude mcp add --scope user playwright -- npx @playwright/mcp@latest --caps=testing,storage,devtools --isolated --output-dir=.playwright-mcp
```

**Fallback: `playwright-cli`** through `Bash` (`npm i -g @playwright/cli@latest`, or `npx playwright cli`), when the server is not connected or a long run would flood the context: it writes snapshots to `.playwright-cli/page-*.yml` and you read only what you need. Neither available: stop and give the user the command above.

| Step | MCP tool (`mcp__playwright__…`) | `playwright-cli` |
|---|---|---|
| Open, go, back, reload | `browser_navigate`, `browser_navigate_back` | `open <url>`, `goto <url>`, `go-back`, `go-forward`, `reload` |
| Read the screen as structure | `browser_snapshot` | `snapshot --filename=<f>` |
| Press, type, choose, key | `browser_click`, `browser_type`, `browser_fill_form`, `browser_select_option`, `browser_press_key` | `click e3`, `dblclick e3`, `fill e4 "<text>"`, `select e5 <value>`, `press Tab` |
| Run a probe | `browser_evaluate` `{ function: "() => { … }" }` | `eval "<function>"` |
| Console and network | `browser_console_messages`, `browser_network_requests`, `browser_network_request` | `console`, `requests`, `request <n>` |
| Viewport, dark mode | `browser_resize`, `browser_emulate_media` | `resize 375 812`, `set-color-scheme dark` |
| Wait on a condition | `browser_wait_for` `{ text }` / `{ textGone }` | `find "<text>"` on a fresh `snapshot`, repeated until it is there |
| Dialogs, tabs | `browser_handle_dialog`, `browser_tabs` | `dialog-dismiss`, `tab-list`, `tab-select <i>` |
| Screenshot | `browser_take_screenshot` `{ filename: "evidence/<date>-<slug>/F-07-cart-total.png", fullPage: true }` | `screenshot --filename=<f> --full-page` |
| Keep a login | `browser_storage_state`, `browser_set_storage_state` | `state-save <f>`, `state-load <f>` |
| End | `browser_close` | `close` |

- A snapshot ref (`e15`) is valid within one snapshot; take a new snapshot after any navigation or change.
- With `filename` set, a screenshot is written to disk and not returned. To *look* at a layout, take it without a filename, or `Read` the file.
- A dialog asking to confirm something irreversible is dismissed, never accepted.
- Never `run-code` and never a page's own `webmcp_*` tools: the user interface is what is being explored.

## 2. Web probes

Each is a function for `browser_evaluate` (or `eval`). Run them after the content has loaded, at every viewport.

**Links: harvest**

```js
() => [...document.querySelectorAll('a[href], area[href]')].map(a => ({
  href: a.href,
  raw: a.getAttribute('href'),
  text: (a.innerText || a.getAttribute('aria-label') || a.title || a.querySelector('img')?.alt || '').trim().slice(0, 80),
  newTab: a.target === '_blank',
  rel: a.rel,
  shown: a.getClientRects().length > 0,
}))
```

Remove duplicates, and remove every link the safe-action floor denies, before anything is requested. `raw` of `#`, an empty string or `javascript:` is a dead-control candidate; a link with no `text` has no accessible name.

**Links: anchors that point at nothing**

```js
() => [...document.querySelectorAll('a[href^="#"]')]
  .map(a => decodeURIComponent(a.getAttribute('href').slice(1)))
  .filter(id => id && !document.getElementById(id) && !document.getElementsByName(id).length)
```

**Links: status of same-origin addresses, inside the signed-in session**

```js
async () => {
  const urls = [/* same-origin addresses from the harvest, floor-denied ones removed */];
  const out = [];
  for (const u of urls) {
    try {
      const r = await fetch(u, { credentials: 'include', redirect: 'follow' });
      const html = await r.text();
      out.push({ u, status: r.status, final: r.url, title: html.match(/<title[^>]*>([^<]*)/i)?.[1]?.trim(), h1: html.match(/<h1[^>]*>([^<]*)/i)?.[1]?.trim() });
    } catch (e) { out.push({ u, error: String(e) }); }
  }
  return out;
}
```

A `200` whose `title` or `h1` says the page does not exist is a soft 404. A client-rendered app returns the same shell for every address: there, open the target with `browser_navigate` and read its heading instead.

**Links: status of external addresses**, from `Bash`, one request at a time, each unique address once, at most 300 per run:

```bash
curl -s -o /dev/null -I -L --max-redirs 5 --max-time 15 -A 'Mozilla/5.0 (link check)' -w '%{http_code} %{num_redirects} %{url_effective}\n' '<url>'
```

When `HEAD` is refused (`405`, `403`, `501`, `000`), ask for the first byte instead: the same command with `-r 0-0` in place of `-I`. A site that still answers `403`, `429` or `999` is blocking robots: record the link as **unverified**, never as broken.

**Layout: sideways overflow**

```js
() => {
  const w = document.documentElement.clientWidth;
  const d = e => `${e.tagName.toLowerCase()}${e.id ? '#' + e.id : ''}${e.dataset.testid ? `[data-testid=${e.dataset.testid}]` : ''} "${(e.innerText || '').trim().slice(0, 40)}"`;
  return {
    viewport: w,
    pageScrollsSideways: document.documentElement.scrollWidth > w,
    offenders: [...document.querySelectorAll('body *')].filter(e => {
      const r = e.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && (r.right > w + 1 || r.left < -1);
    }).slice(0, 20).map(d),
  };
}
```

`pageScrollsSideways` is the finding; `offenders` say where to look. A closed drawer or the next slide of a carousel sits off screen on purpose.

**Layout: a control covered by something else** (controls inside the viewport only: run it at the top, the middle and the bottom of a long page)

```js
() => {
  const d = e => `${e.tagName.toLowerCase()}${e.id ? '#' + e.id : ''}${e.dataset.testid ? `[data-testid=${e.dataset.testid}]` : ''} "${(e.innerText || e.value || '').trim().slice(0, 40)}"`;
  return [...document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, [role=button], [role=link], [role=tab], [role=checkbox], [role=switch]')].flatMap(e => {
    const r = e.getBoundingClientRect();
    const x = r.left + r.width / 2, y = r.top + r.height / 2;
    if (!r.width || !r.height || x < 0 || y < 0 || x >= innerWidth || y >= innerHeight) return [];
    const top = document.elementFromPoint(x, y);
    const own = !top || top === e || e.contains(top) || top.contains(e) || [...(e.labels || [])].some(l => l.contains(top));
    return own ? [] : [{ control: d(e), coveredBy: d(top) }];
  });
}
```

**Layout: text that is cut off**

```js
() => {
  const d = e => `${e.tagName.toLowerCase()}${e.id ? '#' + e.id : ''}${e.dataset.testid ? `[data-testid=${e.dataset.testid}]` : ''}`;
  const cut = v => v === 'hidden' || v === 'clip';
  return [...document.querySelectorAll('body *')].filter(e => {
    if (!e.clientWidth || !e.innerText?.trim() || e.querySelectorAll('*').length > 3) return false;
    const s = getComputedStyle(e);
    return (cut(s.overflowX) && e.scrollWidth > e.clientWidth + 1) || (cut(s.overflowY) && e.scrollHeight > e.clientHeight + 1);
  }).map(e => ({ el: d(e), text: e.innerText.trim().slice(0, 120), ellipsis: getComputedStyle(e).textOverflow === 'ellipsis', title: e.title || null }));
}
```

Cut-off text with an ellipsis and a `title`, a tooltip or a detail screen is a design choice; cut-off text with no way to read the rest is the finding.

**Layout: images**

```js
() => ({
  broken: [...document.images].filter(i => i.complete && i.naturalWidth === 0 && (i.currentSrc || i.src)).map(i => i.currentSrc || i.src),
  noAlt: [...document.images].filter(i => !i.hasAttribute('alt')).map(i => i.currentSrc || i.src),
  distorted: [...document.images].filter(i => {
    const fit = getComputedStyle(i).objectFit;
    return i.naturalWidth && i.width && i.height && fit !== 'cover' && fit !== 'contain' && Math.abs(i.naturalWidth / i.naturalHeight - i.width / i.height) > 0.1;
  }).map(i => i.currentSrc || i.src),
})
```

Scroll to the bottom first: a lazy image that has not been asked for yet is not broken.

**Layout: contrast, first pass**

```js
() => {
  const rgb = s => (s.match(/[\d.]+/g) || []).map(Number);
  const lum = ([r, g, b]) => [r, g, b].map(v => (v /= 255) <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4).reduce((a, v, i) => a + v * [0.2126, 0.7152, 0.0722][i], 0);
  const bg = e => {
    for (; e; e = e.parentElement) {
      const s = getComputedStyle(e), c = rgb(s.backgroundColor);
      if (s.backgroundImage !== 'none') return null;
      if (c.length === 3 || c[3] === 1) return c;
      if (c[3] > 0) return null;
    }
    return [255, 255, 255];
  };
  return [...document.querySelectorAll('body *')].flatMap(e => {
    const own = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own || !e.getClientRects().length) return [];
    const s = getComputedStyle(e), fg = rgb(s.color), b = bg(e);
    if (!b || (fg.length === 4 && fg[3] < 1)) return [];
    const [hi, lo] = [lum(fg), lum(b)].sort((x, y) => y - x), ratio = (hi + 0.05) / (lo + 0.05);
    const px = parseFloat(s.fontSize), large = px >= 24 || (px >= 18.66 && parseInt(s.fontWeight, 10) >= 700);
    return ratio < (large ? 3 : 4.5) ? [{ text: e.innerText.trim().slice(0, 50), ratio: +ratio.toFixed(2), needs: large ? 3 : 4.5, px }] : [];
  });
}
```

It judges solid colours only. Text over an image, a gradient or a translucent layer is skipped: judge those by eye on the screenshot.

**Layout: small targets**

```js
() => [...document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, [role=button], [role=link]')].flatMap(e => {
  const r = e.getBoundingClientRect();
  return r.width > 0 && r.height > 0 && (r.width < 24 || r.height < 24) && getComputedStyle(e).display !== 'inline'
    ? [{ el: (e.innerText || e.getAttribute('aria-label') || e.name || e.tagName).trim().slice(0, 40), w: Math.round(r.width), h: Math.round(r.height) }] : [];
})
```

**Content: text that looks unfinished or leaked**

```js
() => {
  const checks = {
    unfinished: /lorem ipsum|dolor sit amet|\bTODO\b|\bFIXME\b|\bTBD\b|coming soon|placeholder/i,
    leaked: /\bundefined\b|\bNaN\b|\[object Object\]|Invalid Date|\bnull\b|-?Infinity\b/,
    template: /\{\{[^}]*\}\}|\$\{[^}]*\}|%[sd]\b|\{\d+\}|<%[^>]*%>/,
    rawKey: /\b[a-z][a-zA-Z0-9]*(?:[._][a-zA-Z0-9]+){2,}\b/,
    oddNumber: /[€£$]\s?-?\d+\.\d(?!\d)|[€£$]\s?-?\d+\.\d{3,}|\d+\.\d{6,}/,
    plural: /\b1 (?:items|results|days|hours|minutes|products|orders|reviews)\b|\w\(s\)/i,
  };
  const attrs = [...document.querySelectorAll('[placeholder], [title], [alt], [aria-label]')].flatMap(e => ['placeholder', 'title', 'alt', 'aria-label'].map(a => e.getAttribute(a)));
  return [document.title, ...document.body.innerText.split('\n'), ...attrs].map(l => (l || '').trim()).filter(Boolean)
    .flatMap(l => Object.entries(checks).filter(([, re]) => re.test(l)).map(([kind]) => ({ kind, line: l.slice(0, 160) })));
}
```

`rawKey` also matches web addresses, file names and version numbers: read the hits. Spelling, a misleading label and an inconsistent name are found by reading the snapshot, not by a pattern.

**Numbers: every table as rows of text**

```js
() => [...document.querySelectorAll('table')].map(t => [...t.rows].map(r => [...r.cells].map(c => c.innerText.trim())))
```

Figures outside a table (a basket summary, a dashboard tile) are read from the snapshot.

## 3. Recomputing numbers

Copy the figures exactly as shown, then recompute. Never in the head, never with binary floats:

```bash
python3 - <<'PY'
from decimal import Decimal as D, ROUND_HALF_UP
lines = [(D('3'), D('19.99')), (D('1'), D('5.00'))]                  # quantity, unit price, as read off the screen
subtotal = sum(q * p for q, p in lines)
tax = (subtotal * D('0.20')).quantize(D('0.01'), ROUND_HALF_UP)      # rate and rounding from the document; with none, say so
print('subtotal', subtotal, 'tax', tax, 'total', subtotal + tax)
PY
```

The finding carries the figures as read, the working and the result: `shown €78.36 · recomputed 3 × 19.99 + 5.00 = 64.97; 64.97 × 0.20 = 12.99 (half up); 64.97 + 12.99 = 77.96 · difference €0.40`. To check an order, read the column into a list and compare it with `sorted()` of itself, numbers parsed as `Decimal` and dates as dates.

## 4. Driving a native app

**The Appium MCP server** must be connected; with its tools missing, stop and tell the user to register it (`qa/<stack>/skills/mobile-screen-explorer` has the command and the environment variables). Attach to an existing session before creating one, and create with `appium:noReset: true`.

| Step | Tool (`mcp__appium-mcp__…`) |
|---|---|
| Pick the device, start or attach a session | `select_device`, `appium_session_management` |
| Read the screen as structure | `appium_get_page_source` |
| Tap, swipe, scroll to | `appium_gesture` |
| Type, hide the keyboard | `appium_set_value`, `appium_mobile_keyboard` |
| Read one element's text | `appium_get_text` |
| Alerts and permission dialogs | `appium_alert` |
| WebView content | `appium_context` (switch to `WEBVIEW_*`, then the web probes apply) |
| Rotate, background and reopen | `appium_orientation`, `appium_app_lifecycle` |
| Window size, density | `appium_get_window_size`, `appium_mobile_device_info` |
| Screenshot, recording | `appium_screenshot`, `appium_screen_recording` |

The source is stale after every transition: read it again. A visible element missing from the source is an accessibility or context problem, and that is itself a finding. Never reinstall or reset the app to get back to a known place.

## 5. Native probes

Save the page source to a file and read its geometry. `W` and `H` are the window size; `SCALE` is pixels per dp on Android (density ÷ 160) and `1` on iOS, whose source is already in points.

```bash
python3 - source.xml 1080 2400 2.625 <<'PY'
import re, sys, xml.etree.ElementTree as ET
path, W, H, SCALE = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
PRESSABLE = ('Button', 'Link', 'Cell', 'Switch', 'TextField', 'SecureTextField', 'Tab')

def box(n):
    a = n.attrib
    if 'bounds' in a:
        return tuple(map(int, re.findall(r'-?\d+', a['bounds'])))
    if 'width' in a and 'x' in a:
        x, y, w, h = (int(float(a[k])) for k in ('x', 'y', 'width', 'height'))
        return x, y, x + w, y + h

def name(n):
    return next((n.attrib[k] for k in ('content-desc', 'label', 'text', 'name', 'value') if n.attrib.get(k)), '')

nodes = list(ET.parse(path).iter())
least = 48 * SCALE if any('bounds' in n.attrib for n in nodes) else 44
for n in nodes:
    b = box(n)
    if not b or n.attrib.get('displayed') == 'false' or n.attrib.get('visible') == 'false':
        continue
    x1, y1, x2, y2 = b
    pressable = n.attrib.get('clickable') == 'true' or n.tag.endswith(PRESSABLE)
    label = name(n) or next((name(c) for c in n.iter() if name(c)), '')
    where = f'{n.tag.split(".")[-1]} "{label[:40]}" {b}'
    if x2 <= x1 or y2 <= y1:
        if pressable: print('zero-size control:', where)
        continue
    if x1 < 0 or y1 < 0 or x2 > W or y2 > H:
        print('crosses the screen edge:', where)
    if pressable and not label:
        print('control with no name:', where)
    if pressable and (x2 - x1 < least or y2 - y1 < least):
        print('small target:', where)
PY
```

- An element that crosses the edge inside a scrolling list is the next row, not a defect: confirm on the screenshot.
- Overlap, truncation, alignment and contrast are judged on the screenshot; the source does not show them.
- Links, copy, numbers, behaviour and forms are checked exactly as on the web, reading the text from the source.
