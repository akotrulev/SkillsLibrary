# Step forms — one per actor

Step 5 of `runbook-writer`. Every step is a numbered line naming its actor and its action, then the whole command or screen action, then `**Expect:**` with one value (or `**Observe:**` with its open question), and `**Capture:**` when a later step needs something from it.

**Contents:**
- Variables
- API and Admin steps
- UI steps
- Device steps
- DB steps
- Sim and Job steps
- Doc and Notify steps
- Hand steps
- Observe and lag steps
- Helper scripts
- Preconditions, Setup and Cleanup

## Variables

Declared in the runbook's §1, set once in Setup, and written `NAME` in prose, `$NAME` in shell and `{{name}}` in a tool file. With a tool file, §1 gives each variable in both spellings (`BASE_URL` / `baseUrl`).

| Variable | Holds |
|---|---|
| `RUN` | The run marker, `rb-<yyyymmdd>-<n>`, `n` the day's run number: set at run time by the first Setup step, and part of every name, SKU or email the run creates |
| `BASE_URL`, `ADMIN_URL`, `WEB_URL` | Where the API, the admin API and the web UI are |
| `TOKEN` | The bearer token Setup obtains; one per role when the cases need several (`TOKEN_ADMIN`, `TOKEN_VIEWER`) |
| `DB_URL` | The connection the tester's role uses |
| `OUT` | The run's evidence folder |
| `ASYNC_BUDGET` | How long a later outcome may take, from the suite's Setup. Declared only when a step polls |
| `BASELINE_…` | A figure a precondition notes and the last Cleanup step reconciles |

A captured value is named for what it is (`PRODUCT_ID`, `AGED_PRODUCT_ID`), never `ID2`.

## API and Admin steps

Write the form the lookup detected. In every form the request names the test and step it belongs to, the body carries `RUN`, and the response is kept. An **Admin** step has the same form with the admin base URL and the admin token; when it changes what every user shares it is tagged `shared`.

**`curl`** (no project tool found):

````markdown
1. **API** — Create the product.
   ```bash
   curl -sS -X POST "$BASE_URL/api/products" \
     -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d "{\"sku\":\"$RUN-LAMP\",\"name\":\"Desk lamp $RUN\",\"price\":39.90,\"categoryId\":\"$CATEGORY_ID\"}" \
     -o "$OUT/P01.1.json" -w '%{http_code}\n'
   PRODUCT_ID=$(jq -r '.id' "$OUT/P01.1.json")
   ```
   **Expect:** `201`; the body's `sku` is `<RUN>-LAMP`, `price` is `39.90`, `status` is `Active`.   **Capture:** `PRODUCT_ID` = `id`
````

**A `.http` file** (`<NNN>-<slug>-runbook.http` beside the runbook). The step names the request; the file holds it. Two dialects exist, and the file follows the one the project's own files use:

| | JetBrains HTTP Client | VS Code REST Client |
|---|---|---|
| Name a request | `### P01.1 Create the product` | `# @name p01_1` above the request |
| Capture | `> {% client.global.set("productId", response.body.id); %}` | `@productId = {{p01_1.response.body.$.id}}` |
| Environment | `http-client.env.json`, `http-client.private.env.json` for secrets | `rest-client.environmentVariables` in settings |
| Command line | `ijhttp --env-file http-client.env.json --env staging <file>.http` | none: a person sends it from the editor |

```http
### P01.1 Create the product
POST {{baseUrl}}/api/products
Authorization: Bearer {{token}}
Content-Type: application/json

{ "sku": "{{run}}-LAMP", "name": "Desk lamp {{run}}", "price": 39.90, "categoryId": "{{categoryId}}" }

> {% client.global.set("productId", response.body.id); %}
```

**A Postman collection** (`<NNN>-<slug>-runbook.postman_collection.json`): one folder per test, one request per API step, named `P01.1 Create the product`. A capture is one line in the request's post-response script, `pm.environment.set("productId", pm.response.json().id)`. Run a test with `newman run <collection> -e <environment> --folder "P01"`.

**A Bruno folder** (`<NNN>-<slug>-runbook/`): one `.bru` file per API step, the capture in `vars:post-response { productId: res.body.id }`. Run with `bru run <folder> --env <name>`.

