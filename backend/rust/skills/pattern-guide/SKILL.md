---
name: patterns
description: Use when explaining a design pattern in Rust (enum vs trait dispatch, newtype, typestate, builder). Triggers "enum or trait object here". Not for scaffolding (patterns-apply).
---

# Rust Design Patterns — Reference

Conceptual reference for patterns as Rust expresses them. Most GoF patterns collapse into a language feature here: Strategy is an `enum` + `match` or a generic, Decorator is a wrapper type or a `tower::Layer`, Factory is a constructor function, Null Object is `Option`, Template Method is a trait with default methods, Command is an enum, Observer is a channel. **Reach for the language feature first; a trait hierarchy is the last resort, not the default.**

Load `backend/_shared/pattern-guide` for the language-agnostic card (intent, when not to use, failure mode); this skill holds the Rust "how".

## Version policy

Detect the toolchain before answering: `rust-toolchain.toml` (`channel`), `Cargo.toml` `edition` and `rust-version` (the MSRV), the CI image. **Edition 2024 primary, 2021 supported.** Never recommend an API newer than the declared `rust-version`, and never flag a 2021-edition crate for lacking a 2024-only form. The forms below that need a minimum toolchain say so.

## When to use

- "What is pattern X in Rust", "is this idiomatic"
- Choosing between an `enum`, a generic `T: Trait`, and a `Box<dyn Trait>` / `Arc<dyn Trait>`
- Deciding how a function should take and return data (owned, borrowed, `Cow`, `impl Trait`)
- Choosing an error strategy for a crate
- Sharing state between tasks or threads

## When NOT to use

- Scaffolding code into a repo → `pattern-writer`
- Reviewing a diff → `code-review`
- Tokio rules, cancellation, blocking, locks across `.await` → `async-concurrency`
- Making it faster → `performance`

---

## Ownership in signatures — the first design decision

| The function… | Takes | Why |
|---|---|---|
| Only reads the value | `&T`, `&str`, `&[T]`, `&Path` | Accept the most general borrowed form: `&str` not `&String`, `&[T]` not `&Vec<T>` (clippy `ptr_arg`) |
| Stores it or consumes it | `T` (owned), or `impl Into<T>` on a public constructor | The caller decides whether to clone; the callee never clones a borrowed argument "to be safe" |
| Sometimes needs to modify, usually not | `Cow<'_, str>` | Allocates only on the modifying path |
| Mutates the caller's value in place | `&mut T` | Clearer than take-and-return |
| Is generic over a readable source | `impl AsRef<Path>`, `impl Read` | Public APIs only; internal code takes the concrete type |

Return owned values (`String`, `Vec<T>`) unless returning a view into `self` (`&str`, `&[T]`, `impl Iterator<Item = &T> + '_`). **A lifetime parameter on a struct is a cost every user of the struct pays** — use one for short-lived views (parsers, iterators, borrowed config), not for long-lived domain types, which own their data.

**`clone()` is not a borrow-checker fix by default.** Cloning a small `Copy`-able id or an `Arc` is free and fine; cloning a `Vec` or `String` to silence an error usually means the ownership design is wrong — restructure (split the borrow, scope the borrow tighter, take ownership earlier) before reaching for it.

## Strategy / dispatch — enum, generic, or trait object

```rust
pub enum Pricing {
    Standard,
    B2b { contract_id: ContractId },
    Promo { code: PromoCode },
}

impl Pricing {
    pub fn price(&self, cart: &Cart) -> Money {
        match self {
            Pricing::Standard => standard_price(cart),
            Pricing::B2b { contract_id } => b2b_price(cart, contract_id),
            Pricing::Promo { code } => promo_price(cart, code),
        }
    }
}
```

| Shape | Use when | Cost |
|---|---|---|
| **`enum` + `match`** (default) | The variants are known to this crate | Exhaustiveness checked by the compiler; no allocation; adding a variant breaks every `match` — which is the point |
| **Generic `T: Trait`** | The caller picks the implementation at compile time; hot path | Monomorphized per type (code size, compile time); zero dispatch cost |
| **`Box<dyn Trait>` / `Arc<dyn Trait>`** | Implementations are open (plugins, test fakes injected into app state) or a heterogeneous collection | One allocation + vtable call; the trait must be dyn-compatible |

Never use `_ =>` on an enum this crate owns — it turns "a new variant is a compile error" into "a new variant silently takes the default". Mark a **public** enum that will grow `#[non_exhaustive]`, so downstream crates must keep a wildcard arm and adding a variant is not a breaking change.

