# Module boundaries — crate per module

A modular monolith that will be split later (the system plan skeleton's `Modules:` line) is a **Cargo workspace with one library crate per module** plus one binary crate that composes them:

```
Cargo.toml                 # [workspace] members, [workspace.dependencies], [workspace.lints]
crates/app/                # the binary: config, telemetry, router composition
crates/orders/             # lib: pub fn router() -> Router<AppState>, pub commands, pub events
crates/billing/            # lib
```

- **The compiler is the architecture test.** `billing` can reach `orders` only if `crates/billing/Cargo.toml` lists it, and then only its `pub` items. Keep internals `pub(crate)` and re-export the module's surface from `lib.rs`. No dependency-cruiser equivalent is needed.
- **One schema per module.** Each module crate owns a `migrations/` folder whose tables live in its own Postgres schema (`orders.orders`). It holds another module's id as a plain column, with no foreign key into that schema (`database-code`).
- Shared versions and lints are declared once in `[workspace.dependencies]` / `[workspace.lints]`, with `dep = { workspace = true }` in members.
- **A call between modules** is a plain function on the other crate's public surface, taking the pool or the state it needs. **An event** is a type exported by the publisher, delivered in-process through a `tokio::sync::broadcast` or an outbox. Add one only when a second consumer, or "must not fail the publisher", earns it.
