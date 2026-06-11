---
name: qa-accessibility-testing-dotnet
description: Use when tests must scan for accessibility violations — axe-core inside Playwright flows (per-state WCAG scans) or Lighthouse CI (page-level scores with budgets). Triggers: "add a11y tests", "scan for WCAG violations", "fail CI on accessibility regressions", "set an accessibility budget". Pick the tool in the decision matrix, then read its reference file.
---

# QA — Accessibility Testing (.NET 8 / C#)

One registered skill, 2 tools — a project uses exactly one. Identify the project's tool
(dependencies, docker-compose, infra config; ask one question if ambiguous), then **read the matching
`references/<tool>.md` end-to-end before writing any code** — it carries the full model, patterns,
templates, anti-patterns, and hard rules for that tool. This file only routes and holds the rules
shared by every tool in the family.

## Tools in this family

| Read | Use when |
|------|----------|
| `references/axe-playwright.md` | axe-core scans injected into UI flows — per-state WCAG violation gating |
| `references/lighthouse-ci.md` | Lighthouse CI — page-level accessibility/performance scores enforced as budgets |

## Decision matrix — pick the tool

| Need | Use | Why |
|------|-----|-----|
| Rule-based DOM a11y assertions **inside** your functional Playwright run, gate on `Violations` | **`references/axe-playwright.md`** | Free, deterministic, no extra pass; scoped to components; fails fast in the same job |
| A full-page audit (a11y **+** performance + SEO + PWA + best-practices) with a numeric **score** threshold | Lighthouse CI | Separate Lighthouse pass; score-gate (e.g. a11y ≥ 0.9); broader but coarser, not assertion-level |
| Per-element WCAG conformance evidence (rule id + selector + helpUrl) for a specific component | **`references/axe-playwright.md`** | `Violations[].Nodes[]` names the exact failing selector + fix |
| One number to trend a11y over time across whole pages | Lighthouse CI | Score is a trend metric; axe is a pass/fail gate |

**Rule of thumb:** axe-playwright is your **gate** (fail the build on new violations, per component, in
the existing E2E run); Lighthouse CI is your **broad audit + score trend**. They are complementary —
many teams run both.

## Shared rules (every tool in this family)

- Scan per state, not per page — open menus, modals, and validation errors are where violations hide.
- Gate on new violations; triage pre-existing ones into an explicit baseline/allowlist.
- Scans ride on page-object-driven flows, never on hardcoded navigation.

## Cross-references

Each `references/<tool>.md` carries its own cross-references to sibling skills (DB verification,
test environments, CI, chaos). Route there after picking the tool.