**`async fn` in traits** is stable (1.75) and fine for generics, but a trait with `async fn` is **not dyn-compatible**. When the trait must be a trait object (`Arc<dyn OrderRepository>` in `AppState`), either keep the `#[async_trait]` attribute or hand-write `fn save(&self, o: Order) -> Pin<Box<dyn Future<Output = Result<()>> + Send + '_>>`. Prefer a concrete type over both when there is only one implementation.

## Newtype — make invalid states unrepresentable

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[serde(transparent)]
pub struct OrderId(uuid::Uuid);

pub struct Email(String);

impl TryFrom<String> for Email {
    type Error = DomainError;

    fn try_from(raw: String) -> Result<Self, Self::Error> {
        if raw.contains('@') && raw.len() <= 254 {
            Ok(Self(raw))
        } else {
            Err(DomainError::InvalidEmail)
        }
    }
}
```

- Ids that cross a boundary get a newtype; `fn ship(order: OrderId, customer: CustomerId)` cannot be called with the arguments swapped.
- **Parse, don't validate:** the only constructor is the fallible one (`TryFrom` / `parse`), so holding an `Email` proves it was checked. No public tuple field, no `new` that skips the check.
- Money is an integer of minor units in a newtype (`Money { minor: i64, currency: Currency }`), never `f64`.

## Typestate — encode a lifecycle in the type

```rust
pub struct Draft;
pub struct Submitted;

pub struct Invoice<State> {
    lines: Vec<Line>,
    state: std::marker::PhantomData<State>,
}

impl Invoice<Draft> {
    pub fn submit(self) -> Invoice<Submitted> {
        Invoice { lines: self.lines, state: std::marker::PhantomData }
    }
}

impl Invoice<Submitted> {
    pub fn pay(&self) -> Receipt {
        Receipt::for_lines(&self.lines)
    }
}
```

Earned when calling an operation in the wrong state is a real bug class and the states are few and compile-time known (builders, connection handshakes, protocol steps). **Not** for a status stored in a database row — that state is only known at run time; use an `enum Status` and a `match` that returns an error for the refused transition.

## Builder

A builder is earned at **4+ optional fields** or when construction can fail on a combination of fields. Below that, a constructor function or a struct literal with `..Default::default()` is simpler.

```rust
let client = HttpClient::builder()
    .base_url(url)
    .timeout(Duration::from_secs(5))
    .build()?;
```

Builder methods take `self` by value and return `Self` (chainable, no `&mut` gymnastics). `build()` returns `Result` when validation can fail. Don't derive a builder macro for a struct with three fields.

## RAII and `Drop` guards

Cleanup belongs in `Drop`, not in a `finally` the caller must remember: lock guards, temp files (`tempfile::TempDir`), spans (`span.enter()` guard — never held across `.await`, see `async-concurrency`), transactions (`sqlx::Transaction` rolls back on drop unless committed).

- `Drop` cannot be `async` and cannot return an error. Resources needing async or fallible cleanup expose an explicit `close(self) -> Result<()>`, and `Drop` is the best-effort fallback.
- `std::process::exit` and `panic = "abort"` skip destructors — never rely on `Drop` to flush telemetry or commit state on those paths.
- Drop order: locals drop in reverse declaration order; struct fields drop in declaration order. A guard bound to `_` drops **immediately** (`let _ = mutex.lock();` holds nothing); bind it to `_guard`.

## Errors — `Result`, `thiserror`, `anyhow`, `panic!`

| Situation | Use |
|---|---|
| A library or a domain module whose caller branches on the failure | A `thiserror` enum: one variant per case the caller handles, `#[from]` for wrapped sources |
| A binary's `main`, a CLI command, a one-off task | `anyhow::Result` with `.context("what we were doing")` |
| A broken invariant — a bug, not an input | `panic!` / `unreachable!` / `expect("why this cannot fail")` |
| Expected absence | `Option<T>`, not an error variant |

```rust
#[derive(Debug, thiserror::Error)]
pub enum PlaceOrderError {
    #[error("cart is empty")]
    EmptyCart,
    #[error("sku {0} is out of stock")]
    OutOfStock(Sku),
    #[error(transparent)]
    Database(#[from] sqlx::Error),
}
```

- `?` converts through `From`; a `match` on the error enum is the caller's exhaustive handling.
- **Never `Box<dyn Error>` or `anyhow::Error` in a library's public API** — the caller cannot match on it.
- Error types are `Send + Sync + 'static` so they cross task boundaries.
- `unwrap()` in production code is a finding; `expect("…")` is permitted only where the message states the invariant that makes failure impossible. Tests may unwrap freely.
- Error `Display` messages are lowercase with no trailing period (std convention), and never contain secrets.

## Shared state — ownership of mutation

