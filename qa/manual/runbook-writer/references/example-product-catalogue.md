# Worked example — a product catalogue

The filled example for `runbook-writer`: a ten-case suite in, a runbook out. The system has an API, a web admin where a catalogue admin manages products, and a shopper app that only shows them. **Shape is normative; domain content is illustrative.** The matrix lists all seventeen scripts; seven are written out here, and a real runbook writes every one. "In the form of RB-02 step 1" abbreviates this example only: a real runbook holds every command whole.

**Contents:**
- Input — the suite, in short
- Output

## Input — the suite, in short

> **BR-1** A SKU is unique among products that are not deleted; a duplicate is refused with `409 sku-taken`.
> **BR-2** A product is *New* for 5 days after it was created.
> **BR-3** Deleting a product removes it from every list and from the shopper app; the record is kept.
> **BR-5** A product with no category is listed under *Uncategorised*.
> **TC-PROD-001** journey · An admin adds a product and a shopper sees it · P1
> **TC-PROD-002…005** data · create, read, update, delete · P1, P2, P1, P1
> **TC-PROD-006** rule · A duplicate SKU is refused and nothing is created · P1
> **TC-PROD-007** temporal · The *New* badge is shown until the product is 5 days old · P1
> **TC-PROD-008** data · A product from before categories existed is listed under *Uncategorised* · P2
> **TC-PROD-009** field · Price and name accept what is valid and refuse what is not · P2
> **TC-PROD-010** permission · A viewer cannot create a product · P1

## Output

````markdown
# Runbook — Product catalogue (004)

**Covers:** `docs/test-cases/004-product-catalogue.md`, from `docs/specs/004-product-catalogue-design.md`   **Version:** 1 · 2026-11-24
**Channels:** API · UI-web · UI-app · DB
**API calls as:** curl (none found: `**/*.http`, `**/*.rest`, `**/*.postman_collection.json`, `**/*.bru`)
**Codebase read:** API `services/catalogue` @ `4c1e9a2` · web `apps/admin` @ `4c1e9a2` · app `apps/shopper` @ `77b03de`

## 1. Access

| Channel | Where | How to get in | Source |
|---|---|---|---|
| API | `BASE_URL` = `https://api.staging.example.test` | `POST /auth/token`: `QA_ADMIN_USER` (role `catalogue-admin`), `QA_VIEWER_USER` (role `viewer`) | detected `services/catalogue/Program.cs:41` |
| UI-web | `WEB_URL` = `https://admin.staging.example.test` | Sign in as `QA_ADMIN_USER` | stated |
| UI-app | Shopper `2.14.0 (381)`, Pixel 8 emulator, Android 16 | Sign in as `QA_SHOPPER_USER` | stated |
| DB | PostgreSQL 17, database `catalogue_staging`, `DB_URL` | `psql "$DB_URL"`, role `qa_dml` with DML on schema `catalog` | stated |

| Variable | Meaning | Set by |
|---|---|---|
| `RUN` | Run marker, `rb-<yyyymmdd>-<n>`, `n` the day's run number | S-1 |
| `OUT` | The run's evidence folder | S-1 |
| `TOKEN`, `TOKEN_VIEWER` | Bearer tokens | S-2 |
| `CATEGORY_ID` | The category *Lighting `<RUN>`* | S-4 |
| `LIST_BUDGET` | 60 s: the shopper list is cached for that long (detected `services/catalogue/Products/ProductListCache.cs:14`) | S-1 |
| `QA_*_USER`, `QA_*_PASSWORD`, `DB_URL` | Accounts and the connection | the tester's shell, from the secret store |

## 2. Surface map

| Operation | API | UI-web | UI-app | DB | Source |
|---|---|---|---|---|---|
| Create | `POST /api/products` | *Products → New product* (`/admin/products/new`) | not offered | `catalog.products` | detected `ProductsController.cs:31`, `apps/admin/app/products/new/page.tsx:12` |
| Read | `GET /api/products`, `GET /api/products/{id}` | *Products* (`/admin/products`), the detail page | *Shop → <category>* | `catalog.products` | detected `ProductsController.cs:18`, `apps/shopper/app/shop/[category].tsx:9` |
| Update | `PUT /api/products/{id}` | the detail page, *Edit* | not offered | `catalog.products` | detected `ProductsController.cs:52` |
| Delete | `DELETE /api/products/{id}` (sets `deleted_at`) | the detail page, *Delete* | not offered | `catalog.products.deleted_at` | detected `ProductsController.cs:67`, `Migrations/0007_soft_delete.sql:3` |