In a tool file the step in the runbook reads `1. **API** — Create the product: request **P01.1**.` and keeps its `Expect` and `Capture` lines. The expected value stays in the runbook, where the tester reads it.

- **One request per API step**, in the runbook's order, even when two steps send the same call with different data.
- **Every Capture the runbook names is implemented in the file**, by the tool's own means.
- **The project's environment file is used where it lies.** §1 names it and how it is passed (`--env-file api/requests/http-client.env.json`), and lists each variable it lacks. Those go in a private environment file the tester creates beside the tool file and never commits.
- **The response is kept by the tool's own means** (a `>>!` redirect, a `newman` reporter). Where it has none, the run record holds the actual values.

**A read-back** is its own step: `GET` the record, and expect each field the case asserts. A refusal is three steps: the refused request with its status and error code, a read-back, and a DB read, both showing nothing changed.

**A later outcome** is polled: repeat the read every second until the value appears or `ASYNC_BUDGET` passes, and expect the value.

## UI steps

````markdown
3. **UI-web** — On *Products* (`/admin/products`), search for `<RUN>-LAMP` [Products.Search] and open its row.
   **Expect:** One row. The detail page shows name `Desk lamp <RUN>`, price `€39.90`, status *Active*, and a *New* badge.
````

- The screen is named by its heading, with its route for the web and its path through the navigation for an app (`Shop → Lighting`).
- Controls are named by their visible label. A test id from the code follows in brackets; a locator or a screen coordinate is never the step.
- One user action per step: a search and the click on its result are one action, a save is another.
- The Expect is what is on the screen, in its words and figures. For a list it names the row; for a refusal it names the message and the field it sits under.
- A value entered is written out: `price 39.90`, not "a valid price".
- **UI-app** steps name the device and build once, in the test's header, and say when a screen must be refreshed to show new data (`pull to refresh`).
- A test never relies on where an earlier test left the browser or the app: its first UI step opens the screen it needs.

## Device steps

Device and browser state is changed through the same MCP that drives the screens: the Appium server's app-lifecycle and device-control tools, the Playwright server's network-state, resize and tab tools.

| State | Written as |
|---|---|
| App to the background, and back | `**Device** — Send Shopper to the background.` · `**Device** — Bring Shopper to the front.` |
| App killed mid-action | `**Device** — Force-stop Shopper within 1 s of pressing *Confirm*.` then a UI-app step relaunching it |
| Offline, online | `**Device** — Switch the device offline.` and, in Cleanup too, `**Device** — Switch the device online.` |
| Notification shade | `**Device** — Open the notification shade.` then a Notify step |
| Double tap, rotation, viewport | `**Device** — Press *Confirm* twice within 300 ms.` |

A Device step's Expect is the state reached (`Shopper is not in front`). The outcome under test is asserted by the steps after it: one record, never two; the message shown; the state after relaunch.

## DB steps

**A read after an action** is one step, with the rows the action should have changed and one Expect:

````markdown
2. **DB** — The product row.
   ```bash
   psql "$DB_URL" -v ON_ERROR_STOP=1 -At -v id="$PRODUCT_ID" <<'SQL'
   SELECT status, price, deleted_at IS NULL FROM catalog.products WHERE id = :'id';
   SQL
   ```
   **Expect:** `Active|39.90|t`.
````

Read what the suite's outcome means for the rows: the state, the amounts, the history or transition row, the ledger entries. A row that must not exist is a `count(*)` expecting `0`.

### The DB-write rules

1. **API first.** Each write carries a `Why not the API` line: `created_at is set by the server`.
2. **Update what the runbook created or declared.** The row comes from an API call of this run or is a fixture, and the `UPDATE` targets it by primary key.
3. **Insert or delete only what no actor can produce or remove at all.** The insert supplies every column the application requires and carries the run marker.
4. **Guard, change, verify.** A `SELECT` that must return the expected row count, the statement with the same key, a `SELECT` showing the new value.
5. **The row stays one the application could have produced**: fields that time or an operator would have changed together are changed together.
6. **Derived copies are brought along**: a cache, a search index, a read model, a denormalised column. With no way to do that, the test is marked `needs-hook` and the hook is named.
7. **Never** a schema change, a `TRUNCATE`, or a statement whose `WHERE` holds no key.

