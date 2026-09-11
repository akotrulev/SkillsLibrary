---
name: be-python-pattern-guide
description: Use when a Python backend / worker question is at the concept altitude — which idiom fits (Protocol vs ABC, frozen dataclass vs pydantic, Result union vs exception, generator vs list, context manager vs try/finally), and whether a pattern is earned. Triggers "should this be a Protocol or an ABC", "Result type or raise in Python", "is a repository justified here", "dataclass or pydantic model". Do NOT use to scaffold code (`pattern-writer`), review a diff (`code-review`), or for the media pipeline itself (`media-processing`).
---

# Python Design Patterns — Reference

Answers "which idiom, and is it earned" for Python 3.13 / 3.14 backend code and workers. Explains; never writes into the repo. Loads `backend/_shared/pattern-guide` for the language-agnostic pattern cards and layers the Python judgment on top.

## When to use

- Choosing between two Python idioms for the same need
- Deciding whether a GoF pattern is earned or is Java-in-Python
- Explaining why an existing structure is a smell (ABC with one subclass, class with only `__init__` and one method, module-level mutable state)

## When NOT to use

- Scaffolding → `backend/python/skills/pattern-writer`
- Reviewing → `backend/python/skills/code-review`
- Image / SVG / model-inference questions → `backend/python/skills/media-processing`
- Container hardening → `backend/python/skills/sandboxed-worker`

## The Python translation table

Most GoF patterns already exist as language features. Reach for the feature; the class-shaped version is a smell.

| Need | Python idiom | The Java-in-Python smell |
|---|---|---|
| Swap behaviour by kind | `match` on a tagged union of frozen dataclasses, or a dict of callables | `AbstractStrategy` + one subclass per case |
| Interface for injection | `typing.Protocol` (structural; the caller owns it) | `ABC` with `@abstractmethod` where nothing inherits behaviour |
| Wrap a call with logging/retry/timing | a decorator (`functools.wraps`) or a closure | `Decorator` class hierarchy |
| Build a complex value | keyword-only `__init__` on a frozen dataclass, `classmethod` constructors | `FooBuilder().with_x().with_y().build()` |
| Single instance | a module (modules are singletons) or one object built at the composition root | `Singleton` metaclass, `_instance` class attribute |
| Iterate lazily | generator / `itertools` | `Iterator` class with `__next__` bookkeeping |
| Acquire / release | `contextlib.contextmanager`, `ExitStack` | `try/finally` repeated at every call site |
| Domain failure the caller must handle | tagged-union return (`Ok[T] \| Err[E]`) | a custom exception per case the caller catches and inspects |
| Bug / invariant violation | raise (`ValueError`, `RuntimeError`, a domain exception) | a `Result` that nobody can act on |
| Validate untrusted input at a boundary | pydantic v2 model (`model_validate`) | hand-written `if not isinstance` chains |
| Carry validated data inside | frozen `dataclass(slots=True)` | pydantic everywhere, re-validating on every hop |
| Configuration | `pydantic-settings` read once at startup, passed down | `os.environ[...]` scattered through modules |
| Optional dependency wiring | pass callables / objects into a function or constructor | a service locator, a global registry, `importlib` magic |

## Decision rules

**Protocol vs ABC.** `Protocol` when the caller defines what it needs and any object with those methods will do — the normal case for injected collaborators (a store, a clock, a model session). `ABC` only when subclasses must share real behaviour from the base. An ABC with a single concrete subclass is an unearned abstraction; inline it.

**Frozen dataclass vs pydantic.** Pydantic at the boundary where bytes arrive (a job file, an HTTP body, an env block) — it validates and produces a typed value. Once inside, plain frozen dataclasses: they are cheaper, `slots=True` shrinks them, and re-validation on every internal hop is waste. A pydantic model that never sees untrusted input is the wrong tool.

**Result vs raise.** Return a tagged union when the failure is an expected business outcome the caller decides on: `Rejected(reason="polyglot")`, `Unsupported(format="tiff")`. Raise when continuing would be a bug: a corrupt internal state, a missing model file the container was supposed to bake in. Never both in one function. Python has no checked exceptions, so the tagged union is the only way the type checker makes the caller handle the case — `match` over it with no wildcard arm makes an unhandled variant a `mypy --strict` error.

**Generator vs list.** A generator when the sequence is consumed once and may be large (rows, tiles, frames). A list when it is small, reused, or must be indexed. Returning a generator from a public function is a contract: say it in the return type (`Iterator[T]`), never hide it.

**Class vs function.** A class earns its place when there is state that outlives one call and several methods share it (a loaded model session, a connection). A class with `__init__` and one public method is a function with a closure over its arguments; write the function. A `*Utils` / `*Helper` / `*Manager` class is a module.

**Repository.** Only when there are two real stores or a domain reason to hide the query. Over SQLAlchemy 2.x / an object store client the session or client *is* the abstraction.

**Async.** `asyncio` when the process is I/O-bound and concurrent (an HTTP adapter). A CPU-bound image or inference worker is synchronous and gets its parallelism from processes, not from `async def` — an `async` function that calls Pillow or onnxruntime directly blocks the loop and is a **major** review finding. Bridge with `asyncio.to_thread` or a `ProcessPoolExecutor`, never by pretending.

**Module-level state.** Constants and frozen values are fine. A mutable module-level cache, a lazily created global session, a `_registry: dict` that functions append to — all of these make tests order-dependent and are **major** findings. Build the object once at the composition root and pass it in.

## Pattern cards (Python specifics only)

**Tagged union with `match`**
- *Intent* — represent "one of N outcomes" so every consumer must handle every case.
- *Shape* — one frozen dataclass per variant, a `type X = A | B | C` alias (3.12+ `type` statement), `match` with no `case _`.
- *Earned when* — two or more consumers switch on the same kind, or the outcome set will grow.
- *Failure mode* — a `case _: pass` arm, which silently swallows the new variant the union was supposed to force you to handle.

**Protocol-injected collaborator**
- *Intent* — let a function depend on a capability, not a concrete class, so a test can pass a fake.
- *Shape* — a `Protocol` with the one or two methods actually used, declared next to the *consumer*; the real implementation never imports the protocol.
- *Earned when* — the collaborator does I/O, is slow, or is non-deterministic (time, randomness, model inference).
- *Failure mode* — a Protocol that mirrors the whole concrete class; a fake then has to implement twelve methods to satisfy a caller that used two.

**Composition root**
- *Intent* — one place that constructs the object graph; everything else receives its dependencies.
- *Shape* — `build_worker(settings) -> Worker` in `__main__.py` or `app.py`; nothing else calls constructors of collaborators.
- *Earned when* — always, once there are two injected collaborators. Before that, a function with keyword arguments is the root.
- *Failure mode* — a "container" library for six objects; a `get_session()` module function that lazily builds a global.

**Per-job subprocess with resource limits**
- *Intent* — isolate work that untrusted input can make pathological (decompression, tracing, inference) so one bad job cannot take the worker down.
- *Shape* — `multiprocessing` / `subprocess` child with `resource.setrlimit` (address space, CPU seconds) and a wall-clock timeout; the parent maps a killed child to a `Rejected` outcome.
- *Earned when* — the input is user-supplied bytes. That is the whole reason `sandboxed-worker` exists.
- *Failure mode* — a `signal.alarm` in the same process, which cannot interrupt C code inside Pillow or onnxruntime.

## Handoffs

- Concept settled, now write it → `backend/python/skills/pattern-writer`
- Concept settled, now check existing code against it → `backend/python/skills/code-review`
- Cross-stack pattern cards → `backend/_shared/pattern-guide`