`created_at` is set by a column default and no endpoint accepts it (`Migrations/0001_products.sql:9`). `categoryId` is required by the create validator (`CreateProductValidator.cs:14`).

## 3. Coverage matrix

| Script | Carries out | Layer | Priority | Arrange | Act | Assert |
|---|---|---|---|---|---|---|
| RB-01 | TC-PROD-001 | journey | P1 | S-4 | UI-web | UI-web · UI-app · API |
| RB-02 | TC-PROD-002 | data | P1 | S-4 | API | API · UI-web · UI-app |
| RB-03 | TC-PROD-003 | data | P2 | S-5 | API | API |
| RB-04 | TC-PROD-003, UI-web-driven | data | P2 | S-5 | UI-web | UI-web |
| RB-05 | TC-PROD-003, UI-app-driven | data | P2 | S-5 | UI-app | UI-app |
| RB-06 | TC-PROD-004 | data | P1 | API | API | API · UI-web · UI-app |
| RB-07 | TC-PROD-004, UI-web-driven | data | P1 | API | UI-web | UI-web · API · UI-app |
| RB-08 | TC-PROD-005 | data | P1 | API | API | API · UI-web · UI-app · DB |
| RB-09 | TC-PROD-005, UI-web-driven | data | P1 | API | UI-web | UI-web · API |
| RB-10 | TC-PROD-006 | rule | P1 | API | API | API |
| RB-11 | TC-PROD-006 | rule | P2 | API | UI-web | UI-web · API |
| RB-12 | TC-PROD-007 | temporal | P1 | R-1, R-2 | API | API |
| RB-13 | TC-PROD-007 | temporal | P1 | R-1, R-2 | UI-app | UI-app |
| RB-14 | TC-PROD-008 | data | P2 | R-3 | UI-web | UI-web · API |
| RB-15 | TC-PROD-009 | field | P2 | S-4 | API | API |
| RB-16 | TC-PROD-009 | field | P3 | S-4 | UI-web | UI-web · API |
| RB-17 | TC-PROD-010 | permission | P1 | S-4 | API | API |

### Operation grid

| Operation | Driven by API | Driven by UI-web | Driven by UI-app | Asserted on |
|---|---|---|---|---|
| Create | RB-02 | RB-01 | not offered: the shopper app only reads | UI-web, UI-app, API |
| Read | RB-03 | RB-04 | RB-05 | API, UI-web, UI-app |
| Update | RB-06 | RB-07 | not offered: the shopper app only reads | UI-web, UI-app, API |
| Delete | RB-08 | RB-09 | not offered: the shopper app only reads | UI-web, UI-app, API, DB |

## 4. Setup — run once

- **S-1** Set the variables. Raise the last digit of `RUN` for a second run on the same day.
  ```bash
  RUN=rb-$(date +%Y%m%d)-1
  OUT=evidence/$(date +%F)-product-catalogue-run
  LIST_BUDGET=60
  mkdir -p "$OUT"
  ```
  **Expect:** the folder exists.
- **S-2** **API** — Obtain the admin token. Repeat with `QA_VIEWER_USER` for `TOKEN_VIEWER`.
  ```bash
  curl -sS -X POST "$BASE_URL/auth/token" -H "Content-Type: application/json" \
    -d "{\"username\":\"$QA_ADMIN_USER\",\"password\":\"$QA_ADMIN_PASSWORD\"}" \
    -o "$OUT/S-2.json" -w '%{http_code}\n'
  TOKEN=$(jq -r '.accessToken' "$OUT/S-2.json")
  ```
  **Expect:** `200`.   **Capture:** `TOKEN` = `accessToken`
- **S-3** **DB** — Confirm the database.
  ```bash
  psql "$DB_URL" -At -c "SELECT current_database();"
  ```
  **Expect:** `catalogue_staging`.
- **S-4** **API** — Create the category every script uses.
  ```bash
  curl -sS -X POST "$BASE_URL/api/categories" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"name\":\"Lighting $RUN\"}" -o "$OUT/S-4.json" -w '%{http_code}\n'
  CATEGORY_ID=$(jq -r '.id' "$OUT/S-4.json")
  ```
  **Expect:** `201`.   **Capture:** `CATEGORY_ID` = `id`