**A write** is three numbered steps: the guard, the statement, the verify. The first carries the `Why not the API` line.

````markdown
2. **DB** — Guard: the product exists and is new. *Why not the API: `created_at` is set by the server, and no endpoint accepts it.*
   ```bash
   psql "$DB_URL" -v ON_ERROR_STOP=1 -v id="$AGED_PRODUCT_ID" <<'SQL'
   SELECT id, created_at, updated_at FROM catalog.products WHERE id = :'id';
   SQL
   ```
   **Expect:** 1 row, `created_at` within the last minute.
3. **DB** — Age it by exactly 5 days.
   ```bash
   psql "$DB_URL" -v ON_ERROR_STOP=1 -v id="$AGED_PRODUCT_ID" <<'SQL'
   UPDATE catalog.products
      SET created_at = now() - interval '5 days', updated_at = now() - interval '5 days'
    WHERE id = :'id';
   SQL
   ```
   **Expect:** `UPDATE 1`.
4. **DB** — Verify.
   ```bash
   psql "$DB_URL" -v ON_ERROR_STOP=1 -v id="$AGED_PRODUCT_ID" <<'SQL'
   SELECT (now() - created_at) >= interval '5 days' AS aged FROM catalog.products WHERE id = :'id';
   SQL
   ```
   **Expect:** `aged` is `t`.
````

When the guard returns another row count, the statement is not run: the test is blocked at that step.

**An insert** lists every column the application requires (`NOT NULL`, foreign keys, a discriminator, a tenant id), from the schema lookup, and a name or code holding `RUN`. Its guard shows the key is free; its verify returns the row.

**A set of rows** is one statement keyed on the ids the API calls captured, with a guard expecting exactly that many rows.

| Engine | Client | Variable in the statement | `now − 5 days` | Which database am I on |
|---|---|---|---|---|
| PostgreSQL | `psql "$DB_URL" -v ON_ERROR_STOP=1 -v id="$X" <<'SQL'` (a here-document: `-c` does not expand variables) | `:'id'` | `now() - interval '5 days'` | `SELECT current_database();` |
| SQL Server · Azure SQL | `sqlcmd -S "$DB_HOST" -d "$DB_NAME" -b -v id="$X" -Q "…"` | `'$(id)'` | `DATEADD(day, -5, SYSUTCDATETIME())` | `SELECT DB_NAME();` |
| MySQL | `mysql --defaults-extra-file="$DB_CNF" -e "SET @id='$X'; …"` | `@id` | `UTC_TIMESTAMP() - INTERVAL 5 DAY` | `SELECT DATABASE();` |
| MongoDB | `mongosh "$MONGO_URL" --quiet --eval '…'` reading `process.env.X` | `process.env.X` | `new Date(Date.now() - 5 * 24 * 60 * 60 * 1000)` | `db.getName()` |

Timestamps are written in the zone the column is stored in. On MongoDB the guard is `countDocuments({ _id })`, the statement `updateOne({ _id }, { $set: … })`, and its Expect is `matchedCount: 1, modifiedCount: 1`.

**A boundary on a time rule** is one recipe per side, each with its own captured id. Where the suite gives the values, they are used. Where it names only a side ("still new"), the inside value sits far enough from the threshold (an hour, for a rule in days) that the run cannot cross it while it checks.

## Sim and Job steps

A **Sim** step tells the stand-in for a third party what to answer, through its own API or console: fill an order, reject a payment, expire a hold, answer late. It names the object by a captured id and has an Expect on the simulator's reply; the product's reaction is asserted by the steps after it.

```markdown
4. **Sim** — Reject the card payment `PAYMENT_ID` with reason `insufficient-funds`.
   <the whole request to the simulator>
   **Expect:** `200`; the simulator lists the payment as `Rejected`.
```

A simulator switch that changes its behaviour for everyone (auto-answer on or off) is a `shared` step with its reverse in Cleanup.

A **Job** step runs scheduled work now, through the admin endpoint or command the project has for it, and is `shared` when the job processes other users' data too. Before it, a DB read shows what the job will pick up, so the run knows it touches only its own rows:

```markdown
5. **DB** — What is due for the reminder job.
   <the whole query>
   **Expect:** `1` (this run's booking only).
6. **Job** `shared` — Run the reminder job now.
   <the whole request>
   **Expect:** `202`.
```

