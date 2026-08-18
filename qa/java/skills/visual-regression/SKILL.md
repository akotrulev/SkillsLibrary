---
name: qa-visual-regression-java
description: Use when a Java 21 / TestNG test suite must catch unintended visual changes — Playwright's built-in pixel snapshots, Percy's hosted review, or Applitools Eyes visual-AI. Triggers "add visual regression tests", "screenshot diff this page", "the layout broke and no functional test caught it". Do NOT use for structural breakpoint/viewport assertions (use `qa-responsive-testing-java`), or for accessibility scans (use `qa-accessibility-testing-java`).
---

# QA — Visual Regression (Java 21)

One registered skill, 3 tools — a project uses exactly one. Identify the project's tool
(dependencies, docker-compose, infra config; ask one question if ambiguous), then **read the matching
`references/<tool>.md` end-to-end before writing any code** — it carries the full model, patterns,
templates, anti-patterns, and hard rules for that tool. This file only routes and holds the rules
shared by every tool in the family.

## Tools in this family

| Read | Use when |
|------|----------|
| `references/playwright-snapshots.md` | Built-in pixel snapshots — free, baselines live in the repo, start here |
| `references/percy.md` | Hosted pixel-diff with a team review/approval workflow and cross-browser rendering |
| `references/applitools.md` | Visual-AI (Eyes) — layout-aware matching, Ultrafast Grid render matrix, fewest false positives |

## Decision matrix — pick the tool

| Need | Use | Why |
|------|-----|-----|
| Free, baselines in your repo, you own diffing + the CI-container discipline | `references/playwright-snapshots.md` | No SaaS, no per-snapshot cost, full control |
| Hosted baselines + human review UI + server-side **pixel** diff | `references/percy.md` | Kills the platform-rendering problem; team review workflow |
| **Visual-AI** diffing + **match levels** for dynamic content + a real cross-browser/device grid | **`references/applitools.md`** | AI tolerance + Layout-level matching + Ultrafast Grid; most expensive |

**Graduation path:** start **free** with built-in snapshots; move to **Percy** when in-repo baselines
and the platform-rendering discipline become a bottleneck and you want a review workflow; move to
**Applitools** when anti-aliasing noise across many browsers makes even Percy's pixel diff too chatty,
or you need **Layout-level** matching to baseline pages whose *content* changes but whose *structure*
must not.

## Shared rules (every tool in this family)

- Stabilize before snapshotting: freeze animations, clocks, and dynamic data.
- Navigate to the state via page objects — the snapshot is the assertion, not the navigation.
- Baseline updates are reviewed diffs; never blind-regenerate baselines in CI.

## Cross-references

Each `references/<tool>.md` carries its own cross-references to sibling skills (DB verification,
test environments, CI, chaos). Route there after picking the tool.