| Need | Shape |
|---|---|
| Read-only config / clients shared by handlers | `Arc<T>` (or a `Clone` struct of `Arc`s) built once in `main` |
| Small shared mutable value, short critical sections | `Arc<std::sync::Mutex<T>>` / `RwLock` — **never held across `.await`** |
| State that one owner mutates and others query | An actor: a task owning the state, an `mpsc` channel in, `oneshot` replies out |
| A counter / flag | `AtomicU64` / `AtomicBool` with the weakest correct `Ordering` (usually `Relaxed` for a counter) |
| Lazily-initialised global constant | `std::sync::LazyLock` (1.80) — for immutable data only; never a mutable global behind a `Mutex` |
| Single-threaded shared mutation | `Rc<RefCell<T>>` — a smell in application code; restructure ownership first |

`RefCell` and `Mutex` move borrow errors from compile time to run time (a panic or a deadlock). Re-entrant locking (calling a method that locks the same `Mutex` while holding it) deadlocks; `RefCell` double `borrow_mut` panics.

## Conversions

Implement `From<A> for B` (never `Into` directly); fallible conversions are `TryFrom`; parsing from text is `FromStr`. Naming per the API Guidelines: `as_*` is a free borrow-to-borrow view, `to_*` is an expensive conversion that allocates, `into_*` consumes `self`. Getters are named after the field (`fn name(&self)`), never `get_name`.

## Iterators over index loops

```rust
let total: Money = lines.iter().filter(|l| !l.is_free()).map(Line::subtotal).sum();
```

Iterator chains are idiomatic, bounds-check-free, and lazy. Use a `for` loop when the body has side effects, early `return`/`?`, or more than one accumulator — a `fold` with a tuple accumulator is harder to read than the loop it replaced. `collect::<Result<Vec<_>, _>>()` short-circuits on the first error.

## Traits as ports — only when earned

A trait in front of a collaborator is earned by a **second implementation** or a **test that needs a fake for an outbound I/O seam** (clock, id generator, payment gateway, mailer). It is not earned by "we might switch databases". A `struct PgOrderStore { pool: PgPool }` with inherent methods is the default; extract a trait when the second need arrives.

## Modules and visibility

- Private by default; `pub(crate)` for crate-internal sharing; `pub` only for the crate's real API.
- One module per concept, not per layer (`orders/` holding its handler, domain and queries beats `handlers/`, `services/`, `repositories/`).
- `mod.rs` and `name.rs` + `name/` are both valid — match the repo; edition-2018+ code mostly uses `name.rs`.
- Glob imports (`use foo::*`) only for preludes and `use super::*` in test modules.

## Language pitfalls — the short list

| Pitfall | Consequence | Instead |
|---|---|---|
| Integer arithmetic on input-derived values | Panics in debug, **silently wraps in release** | `checked_*` / `saturating_*`, or `overflow-checks = true` in `[profile.release]` for money paths |
| `x as u32` on a wider or signed value | Silent truncation / sign change | `u32::try_from(x)?` |
| `let _ = guard_returning_call();` | The guard drops immediately | `let _guard = …;` |
| `#[derive(Debug)]` on a struct holding a secret | The secret lands in logs and panics | `secrecy::SecretString`, or a manual `Debug` that redacts |
| `HashMap` iteration order relied on | Non-deterministic output, flaky tests | `BTreeMap`, or sort before emitting |
| `impl Trait` in argument position on a public fn | Caller cannot turbofish the type | A named generic when callers need it |
| `&String`, `&Vec<T>`, `&Box<T>` parameters | Needless indirection, narrower API | `&str`, `&[T]`, `&T` |
| `std::env::set_var` | `unsafe` in edition 2024 — racy with other threads | Read config once at startup into a struct |
| Over-annotated lifetimes | Noise, harder refactors | Let elision work; name a lifetime only when the compiler asks |

## `unsafe`

Application and service code contains **no `unsafe`**. Where a crate genuinely needs it (FFI, a measured hot path), every `unsafe` block carries a `// SAFETY:` comment stating the invariant that makes it sound — the one comment form the house comment rule permits inside a body, because clippy's `undocumented_unsafe_blocks` lint requires it — the block is as small as possible, it is wrapped in a safe function whose signature upholds the invariant, and it is tested under Miri. Each `unsafe fn` documents its contract in a `# Safety` doc section.

## Handoffs

- Scaffolding any of the above → `pattern-writer`
- Async and concurrency rules → `async-concurrency`
- Measuring and fixing slowness → `performance`
- Reviewing for misuse → `code-review`
- Language-agnostic pattern cards → `backend/_shared/pattern-guide`
