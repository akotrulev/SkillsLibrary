---
description: Assess a repo end to end with the free/open-source Metasploit Framework. First a static pass profiles the repo (services/ports · dependency-CVE leads · app/auth fingerprint) and synthesizes a per-surface test plan. Then, against the repo's OWN deployment — which the command starts if it is not already running — it runs the testing live: non-destructive enumeration and default-credential checks directly, with any destructive/exploit/payload step handed off to the operator. Owned lab or isolated UAT targets only; leaves the environment as it found it.
argument-hint: [the repo path to assess; optionally how its deployment is reached if not localhost]
disable-model-invocation: true
---

Assess a repo with the **free Metasploit Framework** end to end: profile it, **start its deployment if it isn't already running**, then **run the testing live** against that running stack.

## Target and authorization

This command runs **live modules against a real deployment**. Run it only against a target the user owns and is authorized to test — their **local lab or an isolated UAT**, never a shared or production host. Invoking it against your own repo's deployment *is* the authorization for the non-destructive battery (version/directory enumeration, single-pair default-credential checks). A genuinely destructive step — anything flagged `availabilityRisk`, or that delivers a payload/shell — is still gated: follow the **operator-handoff protocol** in `security/metasploit-setup/SKILL.md` — state the exact command, the user runs it, pastes the result back, and the run continues.

## Procedure

1. **Resolve the repo** from `$ARGUMENTS`. If none was given, ask for it before doing anything.

2. **Profile + plan (static — touches no host).** Invoke the workflow to read the source and produce the deploy profile and per-surface test plan:
   `Workflow({ scriptPath: "${CLAUDE_PLUGIN_ROOT}/security/workflows/metasploit-framework-assessment.mjs", args: { repo: "<repo path>", targetHint: "<how its deployment is reached, if known>" } })`
   (inside the SkillsLibrary repo itself, use `security/workflows/metasploit-framework-assessment.mjs`.) It maps services/ports, CVE leads, the auth surface, the test plan, the scope-file skeleton, and the out-of-reach surfaces.

3. **Start the project if it is not already running.**
   - **First read the repo to learn how *this* repo starts — do not assume.** Read the README (and any CONTRIBUTING / `docs/` / "getting started" guide), then the `Makefile`, `package.json` scripts, `docker-compose*.yml`, `.env.example` and any deploy workflow. Derive the repo's actual start procedure **and its prerequisites** (env file to copy, build step, DB migrations, seed) from what they say, not from a fixed default. The static profile from step 2, and the repo's own `run`/`dev:run` skill if it has one, feed this.
   - **Check the run state before starting**, so an already-up stack is reused rather than double-started, and **record whether this command started it** (that decides teardown in step 6). For a compose repo that check is `docker compose ps`.
   - **Run the discovered start procedure.** It is often `docker compose up -d --wait`, but only when that is in fact how the README/repo says to start it. If the repo gives no determinable way to start, ask rather than guess.
   - Confirm the profile's services are actually listening, and note how they are reached. Compose typically binds to `127.0.0.1`; from a Metasploit container, reach the host via `host.docker.internal` (macOS/Windows) or `--network host` (Linux).

4. **Run the testing live** against the running stack, working the plan's tests in order:
   - Run the **non-destructive** modules directly (`http_version`, `dir_scanner`, single-pair `*_login` default-credential checks) and record each module's real result.
   - For any test flagged `availabilityRisk` or that delivers a payload/shell, **do not run it** — hand it to the operator per the handoff protocol and continue on their pasted result. Verify a module exists (`search`) before asserting it.
   - Keep loot out of the chat: report *that* a secret or working default credential exists, never its value.

5. **Report the real outcome:** each test's actual module result next to the plan, the deploy profile, the out-of-reach surfaces, and the critic's findings. Call out anything that proved live — a default credential that worked, a service exposed beyond loopback.

6. **Leave the environment as found.** If this command started the stack in step 3, stop it (`docker compose down`, or the matching stop command) once testing is done; if it was already running, leave it up. Say which.

**The paid Metasploit Pro lane is a separate workflow**, planned in `docs/plans/` for later — this command is the Framework lane only.

**Repo / target:**

$ARGUMENTS
