# Reading an OpenAPI contract into the basis

Walk the contract; do not read it as prose. Each keyword lands in one place, and schema constraints go to the data dictionary (§6), never to one validation row each.

| Schema / operation keyword | Lands in |
|---|---|
| `required` array | data dictionary `Required = yes` |
| `minimum` / `maximum` / `exclusiveMinimum` / `minLength` / `maxLength` / `minItems` / `maxItems` | data dictionary *Range* (note open vs closed) |
| `enum` / `pattern` / `format` | data dictionary *Format* |
| `default` / `nullable` / `readOnly` | data dictionary *Notes* |
| each `4xx` response + its schema | the *On violation* column of the data-dictionary field it rejects; a `4xx` that no field or rule explains is an Open question ("what triggers 409?") |
| `security` / scopes per operation | actors & roles; one V row per operation-scope pair — authorization is a rule |
| `x-`-extensions, `description` prose | rules (BR) only when they state a decision; otherwise ignored |

A constraint the schema states and the prose contradicts is a ⚠️ conflict row.

Beyond the schema, read each operation for what the business does with it: what a successful call changes (a rule, §3), what it costs or computes (a calculation, §3), and which goal it serves (a journey, §5). A contract with every field listed and no rule, figure or journey extracted is half read.
