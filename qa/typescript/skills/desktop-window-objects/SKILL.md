---
name: desktop-window-objects
description: Use when creating or updating a WebdriverIO window object for a macOS or Windows app from explored elements. Triggers "create a window object". Not for finding elements (desktop-screen-explorer).
disable-model-invocation: true
---

# QA — Desktop Window Object Builder (TypeScript)

Turns a discovered element inventory into a **WebdriverIO window object**: a `BaseWindow` subclass under `src/windows/`. It consumes the element table and locator rungs from `qa/typescript/skills/desktop-screen-explorer` (or an inventory the user supplies) and emits or updates one window class. It owns **codegen, multi-window and dialog handling, waits, and the create/update diff**. The shared rules (id contract, window-object rules, window scoping) are `qa/_shared/desktop-testing`; the Mocha spec conventions are `qa/typescript/skills/ui-test-author/appium`. The mobile twin is `qa/typescript/skills/mobile-screen-objects`.

## Inputs needed

1. **Window name** (PascalCase: `LibraryWindow`, `SettingsWindow`, `ExportDialog`) and whether it is a main window, a document window, a sheet or a dialog.
2. **Element list**: per element the name, type and rung from the explorer (the test id first, `~id`).
3. **Landmark**: one container id that proves the window is up (used by `verifyWindowLoaded()`).
4. **Actions**: user-intent actions, and for each whether it opens another window or dialog (→ its class).
5. **Target project**: repo path and the existing `src/windows/` convention.

## Conventions

The standards an emitted object must meet are the qa-typescript rule files `page-objects.md`, `desktop-tests.md` and `qa-typescript.md` (the project's copy in `.claude/rules/qa-typescript/`, or the plugin's in `qa/typescript/skills/rules/`). The codegen specifics:

- Element access goes through `BaseWindow`'s finders, in ladder order: `byTestId` (`$('~id')`, the same on both platforms) → `within(container).byTestId` for rows → a label or native query as a named fallback → XPath last.
- Each id is a `private static readonly {ELEMENT}_ID` constant (a fallback is `{ELEMENT}_FALLBACK`); elements are `private get` accessors. A window exposes intent actions and value queries (text, a boolean, a count), never an element.
- Navigation actions return `Promise<{Destination}>` (`return new {Destination}()`); same-window actions return `Promise<void>`.
- Folder `src/windows/`, file `src/windows/<Window>.ts`. A repeating row is a region component picked by its content (a title, a name), never by position. A native control (date picker, combo box, tab view, outline, segmented control) is a control component in `src/components/controls/` at first use, taking its root and exposing intent (`exportDialog.format.choose('PNG')`). Neither kind extends `BaseWindow`.
- Every method is one user action, top to bottom: no boolean parameter that picks behaviour, no "if it is displayed", no platform branch. Names state the action, never the outcome.
- Per-platform ids (only where one object serves both apps) live in a locator map keyed by platform: one accessor per element, and no action branches on the platform.

## Template

```typescript
import { $, browser } from '@wdio/globals';
import type { ChainablePromiseElement } from 'webdriverio';

export abstract class BaseWindow {
  private static readonly TIMEOUT_MS = 10_000;

  protected byTestId(id: string): ChainablePromiseElement {
    return $(`~${id}`);
  }

  protected async waitUntilDisplayed(element: ChainablePromiseElement, what: string): Promise<void> {
    await browser.waitUntil(() => element.isDisplayed(), {
      timeout: BaseWindow.TIMEOUT_MS,
      timeoutMsg: `Expected ${what} to be displayed within ${BaseWindow.TIMEOUT_MS} ms`,
    });
  }

  abstract verifyWindowLoaded(): Promise<void>;
}
```

```typescript
import { expect } from '@wdio/globals';
import { BaseWindow } from './BaseWindow.js';
import { AlbumRow } from './AlbumRow.js';

export class LibraryWindow extends BaseWindow {
  private static readonly ROOT_ID = 'Library.Window';
  private static readonly SEARCH_ID = 'Library.SearchField';
  private static readonly ALBUM_TABLE_ID = 'Library.AlbumTable';

  private get root() { return this.byTestId(LibraryWindow.ROOT_ID); }
  private get search() { return this.byTestId(LibraryWindow.SEARCH_ID); }
  private get albumTable() { return this.byTestId(LibraryWindow.ALBUM_TABLE_ID); }

  async verifyWindowLoaded(): Promise<void> {
    await expect(this.root).toBeDisplayed({ message: 'Expected LibraryWindow to be visible but Library.Window was not found' });
  }

  async searchFor(text: string): Promise<void> {
    await this.search.setValue(text);
  }

  album(title: string): AlbumRow {
    return new AlbumRow(this.albumTable, title);
  }
}
```

The row holds its key and is re-resolved from its container on each call, through a wait condition with a message, because a Windows `AutomationId` repeats across rows and is unique among siblings only:

