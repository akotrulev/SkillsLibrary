# Page anatomy and form layout

The depth behind [`ux-patterns`](../SKILL.md) §3 and §4. The page-type table's primary actions and the surface rule stay in the skill; what each type is made of and its rules are here.

## §3 — the skeleton

Every page has the same skeleton — **header · optional toolbar · content region(s)** — so people learn it once:

- **Page header:** the title (one `h1`, and it is the same words as the nav label and the route title — `ui-rules`' one-name rule); breadcrumb above it from depth two; **one primary action** at the right, verb-labeled (`ux-writing`); at most two secondary actions visible, the rest in an overflow menu; a short status/summary line when the entity has state.
- **Toolbar** (list pages): search, filters, view switch, bulk actions — rendered *above* the data region so a failed load never unmounts them (`error-handling` owns the scoping).
- **Content region(s):** each carries its own loading / loaded / failed / empty state (`error-handling`); a page never shows one spinner for everything.

## §3 — rules per page type

| Page type | Made of | Rules |
|---|---|---|
| **List** | toolbar · table or card grid · pagination | A row is a link to its detail; the table is the default, cards only when the visual (image, status) *is* the information; filters reflect in the URL; correctness rules (sort, paging, truncation, bulk) are `ui-rules`' |
| **Detail** | header with status + key facts · sections or tabs · related lists | Tabs only when sections are independent and > 3; otherwise one scrolling page with anchored sections; related lists link back to their own list pages; edit is in place or a sibling route, never a modal for a long form |
| **Form** (create / edit) | one column · grouped sections · sticky footer for long forms | Layout in §4; a create form opens from the list's primary action and returns to the created item's detail on success |
| **Dashboard** | KPI row · one primary chart · one or two tables of what needs attention | Every tile is a link to the list it summarises, filtered to the tile's meaning; no tile without a next step; no chart without a question it answers (chart craft: [`design/charts`](../../charts/SKILL.md)); "what needs my attention" beats "what happened" |
| **Wizard** | numbered steps · progress · back/next · a review step | Only for ≥ 4 steps whose later inputs depend on earlier ones; otherwise a sectioned form; draft is saved between steps; back never loses input; the review step is the confirmation |
| **Settings** | grouped sections, each a small form | Destructive settings (delete workspace) are the last section, visually separated, confirmed by object name (`ui-rules`) |

## §4 — form layout

- **One column.** Multi-column forms break the eye's path and hide fields; the exception is a genuinely paired short field (city · postcode).
- **Labels above fields**, always visible — placeholders are hints, never labels (`ui-code-audit` flags the code smell; the decision is here).
- **Group into titled sections** past ~7 fields; the section title is the user's word for that part of the object.
- **Required is the default; mark the optional.** Marking every required field with an asterisk on a form that is 90 % required inverts the signal.
- **Field width follows expected content** — a 40-character-wide field for a 4-digit code invites the wrong input.
- **Defaults and prefill do the common case.** A field the system can infer (currency from the account, date as today, the current user as owner) is prefilled and editable, not empty.
- **Primary action where the eye ends:** bottom of the form, leading edge, verb-labeled; Cancel beside it as the secondary; a destructive action is never adjacent to Save. Long forms get a sticky footer so the action is always reachable.
- **Unsaved changes are guarded** on navigation away (mechanics: `ui-code-audit`'s rule / the stack's `forms`); validation timing and error rendering are the stack's `forms`.
- **Progressive disclosure inside a form:** advanced or rarely-used fields sit behind an "Advanced" expander, collapsed by default, never hidden on another page.