Where the project has no way to run a job on demand, the test waits for the schedule (the execution order names the time) or is marked `needs-hook`.

## Doc and Notify steps

A **Doc** step fetches a generated document and asserts its content as text: download it through the API, extract the text with the tool on the machine (`pdftotext -layout`, or the project's own), and expect the row or figure. A layout check is a UI step on the screen that shows the document.

```markdown
7. **Doc** — The October statement.
   <the whole download and text-extraction command>
   **Expect:** one line `Desk lamp rb-… 1 39.90`; page 1 total `39.90`.
```

A **Notify** step asserts a message where it arrives:

| Message | Read through | Expect names |
|---|---|---|
| Push | A Device step opens the notification shade, then the Appium snapshot | The title, the text, and the screen a tap opens |
| Email | The environment's mail catcher, by the recipient holding `RUN` | The subject, the figures in the body, where its link leads |
| In-app | A UI step on the inbox or the banner | The text and the screen it opens |
| Any, as sent | The dispatch row, as a DB step | The type and the recipient |

That no message arrives is polled to the end of its budget, then asserted as a count of `0`.

## Hand steps

A step only a person can do stays in its test, marked **Hand**, with exactly what to do and what to report back. An agent's run stops there and asks.

```markdown
3. **Hand** — In the feature-flag console, switch `catalogue.new-badge` off for staging. Report the time it was saved.
   **Expect:** the console shows the flag off.
```

## Observe and lag steps

**An observe step** records behaviour nobody has decided. It names exactly what to write down and the open question it feeds:

```markdown
6. **UI-app** — Open the product after its category was deleted.
   **Observe:** the screen shown, and any message (OQ-4).
```

**A lag step** measures how long an outcome takes. It is the only place a fixed moment is written:

```markdown
4. **UI-app** — Stay on *Shop → Lighting* without refreshing; look at +3 s and at +15 s.
   **Observe:** at which look the new price is shown (OQ-5).
```

With a budget the suite states, the same measurement is an Expect: `the new price is shown within LIST_BUDGET`.

## Helper scripts

A step is one command where one command can do it. A helper script is written only for what a single command cannot do, and several steps need: waiting until a condition holds, a loop against a simulator (reject every attempt until it settles), a download with its text extraction, a call that needs a signed or multi-step request.

- Use a script the project already has before writing one.
- New scripts go in `docs/runbooks/<NNN>-<slug>-runbook-tools/`, in the scripting language the project uses, else Python or shell, written to the house code rules.
- Each does one thing and is named for it (`wait-orders`, `reject-until-settled`).
- Each reads the environment and its secrets from the variables of §1, prints its target (environment and user) first on stderr, and never prints a secret.
- Each refuses to run when the environment it is pointed at is not the one the runbook names.
- Each exits non-zero on failure, with the response it got.
- No script writes to the database: DB writes stay inline, with their guard and verify.
- §1's Tools table lists each script with its use, and a step still shows the whole invocation.

## Preconditions, Setup and Cleanup

**Preconditions** are `PRE-1`…, a table checked before every session and never changed by it: the right app or site in front and the right build, the right user and account signed in, each shared switch in the state the tests need, each fixture in its required state, nothing left over from an earlier run (a search for the run-marker prefix), and each baseline noted into its `BASELINE_…` variable. Each row has how to check it and the required state. A precondition that fails stops the session; it is never "fixed" by a step outside Setup.

**Setup** steps are `S-1`…, once per run: set the variables with the day's `RUN`, obtain each token, sign in on each UI, confirm the database name, seed through the API the reference data every test shares, and declare each budget a step polls against. Each has an Expect. Tests then start signed in.

**Cleanup** steps are `C-1`…, in the reverse of creation:

1. the records the tests made, by captured id through the API where an endpoint exists, else by a guarded DB statement keyed on the id or on `RUN`;
2. the recipes' rows, then the Setup's;
3. every `shared` step reversed, by the values written down when it was changed;
4. each fixture restored to its required state;
5. a search for `RUN` on each actor, expecting nothing;
6. each baseline read again and compared with its `BASELINE_…`, every difference explained by a test.

What cannot be removed or reversed is not hidden: it is the §4 permanent-change list, and the run reports it.