- **S-5** **API** — Create the two products the read scripts list: `<RUN>-SHELF` (*Wall shelf `<RUN>`*, 24.00) and `<RUN>-STOOL` (*Step stool `<RUN>`*, 18.50), in the form of RB-02 step 1.
  **Expect:** `201` twice.   **Capture:** `SHELF_ID`, `STOOL_ID`
- **S-6** **UI-web** — Open `WEB_URL` and sign in as `QA_ADMIN_USER`.
  **Expect:** The *Products* heading.
- **S-7** **UI-app** — Open Shopper and sign in as `QA_SHOPPER_USER`.
  **Expect:** The *Shop* tab.

## 5. Data recipes

### R-1 — A product one hour short of 5 days old

*Why not the API: `created_at` is set by a column default, and no endpoint accepts it.* The inside value sits an hour from the threshold so the run cannot cross it while it checks. Derived copy: the shopper list cache, which the scripts wait out with `LIST_BUDGET`.

1. **API** — Create `<RUN>-AGED-IN` (*Floor lamp `<RUN>`*, 59.00) in the form of RB-02 step 1.
   **Expect:** `201`.   **Capture:** `AGED_IN_ID` = `id`
2. **DB** — Guard: the row exists and is new.
   ```bash
   psql "$DB_URL" -v ON_ERROR_STOP=1 -v id="$AGED_IN_ID" <<'SQL'
   SELECT id, created_at FROM catalog.products WHERE id = :'id';
   SQL
   ```
   **Expect:** 1 row, `created_at` within the last minute.
3. **DB** — Age it.
   ```bash
   psql "$DB_URL" -v ON_ERROR_STOP=1 -v id="$AGED_IN_ID" <<'SQL'
   UPDATE catalog.products
      SET created_at = now() - interval '5 days' + interval '1 hour',
          updated_at = now() - interval '5 days' + interval '1 hour'
    WHERE id = :'id';
   SQL
   ```
   **Expect:** `UPDATE 1`.
4. **DB** — Verify.
   ```bash
   psql "$DB_URL" -v ON_ERROR_STOP=1 -v id="$AGED_IN_ID" <<'SQL'
   SELECT (now() - created_at) < interval '5 days' AS inside FROM catalog.products WHERE id = :'id';
   SQL
   ```
   **Expect:** `inside` is `t`.

### R-2 — A product exactly 5 days old

As R-1 with SKU `<RUN>-AGED-OUT` (*Table lamp `<RUN>`*, 45.00), captured as `AGED_OUT_ID`, and `created_at = now() - interval '5 days'`. The verify selects `(now() - created_at) >= interval '5 days' AS outside` and expects `t`.

### R-3 — A product from before categories existed

*Why not the API: `categoryId` is required by the create validator, so no call can produce a product without one.*

1. **DB** — Guard: the id and the SKU are free.
   ```bash
   LEGACY_ID=$(uuidgen | tr 'A-Z' 'a-z')
   psql "$DB_URL" -v ON_ERROR_STOP=1 -At -v id="$LEGACY_ID" -v sku="$RUN-LEGACY" <<'SQL'
   SELECT count(*) FROM catalog.products WHERE id = :'id' OR sku = :'sku';
   SQL
   ```
   **Expect:** `0`.   **Capture:** `LEGACY_ID`
2. **DB** — Insert it as the 2023 import left such rows: no category, status `Active`.
   ```bash
   psql "$DB_URL" -v ON_ERROR_STOP=1 -v id="$LEGACY_ID" -v sku="$RUN-LEGACY" -v name="Reading lamp $RUN" <<'SQL'
   INSERT INTO catalog.products (id, sku, name, price, category_id, status, created_at, updated_at)
   VALUES (:'id', :'sku', :'name', 29.00, NULL, 'Active', '2023-06-01T09:00:00Z', '2023-06-01T09:00:00Z');
   SQL
   ```
   **Expect:** `INSERT 0 1`.
3. **API** — Verify the application reads it.
   ```bash
   curl -sS "$BASE_URL/api/products/$LEGACY_ID" -H "Authorization: Bearer $TOKEN" \
     -o "$OUT/R-3.3.json" -w '%{http_code}\n'
   ```
   **Expect:** `200`; `categoryId` is `null`.

## 6. Scripts

