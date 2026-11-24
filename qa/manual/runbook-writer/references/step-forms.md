# Step forms — API, UI and DB

Step 5 of `runbook-writer`. One form per channel. Every step is a numbered line naming its channel and its action, then the command or screen action, then `**Expect:**` with one value, and `**Capture:**` when a later step needs something from it.

## Variables

Declared in the runbook's §1, set once before Setup, and written `NAME` in prose, `$NAME` in shell and `{{name}}` in a tool file.

| Variable | Holds |
|---|---|
| `RUN` | The run marker, `rb-<yyyymmdd>-<n>`, `n` the day's run number: set at run time by the first Setup step, and part of every name, SKU or email the run creates |
| `BASE_URL`, `WEB_URL` | Where the API and the web UI are |
| `TOKEN` | The bearer token Setup obtains; one per role when the cases need several (`TOKEN_ADMIN`, `TOKEN_VIEWER`) |
| `DB_URL` | The connection the tester's role uses |
| `OUT` | The run's evidence folder, where responses are saved |
| `ASYNC_BUDGET` | How long a later effect may take, from the suite's Setup. Declared only when a script polls |

A captured value is named for what it is (`PRODUCT_ID`, `AGED_PRODUCT_ID`), never `ID2`. With a tool file, §1's variable table gives each variable in both spellings (`BASE_URL` / `baseUrl`).

## API steps

Write the form the lookup detected. In every form the request names the script and step it belongs to, the body carries `RUN`, and the response is kept.

**`curl`** (no project tool found):

````markdown
1. **API** — Create the product.
   ```bash
   curl -sS -X POST "$BASE_URL/api/products" \
     -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d "{\"sku\":\"$RUN-LAMP\",\"name\":\"Desk lamp $RUN\",\"price\":39.90,\"categoryId\":\"$CATEGORY_ID\"}" \
     -o "$OUT/RB-01.1.json" -w '%{http_code}\n'
   PRODUCT_ID=$(jq -r '.id' "$OUT/RB-01.1.json")
   ```
   **Expect:** `201`; the body's `sku` is `<RUN>-LAMP`, `price` is `39.90`, `status` is `Active`.   **Capture:** `PRODUCT_ID` = `id`
````

**A `.http` file** (`<NNN>-<slug>-runbook.http` beside the runbook). The step names the request; the file holds it. Two dialects exist, and the file follows the one the project's own files use:

| | JetBrains HTTP Client | VS Code REST Client |
|---|---|---|
| Name a request | `### RB-01.1 Create the product` | `# @name rb01_1` above the request |
| Capture | `> {% client.global.set("productId", response.body.id); %}` | `@productId = {{rb01_1.response.body.$.id}}` |
| Environment | `http-client.env.json`, `http-client.private.env.json` for secrets | `rest-client.environmentVariables` in settings |
| Command line | `ijhttp --env-file http-client.env.json --env staging <file>.http` | none: a person sends it from the editor |

```http
### RB-01.1 Create the product
POST {{baseUrl}}/api/products
Authorization: Bearer {{token}}
Content-Type: application/json

{ "sku": "{{run}}-LAMP", "name": "Desk lamp {{run}}", "price": 39.90, "categoryId": "{{categoryId}}" }

> {% client.global.set("productId", response.body.id); %}
```

**A Postman collection** (`<NNN>-<slug>-runbook.postman_collection.json`): one folder per script, one request per API step, named `RB-01.1 Create the product`. A capture is one line in the request's post-response script, `pm.environment.set("productId", pm.response.json().id)`. Run a script with `newman run <collection> -e <environment> --folder "RB-01"`.

**A Bruno folder** (`<NNN>-<slug>-runbook/`): one `.bru` file per API step, the capture in `vars:post-response { productId: res.body.id }`. Run with `bru run <folder> --env <name>`.

In a tool file the step in the runbook reads `1. **API** — Create the product: request **RB-01.1**.` and keeps its `Expect` and `Capture` lines. The expected value stays in the runbook, where the tester reads it.

- **One request per API step**, in the runbook's order, even when two steps send the same call with different data: the file is read top to bottom like the runbook.
- **Every Capture the runbook names is implemented in the file**, by the tool's own means.
- **The project's environment file is used where it lies.** §1 names it and how it is passed (`--env-file api/requests/http-client.env.json`), and lists each variable it lacks (`run`, the accounts). Those go in a private environment file the tester creates beside the tool file and never commits.
- **The response is kept by the tool's own means** (a `>>!` redirect, a `newman` reporter). Where it has none, the run record holds the actual values.

