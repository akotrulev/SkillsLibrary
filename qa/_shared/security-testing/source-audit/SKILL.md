---
name: source-audit
description: Use for an agent-driven, source-first security audit of a codebase — coverage-ledger hunters, adversarial verifiers, schema-validated findings; Cloudflare's vendored workflow plus house overrides. Triggers "security audit this codebase", "find vulnerabilities in ./src", "white-box security review". Do NOT use for a CI scanner gate (`code-scan`), to prove a finding on a running env (`exploit-validation`), or to audit governance artifacts (`standards-audit`).
---

# Security Testing — Source Audit

A scanner gate (`code-scan`) matches known patterns on every PR. This skill is the other half: a periodic,
model-driven hunt through the source for **trust-boundary failures a rule cannot express** — authorization
gaps across sibling paths, tenant leaks through derived copies, chained logic flaws — each one traced in source,
attacked by a verifier that did not find it, and recorded only with the boundary it crosses.

The workflow is **Cloudflare's `security-audit` skill, vendored untouched** at `qa/_shared/vendor/security-audit/`
(provenance in [`qa/_shared/ATTRIBUTIONS.md`](../../ATTRIBUTIONS.md)). **Upstream is authoritative for the
procedure**: the operating modes, the execution-safety rules, write isolation, the coverage ledger, run profiles
and budget, the six phases, the evidence bar, the severity anchors and both validators. This file states only
where the library departs from it. Never paraphrase upstream from memory — read it.

## Load order

Resolve against `${CLAUDE_PLUGIN_ROOT}/qa/_shared/vendor/security-audit/` from an installed plugin, or
`qa/_shared/vendor/security-audit/` in this repo.

1. Read upstream `SKILL.md` end to end. It decides guidance mode versus full audit mode.
2. In full audit mode, read each phase file when its phase starts (`RECONNAISSANCE.md`, `HUNTING.md`,
   `ATTACK-CLASSES.md`, `VALIDATION-AND-REPORTING.md`) and only the domain companions reconnaissance selects.
3. Apply the overrides below. Where one is silent, upstream holds.

## Overrides

| Upstream | Here | Why |
|---|---|---|
| The parent is whichever agent loaded the skill | **Full audit mode runs only in the main session** (`/qa-<stack>:source-audit`). A subagent — `qa-security` included — cannot spawn agents, so there it uses guidance mode and hands a full audit back to the main session. | Claude Code subagents have no `Agent` tool. |
| Task tool; `research` and `general` agent roles | The `Agent` tool; **both roles run as `general-purpose`**, one isolated agent per assignment, independent assignments sent in one message so they run in parallel. A `research` agent's read-only boundary is carried by its prompt, as upstream already writes it. | `Explore` reads excerpts and locates code; upstream verifiers and critics must read at depth. |
| Output directory defaults to `~/security-audit-skill/<repo>/run-<N>` | Default `<repo-root>/.security-audit/run-<N>/`. Before writing, prove it is ignored with `git check-ignore -q .security-audit/`; if it is not, ask the user to add `.security-audit/` to `.gitignore` or to name an external path. Never write the run into `docs/audits/`, and never commit it. | Keeps the run in the project (house rule) while meeting upstream's ignored-directory condition. The reports describe unpatched vulnerabilities, so they are not committed. |
| Budget proposed "for a large target" | **Always** propose a `budget` and a profile before reconnaissance, with the estimate upstream's cost section defines; start on `quick` for a first run unless the user asks for more. | A `standard` run spawns an agent per ledger unit plus critics and one or two verifiers per candidate. |
| An OS-enforced sandbox | A container counts only when **every** upstream control holds, disk limit included: no network (`--network none`), target and toolchain mounted read-only, one writable scratch bind, an `env -i` allowlisted environment, CPU / memory / pids / file-size limits and a wall-clock `timeout`, with an image already present locally. If one control cannot be enforced, upstream's rule stands: nothing executes, and the lead stays `needs_validation`. | macOS gives no such sandbox by default; a partial sandbox is not one. |
| "Phase 1–6" | Read as the agent's **steps**. A plan that schedules an audit names it one task. | Library vocabulary. |

**Kept from upstream on purpose:** the `confirmed` / `needs_validation` / `rejected` verdicts and the
critical → informational severity anchors. The library's Data / Code / Logical-conflict audit split and its
blocker → nit review scale do not apply — a security verdict is a different axis, and the validators enforce
upstream's shape.

## Authorization

Full audit mode reads source and runs target code only in the sandbox, against dummy fixtures, so it needs no
`#volatile` authorization line. The moment a lead needs a running deployment, it leaves this skill — upstream
already forbids live probing.

## Handoffs

- A `needs_validation` record whose blocker is runtime or deployment behaviour → `exploit-validation` on an
  authorized throwaway env, under `qa-security`'s authorization rule.
- A `confirmed` access-control finding → a regression row in `<stack>:permission-testing`.
- The fix → the owning `be-*` / `fe-*` / `mobile-*` agent, from the record's smallest-fix and regression-test
  fields. This skill never edits target source.
- A pattern worth catching on every PR → a custom rule in `code-scan`.

## Refreshing the vendored copy

Copy upstream `skills/security-audit/*` and `LICENSE` over `qa/_shared/vendor/security-audit/` at a new pinned
commit, run `node --test qa/_shared/vendor/security-audit/*.test.cjs`, re-check each override row against the
new upstream text, and update the commit and date in `qa/_shared/ATTRIBUTIONS.md`.