```typescript
import { browser } from '@wdio/globals';
import type { ChainablePromiseElement } from 'webdriverio';

export class AlbumRow {
  private static readonly ROW_ID = 'Library.Row';
  private static readonly TITLE_ID = 'Library.Row.Title';
  private static readonly ARTIST_ID = 'Library.Row.Artist';
  private static readonly TIMEOUT_MS = 10_000;

  constructor(private readonly table: ChainablePromiseElement, private readonly albumTitle: string) {}

  async artistText(): Promise<string> {
    return (await this.row()).$(`~${AlbumRow.ARTIST_ID}`).getText();
  }

  async open(): Promise<void> {
    await (await this.row()).doubleClick();
  }

  private async row(): Promise<WebdriverIO.Element> {
    return browser.waitUntil(() => this.matchingRow(), {
      timeout: AlbumRow.TIMEOUT_MS,
      timeoutMsg: `No ${AlbumRow.ROW_ID} in the album table shows ${this.albumTitle}`,
    });
  }

  private async matchingRow(): Promise<WebdriverIO.Element | undefined> {
    return this.table
      .$$(`~${AlbumRow.ROW_ID}`)
      .findSeries(async (row) => (await row.$(`~${AlbumRow.TITLE_ID}`).getText()) === this.albumTitle);
  }
}
```

On macOS a row that combines its children (`.accessibilityElement(children: .combine)`) exposes only the row id: match on the row's own `label` or `value` and drop the child accessor.

A fallback (no id yet): name the constant `*_FALLBACK`, use a label or native query before XPath, and add the row to `missing-testids.md`. This one is Windows, where `name=` reads the UIA `Name`; on Mac2 `name` is the `identifier`, so a macOS label fallback is a `predicate string` on `label`:

```typescript
private static readonly EXPORT_BUTTON_FALLBACK = 'Export…';
private get exportButton() { return $(`name=${ExportDialog.EXPORT_BUTTON_FALLBACK}`); }
```

## Multi-window and dialogs

- **A window object is bound to one window.** The action that opens another window returns the destination's object, and the destination's constructor or `verifyWindowLoaded()` switches to it. Switching is a method on `BaseWindow`, never inline in a test.
- **Mac2:** find the window with `driver.executeScript('macos: listWindows', [])` (driver 4.5.0 and later) and match on `title`. **WinCore:** `driver.getWindowHandles()` omits untitled windows, so use `windows: getWindows` and match on `title` or `className`, then `driver.switchToWindow(handle)`.
- Switch back to the previous window object after a dialog closes: the action that confirms or cancels returns the parent window's object.
- Wait for the destination's landmark, never for a duration. A dialog that must appear is asserted with `waitUntil` on the window count or on its landmark, with a message naming the dialog.
- A system panel (open/save, permission) is another process: model it as its own small object with ids read from its tree, or report it. A UAC prompt is never driven.
- A quit with unsaved work is asserted: the confirmation prompt appears, then the test chooses.

## Waits

`BaseWindow.waitUntilDisplayed` and the `waitFor*` element commands (`waitForDisplayed`, `waitForEnabled`) are the only waits. Add a new wait to the base class, never inline in a window object or a spec, and no `browser.pause` anywhere. The timeout message names the element and the window.

## Procedure

1. **Check for an existing object.** Glob `**/src/windows/<Window>.ts`. Exists → **update** (step 4). The project has no `src/windows/` → run `qa/typescript/skills/desktop-project-setup` first.
2. **Map each element to a constant and accessor** by its rung. Test-id elements use `byTestId`; fallbacks are `*_FALLBACK` with a `missing-testids.md` row. Each repeating group becomes a region component addressed inside its container and picked by content; each native control becomes a control component, reusing the project's class when one exists.
3. **Write the class** per the conventions: constants, `private get` accessors, `verifyWindowLoaded()` on the landmark, one intent-named `async` action per user action, one query method per datum a test reads. Stub any destination window that does not exist.
4. **Update mode, diff before writing:**
   - New element, not in the class → add constant and accessor or action.
   - Constant in the class, element gone from the window → flag and **ask** before deleting (it may belong to a state not reached).
   - An id changed → update the constant and note it as a breaking rename.
   - A fallback where an id now exists → upgrade to `byTestId`, rename, remove the row from `missing-testids.md`.
   - Never reorder or rename public methods tests already call without flagging it.
5. **Verify:** `npx tsc --noEmit` clean. Confirm the landmark matches what the explorer reported.
6. **Report:** class created or updated (diff summary), counts (id-backed / fallback / ⚠ XPath), destination stubs, open questions.

## Rules

- **Discovery is not this skill's job**: never invent a locator.
- One class per window; update in place rather than creating a duplicate.
- A window object takes no driver; `$` appears only in `BaseWindow` and components. The only assertion inside an object is `verifyWindowLoaded()`.
- Everything else is the rule files named under Conventions; where they and this skill disagree, the rule files win.