### RB-01 — An admin adds a product on the web and a shopper finds it in the app (P1 · journey)
**Carries out:** TC-PROD-001   **Uses:** S-4   **Device:** Shopper 2.14.0 (381), Pixel 8 emulator

1. **UI-web** — Open *Products* (`/admin/products`).
   **Expect:** The *Products* heading and the *New product* button.
2. **UI-web** — Press *New product* [Products.New]. Enter SKU `<RUN>-LAMP`, name `Desk lamp <RUN>`, price `39.90`, category *Lighting `<RUN>`*, and press *Save* [ProductForm.Save].
   **Expect:** The detail page of *Desk lamp `<RUN>`*: price `€39.90`, status *Active*, a *New* badge.   **Capture:** `LAMP_ID` = the id in the page's address
3. **UI-web** — Open *Products* and search for `<RUN>-LAMP` [Products.Search].
   **Expect:** One row: *Desk lamp `<RUN>`*, `€39.90`, *Active*.
4. **UI-app** — As the shopper, open *Shop → Lighting `<RUN>`* and pull to refresh until the product appears, within `LIST_BUDGET`.
   **Expect:** *Desk lamp `<RUN>`* at `€39.90`, with a *New* badge.
5. **API** — Read the product back.
   ```bash
   curl -sS "$BASE_URL/api/products/$LAMP_ID" -H "Authorization: Bearer $TOKEN" \
     -o "$OUT/RB-01.5.json" -w '%{http_code}\n'
   ```
   **Expect:** `200`; `sku` is `<RUN>-LAMP`, `price` is `39.90`, `status` is `Active`, `isNew` is `true`.

### RB-02 — A product created through the API shows on the web and in the app (P1 · data)
**Carries out:** TC-PROD-002   **Uses:** S-4

1. **API** — Create the product.
   ```bash
   curl -sS -X POST "$BASE_URL/api/products" \
     -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d "{\"sku\":\"$RUN-CHAIR\",\"name\":\"Folding chair $RUN\",\"price\":32.00,\"categoryId\":\"$CATEGORY_ID\"}" \
     -o "$OUT/RB-02.1.json" -w '%{http_code}\n'
   CHAIR_ID=$(jq -r '.id' "$OUT/RB-02.1.json")
   ```
   **Expect:** `201`; `sku` is `<RUN>-CHAIR`, `price` is `32.00`, `status` is `Active`.   **Capture:** `CHAIR_ID` = `id`
2. **UI-web** — On *Products* (`/admin/products`), search for `<RUN>-CHAIR` and open its row.
   **Expect:** The detail page shows *Folding chair `<RUN>`*, `€32.00`, *Active*, category *Lighting `<RUN>`*.
3. **UI-app** — Open *Shop → Lighting `<RUN>`* and pull to refresh until the product appears, within `LIST_BUDGET`.
   **Expect:** *Folding chair `<RUN>`* at `€32.00`.

### RB-07 — A price changed on the web is the price the API and the app give (P1 · data)
**Carries out:** TC-PROD-004, UI-web-driven   **Uses:** S-4

1. **API** — Create `<RUN>-DESK` (*Standing desk `<RUN>`*, 310.00) in the form of RB-02 step 1.
   **Expect:** `201`.   **Capture:** `DESK_ID` = `id`
2. **UI-web** — Open `/admin/products/<DESK_ID>`, press *Edit* [Product.Edit], set the price to `289.00` and press *Save* [ProductForm.Save].
   **Expect:** The detail page shows `€289.00`.
3. **API** — Read the product back in the form of RB-01 step 5, saving the body as `RB-07.3.json`.
   **Expect:** `200`; `price` is `289.00`, `name` is `Standing desk <RUN>`.
4. **UI-app** — Open *Shop → Lighting `<RUN>`* and pull to refresh until the price changes, within `LIST_BUDGET`.
   **Expect:** *Standing desk `<RUN>`* at `€289.00`.

### RB-08 — A product deleted through the API is gone everywhere, and its record is kept (P1 · data)
**Carries out:** TC-PROD-005   **Uses:** S-4

1. **API** — Create `<RUN>-RUG` (*Wool rug `<RUN>`*, 120.00) in the form of RB-02 step 1.
   **Expect:** `201`.   **Capture:** `RUG_ID` = `id`
2. **API** — Delete it.
   ```bash
   curl -sS -X DELETE "$BASE_URL/api/products/$RUG_ID" -H "Authorization: Bearer $TOKEN" \
     -o "$OUT/RB-08.2.json" -w '%{http_code}\n'
   ```
   **Expect:** `204`.
