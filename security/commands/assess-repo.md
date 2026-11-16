---
description: Run the free/open-source Metasploit Framework assessment workflow against a repo — three parallel readers derive the deploy profile (ports/services · dependency-CVE leads · app/auth fingerprint), one agent synthesizes the Framework setup + per-surface test plan with ready-to-paste operator commands, and a completeness critic checks it. Static planning only: it reads source, touches no live target, runs no exploit, and stops at the authorization gate. Live acts are operator-run via /penetration-testing:pentest.
argument-hint: [the repo path to assess, and optionally the deployed lab target hint]
---

Run the **free Metasploit Framework** repo-assessment workflow and present the engagement package.

1. Invoke the workflow with the `Workflow` tool, pointing at the script and passing the repo:
   `Workflow({ scriptPath: "${CLAUDE_PLUGIN_ROOT}/security/workflows/metasploit-framework-assessment.mjs", args: { repo: "<repo path from $ARGUMENTS>", targetHint: "<lab target hint if given>" } })`
   (inside the SkillsLibrary repo itself, use `security/workflows/metasploit-framework-assessment.mjs`).
2. When it returns, present the engagement package to the user: the **deploy profile**, the **setup** (Docker image pinned by digest · engagement-named `msfdb` workspace · the Framework MCP server read-only), the **test plan** (each test's module, the single proven outcome, and the ready-to-paste **operator command**), the **scope-file skeleton**, and the **out-of-reach** surfaces plus the critic's findings.

**Planning only — this crosses no gate.** The workflow reads source statically and executes nothing against a live target. Every live act is **operator-run**: the user commits the scope file (`docs/security/engagement-<NNN>.md`), re-confirms authorization, then runs the kill chain via `/penetration-testing:pentest` (or `/penetration-testing:provision` to stand up the toolchain first). Where a live step is gated or the assistant cannot run it, follow the **operator-handoff protocol** in `security/metasploit-setup/SKILL.md`: state the exact command, the user runs it, pastes the result back, and the run continues.

**The paid Metasploit Pro lane is a separate workflow**, planned in `docs/plans/` for later — this command is the Framework lane only.

**Repo / target (required):**

$ARGUMENTS

If no repo path was given, ask for it before running anything.