**A read-back** is its own step: `GET` the record, and expect each field the case asserts. A refusal is two steps: the refused request with its status and error code, then a read-back showing nothing changed.

**A later effect** is polled: repeat the read every second until the value appears or `ASYNC_BUDGET` passes, and expect the value.

## UI steps

````markdown
3. **UI-web** — On *Products* (`/admin/products`), search for `<RUN>-LAMP` [Products.Search] and open its row.
   **Expect:** One row. The detail page shows name `Desk lamp <RUN>`, price `€39.90`, status *Active*, and a *New* badge.
````

- The screen is named by its heading, with its route for the web and its path through the navigation for an app (`Shop → Lighting`).
- Controls are named by their visible label. A test id from the code follows in brackets; a locator is never the step.
- One user action per step: a search and the click on its result are one action, a save is another.
- The Expect is what is on the screen, in its words and figures. For a list it names the row; for a refusal it names the message and the field it sits under, and a following step shows the record unchanged.
- A value entered is written out: `price 39.90`, not "a valid price".
- **UI-app** steps name the device and build from the Access table once, in the script's header, and say when a screen must be refreshed to show new data (`pull to refresh`).
- A step that must start from a state the previous script changed begins with the action that reaches it. Scripts never rely on where an earlier script left the browser.

## DB steps

A DB step is three numbered steps: the guard, the statement, the verify. The first carries the `Why not the API` line.

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

When the guard returns another row count, the statement is not run: the script is blocked at that step.

**An insert** lists every column the application requires (`NOT NULL`, foreign keys, a discriminator, a tenant id), from the schema lookup, and a name or code holding `RUN`. Its guard shows the key is free; its verify returns the row.

**A set of rows** (ten products spread over a month) is one statement keyed on the ids the API calls captured, with a guard expecting exactly that many rows.

| Engine | Client | Variable in the statement | `now − 5 days` | Which database am I on |
|---|---|---|---|---|
| PostgreSQL | `psql "$DB_URL" -v ON_ERROR_STOP=1 -v id="$X" <<'SQL'` (a here-document: `-c` does not expand variables) | `:'id'` | `now() - interval '5 days'` | `SELECT current_database();` |
| SQL Server · Azure SQL | `sqlcmd -S "$DB_HOST" -d "$DB_NAME" -b -v id="$X" -Q "…"` | `'$(id)'` | `DATEADD(day, -5, SYSUTCDATETIME())` | `SELECT DB_NAME();` |
| MySQL | `mysql --defaults-extra-file="$DB_CNF" -e "SET @id='$X'; …"` | `@id` | `UTC_TIMESTAMP() - INTERVAL 5 DAY` | `SELECT DATABASE();` |
| MongoDB | `mongosh "$MONGO_URL" --quiet --eval '…'` reading `process.env.X` | `process.env.X` | `new Date(Date.now() - 5 * 24 * 60 * 60 * 1000)` | `db.getName()` |

Timestamps are written in the zone the column is stored in. On MongoDB the guard is `countDocuments({ _id })`, the statement `updateOne({ _id }, { $set: … })`, and its Expect is `matchedCount: 1, modifiedCount: 1`.

**A boundary on a time rule** is one recipe per side, each with its own captured id: for "new for 5 days", a product aged 5 days less one hour still has the badge, and a product aged exactly 5 days does not. Where the suite gives the values, they are used. Where it names only a side ("still new"), the inside value sits far enough from the threshold (an hour, for a rule in days) that the run cannot cross it while it checks.

## Setup and Cleanup

**Setup** steps are `S-1`…: set the variables with the day's `RUN`, obtain each token, sign in on each UI, confirm the database name, seed the reference data every script shares through the API, and declare each budget a script polls against. Each has an Expect. Scripts then start signed in.

**Cleanup** steps are `C-1`…, in the reverse of creation: records the scripts made, then the recipes' rows, then the Setup's. Each removes by captured id through the API where an endpoint exists, else by a guarded DB statement keyed on the id or on `RUN`. The last step lists what is left: a search for `RUN` on each channel, expecting nothing.