3. **API** — Read it back in the form of RB-01 step 5, saving the body as `RB-08.3.json`.
   **Expect:** `404`; the error code is `product-not-found`.
4. **UI-web** — On *Products*, search for `<RUN>-RUG`.
   **Expect:** *No products found*.
5. **UI-app** — Open *Shop → Lighting `<RUN>`* and pull to refresh until the product is gone, within `LIST_BUDGET`.
   **Expect:** No *Wool rug `<RUN>`* in the list.
6. **DB** — The record is kept. *Why not the API: no response and no screen shows a deleted product.*
   ```bash
   psql "$DB_URL" -v ON_ERROR_STOP=1 -At -v id="$RUG_ID" <<'SQL'
   SELECT count(*) FROM catalog.products WHERE id = :'id' AND deleted_at IS NOT NULL;
   SQL
   ```
   **Expect:** `1`.

### RB-12 — The API calls a product new until it is 5 days old (P1 · temporal)
**Carries out:** TC-PROD-007   **Uses:** R-1, R-2

| Product | Age | Working | `isNew` |
|---|---|---|---|
| `AGED_IN_ID` | 5 days − 1 hour | 119 h < 120 h | `true` |
| `AGED_OUT_ID` | 5 days | 120 h is not < 120 h | `false` |

1. **API** — Read `AGED_IN_ID` in the form of RB-01 step 5, saving the body as `RB-12.1.json`.
   **Expect:** `200`; `isNew` is `true`.
2. **API** — Read `AGED_OUT_ID` the same way, saving the body as `RB-12.2.json`.
   **Expect:** `200`; `isNew` is `false`.

### RB-13 — The shopper sees the New badge until the product is 5 days old (P1 · temporal)
**Carries out:** TC-PROD-007   **Uses:** R-1, R-2   **Device:** Shopper 2.14.0 (381), Pixel 8 emulator

1. **UI-app** — Open *Shop → Lighting `<RUN>`* and pull to refresh until *Table lamp `<RUN>`* shows no badge, within `LIST_BUDGET`.
   **Expect:** *Table lamp `<RUN>`* with no *New* badge.
2. **UI-app** — Find *Floor lamp `<RUN>`* in the same list.
   **Expect:** *Floor lamp `<RUN>`* with a *New* badge.

### RB-14 — A product with no category is listed under Uncategorised (P2 · data)
**Carries out:** TC-PROD-008   **Uses:** R-3

1. **UI-web** — On *Products*, choose the category filter *Uncategorised* [Products.CategoryFilter] and search for `<RUN>-LEGACY`.
   **Expect:** One row: *Reading lamp `<RUN>`*, `€29.00`, *Active*.
2. **UI-web** — Open the row.
   **Expect:** The detail page shows category *Uncategorised* and no *New* badge.

## 7. Cleanup — always runs

- **C-1** **API** — `DELETE /api/products/{id}` for every product id captured except `RUG_ID` (deleted by RB-08), newest first. **Expect:** `204` each.
- **C-2** **DB** — Remove the run's product rows. *Why not the API: its delete keeps the record.* Guard:
  ```bash
  psql "$DB_URL" -v ON_ERROR_STOP=1 -At -v run="$RUN" <<'SQL'
  SELECT count(*) FROM catalog.products WHERE sku LIKE :'run' || '-%';
  SQL
  ```
  **Expect:** as many rows as product ids the run captured. Then the same `WHERE` in a `DELETE`, expecting `DELETE` with that count.
- **C-3** **API** — `DELETE /api/categories/$CATEGORY_ID`. **Expect:** `204`.
- **C-4** Search for `<RUN>` on *Products*, in the app's *Shop*, and in `catalog.products`. **Expect:** nothing on any of the three.

## 8. Not run through a channel

| Case | Why | What it needs |
|---|---|---|
| — | Every case has a script | — |

## 9. Assumptions and open questions

- **OQ-1** The spec says a product is *New* "for 5 days". The code compares with `<` (`ProductMapper.cs:22`), so a product exactly 5 days old is not new. RB-12 and RB-13 follow the suite, which reads it the same way; the owner confirms.
- **A-1** The app has no test ids on its list rows (`apps/shopper/app/shop/[category].tsx:31`), so UI-app steps find a product by its name.
````
