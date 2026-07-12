# Attributions

Imported skills from third-party repos. Each upstream directory was copied verbatim into the path listed below. Original authors retain copyright.

## anthropics/skills — https://github.com/anthropics/skills

| Upstream skill         | Local path                           |
|------------------------|--------------------------------------|
| webapp-testing         | `qa/_shared/webapp-testing/`         |
| docx                   | `extras/docx/`                       |
| pdf                    | `extras/pdf/`                        |
| pptx                   | `extras/pptx/`                       |
| xlsx                   | `extras/xlsx/`                       |
| doc-coauthoring        | `extras/doc-coauthoring/`            |
| brand-guidelines       | `design/brand-guidelines/`           |
| canvas-design          | `design/canvas-design/`              |
| frontend-design        | `design/frontend-design/`            |
| theme-factory          | `design/theme-factory/`              |
| algorithmic-art        | `extras/algorithmic-art/`            |
| internal-comms         | `communication/internal-comms/`      |
| slack-gif-creator      | `communication/slack-gif-creator/`   |
| claude-api             | `ai-development/claude-api/`         |
| mcp-builder            | `ai-development/mcp-builder/`        |
| skill-creator          | `meta/skill-creator/`                |

## vercel-labs/agent-skills — https://github.com/vercel-labs/agent-skills

| Upstream skill              | Local path                                       |
|-----------------------------|--------------------------------------------------|
| react-best-practices        | `design-patterns/react/reference/`               |
| react-view-transitions      | `design-patterns/react/view-transitions/`        |
| composition-patterns        | `design-patterns/react/composition-patterns/`    |
| react-native-skills         | `design-patterns/react-native/`                  |
| deploy-to-vercel            | `extras/vercel-deployment/deploy/`               |
| vercel-cli-with-tokens      | `extras/vercel-deployment/cli-tokens/`           |
| vercel-optimize             | `extras/vercel-deployment/optimize/`             |
| web-design-guidelines       | `design/web-design-guidelines/`                  |

## obra/superpowers — https://github.com/obra/superpowers

| Upstream skill                  | Local path                                              |
|---------------------------------|---------------------------------------------------------|
| test-driven-development         | `engineering-practices/test-driven-development/`        |
| systematic-debugging            | `engineering-practices/systematic-debugging/`           |
| brainstorming                   | `engineering-practices/brainstorming/`                  |
| writing-plans                   | `engineering-practices/writing-plans/`                  |
| executing-plans                 | `engineering-practices/executing-plans/`                |
| requesting-code-review          | `engineering-practices/requesting-code-review/`         |
| receiving-code-review           | `engineering-practices/receiving-code-review/`          |
| verification-before-completion  | `engineering-practices/verification-before-completion/` |
| using-git-worktrees             | `engineering-practices/using-git-worktrees/`            |
| finishing-a-development-branch  | `engineering-practices/finishing-a-development-branch/` |
| dispatching-parallel-agents     | `engineering-practices/dispatching-parallel-agents/`    |
| subagent-driven-development     | `engineering-practices/subagent-driven-development/`    |
| writing-skills                  | `meta/writing-skills/`                                  |

**Modified imports (2026-07-11, engineering-practices adaptation):** 10 developer-workflow skills are no longer verbatim. All were adapted for this library: `name:` renamed to the `ep-*` prefix (e.g. `ep-brainstorming`) with repo-style trigger/anti-trigger `description`; all `superpowers:*` cross-references rewritten to plugin-local `ep-*` names and the `elements-of-style:*` reference dropped (self-containment rule — the set has zero external-plugin dependencies); superpowers file paths (`docs/superpowers/specs|plans/`, `~/.config/superpowers/worktrees/`) replaced with `docs/specs/`, `docs/plans/`, and `.worktrees/`; upstream persona/memoir language normalized to impersonal house style; `systematic-debugging`'s upstream dev-fixtures deleted (`CREATION-LOG.md`, `test-academic.md`, `test-pressure-{1,2,3}.md`); the `brainstorming` visual companion demoted to on-explicit-request.

- The **first 8** — `test-driven-development`, `systematic-debugging`, `brainstorming`, `writing-plans`, `executing-plans`, `verification-before-completion`, `using-git-worktrees`, `finishing-a-development-branch`.
- The **2 agent-dispatch skills** (`subagent-driven-development`, `dispatching-parallel-agents`) were additionally **reshaped from speed-first to cost-first**: a Conservative agent-spawning policy (cost before speed; inline is the default; a hard gate — more than 2 agents needs the user's permission first) inverts their upstream "fresh subagent per task" / "3+ failures → one agent each" defaults. `subagent-driven-development`'s dangling `requesting-code-review` template reference was replaced with an inline review rubric pointing at CLAUDE.md's severity-table format.

The remaining 2 obra/superpowers skills in `engineering-practices/` (`requesting-code-review`, `receiving-code-review`) are still verbatim and out of scope pending a later adaptation session. Original authors retain copyright.

## Authored locally

| Skill                                       | Path                                       |
|---------------------------------------------|--------------------------------------------|
| communication-business-analysis             | `communication/business-analysis/`         |
| communication-user-story-writer             | `communication/user-story-writer/`         |
| communication-stakeholder-updates           | `communication/stakeholder-updates/`       |
| design-brand-intake                          | `design/brand-intake/`                     |
| design-iconography                           | `design/iconography/`                      |

## Refreshed from installed plugins

| Local skill                | Refreshed from                                                                 | Date       | Notes |
|----------------------------|--------------------------------------------------------------------------------|------------|-------|
| `design/frontend-design/`  | `claude-plugins-official/frontend-design` (installed plugin `frontend-design/skills/frontend-design`) | 2026-07-11 | Session F (frontend design-craft). The vendored copy was a superseded 41-line version of the anthropics/skills original; refreshed against the newer installed-plugin content (three-AI-look calibration, signature-element, hero-as-thesis, brainstorm→critique→build→critique two-pass token system, full "writing in design" section, subject-grounding) and folded in a Composition & atmosphere section (design gap #7). Repo frontmatter conventions preserved (repo-style trigger/anti-trigger `description`, ≤1024 chars; upstream `license:` line not carried over — original authors retain copyright per the tables above). |

## Notes

- Imported skill `name:` fields in frontmatter were left unchanged — they keep their upstream identifiers (e.g., `vercel-react-best-practices`, `test-driven-development`). If you adopt the project's `<domain>-<skill>` convention, rename in a follow-up pass.
- If any upstream skill conflicts with the global rules in `CLAUDE.md`, the global rules win — call out the conflict in usage.
- `design/brand-intake` (locally authored, Session DT3) borrows the *structure* of Anthropic's [`brand-guidelines`](https://github.com/anthropics/skills/tree/main/skills/brand-guidelines) skill (color/typography/voice encoding) and uses that skill's Anthropic-brand defaults — dark `#141413`, light `#faf9f5`, grays `#b0aea5`/`#e8e6dc`, accents `#d97757`/`#6a9bcc`/`#788c5d`, Poppins headings + Lora body — as its worked "example brand" fixture. Original brand values © Anthropic. (The `design/brand-guidelines/` row above is a not-yet-vendored import target; brand-intake is the library's own brownfield-intake skill, not a copy of it.)
