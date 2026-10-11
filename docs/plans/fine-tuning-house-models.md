# Training a house model for SkillsLibrary — the single-adapter plan

**Date:** 2026-08-18
**Status:** research note. Nothing built, nothing decided beyond the shape.
**Decision taken:** **one house adapter, not a fleet.** A single LoRA taught this library's shared conventions, applied under whichever agent prompt is loaded — rather than one adapter per stack or per agent. Rationale in §1; the per-agent fleet is explicitly deferred (§8).
**Scope:** fine-tuning an open-weight model to run this library's skills and agents. Adjacent to but separate from model *portability* (running the library as-is on non-Anthropic models) — that is its own plan, and shares the Phase-0 harness.

---

## 0. The short answer

Yes, this is possible. Three corrections to the original framing shape everything below:

1. **The unit is an adapter, not a model.** You would never train 49 models. A LoRA is a small low-rank delta over a frozen base — and the base is the entire cost.
2. **One adapter beats forty-nine.** What the agents in this library disagree about is *domain*; what they agree about is *discipline* — the severity table, the evidence grammar, the phase structure, the artifact conventions. Discipline is the trainable part, it is shared, and it is where small models actually fail. Training it once hits every agent.
3. **Fine-tuning buys format adherence, not reasoning.** So the house adapter raises the floor everywhere; it does not raise the ceiling on `be-planner` or `code-auditor`, which stay on frontier models permanently (§6).

Recommendation up front: **build the eval harness (Phase 0) before anything else.** It is useful with or without fine-tuning, and nothing downstream is honest without it.

---

## 1. Why one adapter

### What a LoRA is

LoRA freezes the base weights and trains a small low-rank delta injected into the attention and MLP projections. QLoRA additionally quantizes the frozen base to 4-bit during training, which is what makes single-GPU tuning of a large model feasible.

| Property | Typical value |
|---|---|
| Trainable params | 0.1–2% of base |
| Adapter size on disk | 20 MB (r=8, small model) → ~400 MB (r=64, 70B) |
| Training VRAM (QLoRA, 4-bit base) | ~10 GB for 8B · ~24 GB for 32B · ~48 GB for 70B |
| Training time | hours, not days, on one rented GPU for a few thousand examples |

### The argument for a single one

**Data.** A behavior-changing adapter wants on the order of 1,000–10,000 gated (input → ideal output) pairs. Per adapter. Forty-nine adapters is forty-nine data-collection problems, and the low-volume agents (`be-planner` fires once per initiative) will never reach threshold. One adapter pools every agent's runs into one training set, so the mechanical writers that fire constantly subsidise the ones that do not.

**Eval.** Every adapter needs its own held-out set, its own score, its own regression watch. One adapter is one number to defend.

**What is actually shared.** Across all 374 skills and 49 agents the library repeats the same disciplines:

- the `blocker` / `major` / `minor` / `nit` severity table and the review output format
- the `#confirmed` / `#inferred` / `#observed` evidence grammar, and "a `file:line` is only produced by reading that line this round"
- the comment rules (`engineering-practices/code-comments`) — no inline comments, doc comments only on the four qualifying cases
- the orientation-cache protocol (`engineering-practices/agent-orientation-cache`) — TRUST / DELTA / FULL, the map is a lead not evidence
- artifact conventions — `docs/audits/` · `docs/plans/` · `docs/business-model/`, `NNN` minting, rounds never overwritten, IDs never renumbered
- the phase discipline itself — announce the mode, run the phases in order, close every section with a rollup, never skip the hostile self-review
- the house code rules — constructor injection, async all the way, no `OR` in an assertion, no `try/catch` in a test body, simplicity over speculative abstraction

That list *is* the small-model failure surface. A generic 8B does not violate it because it disagrees; it violates it because 18 KB of agent prompt plus three loaded skills is more instruction than it can hold. Baking the shared half into weights frees the context for the domain half.

**Serving.** One adapter means no multi-LoRA routing, no adapter registry, no per-request selection logic. `vllm serve <base> --enable-lora --lora-modules house=<path>` and done.

### What one adapter cannot do

It will not teach EF Core 10 specifics, Next.js App Router semantics, or Terraform provider surfaces. Those stay in the skills, where they belong and where they can be updated without retraining.

---

## 2. What the base costs

The adapter is near-free. The base model is the whole bill.

Rough VRAM at 4-bit, before KV cache. Add 20–50% for the long contexts this library uses (agent prompts 7–29 KB, p50 ~18 KB, plus 2–5 skills per phase at p50 ~13 KB — assume 32k minimum, realistically 128k):

| Class | Examples | VRAM (weights) | Realistic host |
|---|---|---|---|
| 8B | Qwen3-8B, Llama-3.1-8B | ~6 GB | consumer GPU, Mac 32 GB |
| 14B | Qwen3-14B | ~10 GB | 1× 3090/4090 |
| 30–32B | Qwen3-32B, Devstral-class | ~20–24 GB | 1× 4090, Mac Studio 64 GB |
| 70B | Llama-3.3-70B, Qwen2.5-72B | ~45 GB | 2× 4090, 1× A100/H100 80 GB |

**Money, kept warm:**

| Option | Approx. cost | Notes |
|---|---|---|
| Rented H100 80 GB, 24/7 | ~$1,500–2,200 / mo | spot is cheaper and less reliable |
| Rented H100, scale-to-zero | usage-priced | 30–120 s cold start — rough for interactive work, fine for batch |
| Mac Studio, 64–192 GB unified | one-time ~$4–10k | MLX / llama.cpp; slow prefill, fine for the mechanical lanes |
| 2× 4090 workstation | one-time ~$5–7k | 48 GB total; 70B at 4-bit fits tightly |

**`shanks` is not a candidate** — a wifi-only Lenovo laptop running microk8s is a control plane, not an inference host. It can orchestrate remote inference; it cannot serve a 32B.

**The honest comparison:** an always-warm H100 is a great many frontier API tokens. This wins on economics only at high volume on the mechanical lanes, or when offline / on-prem / data-residency is a hard requirement rather than a preference.

---

## 3. The real blocker: training data

You have zero labeled pairs today. The only realistic source is **distillation from your own runs**: capture transcripts of frontier models executing these agents, filter to the runs that produced good artifacts, train the small model to imitate them.

```
frontier runs ──► transcript capture ──► automated quality gate ──► human spot-check ──► SFT set
                                              │
                                              └── rejects → discard
```

### Why this library suits it unusually well

The artifacts are **structured and script-checkable** — the automatic quality signal most fine-tuning projects lack:

| Artifact | Machine-checkable property |
|---|---|
| `code-auditor` report | every finding carries a `file:line`; the file and line exist at that commit |
| `*-conformance-r<N>.md` | all lettered sections present; every section has a rollup; no ID renumbered vs. the prior round |
| `delivery-plan.md` | every `agent` / `skills[]` string resolves against the real catalog; `streamId` + `order` all-or-nothing; `dependsOn` acyclic |
| `api-surface.md` | every endpoint has request/response field tables; validation-catalog references resolve |
| generated test code | compiles; no `Thread.Sleep`; no `try/catch` in a test body; no `OR` in an assertion |
| generated production code | compiles; no inline comments; no service locator; no `.Result` / `.Wait()` |
| `-explained.md` companion | contains no rule or number absent from its source; header + source commit present |

Note what these check: almost entirely the *shared discipline* of §1, not domain correctness. The gate and the adapter are aimed at the same thing, which is why one adapter is the coherent target.

**Build these once, use them twice** — as the eval harness (Phase 0) and as the data filter (Phase 2). Highest-leverage work in the document.

### Volume

One adapter needs ~2,000–5,000 gated pairs *in total*, pooled across agents — not per agent. At a 30–60% gate pass rate that is a few thousand captured runs, reachable over months of normal use. Weight the mix toward the mechanical writers (§5) because they generate the most data and the cleanest signal, but keep a tail of every agent type so the discipline generalises rather than overfitting to code emission.

### Synthetic augmentation

You can multiply real runs by varying inputs (different stacks, entity names, versions) and having a frontier model produce the ideal output, gated identically. Supplement, never replacement — synthetic data inherits and amplifies the teacher's blind spots.

---

## 4. What it buys, and what it does not

**Buys:**

- **Procedure adherence.** The characteristic small-model failure here is structural: phases skipped, Mode B collapsed into Mode A, rollups dropped, the read-only contract broken by a "helpful" fix. SFT is very good at teaching a fixed shape.
- **Prompt compression.** Agent files run 7–29 KB, plus loaded skills. With the shared discipline in weights, the runtime prompt carries domain only — a per-call cost *and* latency win compounding over every phase.
- **House conventions by default** — severity table, evidence tiers, comment rules, artifact naming, `NNN` minting.
- **Trainable refusals** — "never emit an agent name outside the catalog", "never mark Resolved without a fresh re-trace". Exactly what a generic small model gets wrong.

**Does not buy:**

- **Reasoning headroom.** A tuned 8B will not out-trace a frontier model across 40 files. Holding a 60-item register while tracing code and *refusing to confabulate* is capability, not format.
- **Knowledge** of framework versions and provider surfaces.
- **Long-context reliability** — tuning at 8k and serving at 128k does not make it good at 128k.
- **Severity judgment.** Whether an unearned abstraction is `major` or `minor` here is a call.

---

## 5. Training mix — which agents feed the adapter

One adapter, but the data mix is deliberate. Weight by signal quality and volume, not by how much you like the agent.

**Heavy weight — mechanical, fixed output shape, compiler-checkable, high volume:**
`be-{dotnet,java,node}-pattern-writer` · `api-models` · `api-client-writer` · `test-data-builder` · `mobile-screen-objects` · `gherkin-step-code` · `feature-file-writer` · `be-shared-plain-language-companion` and the `-explained.md` lane · `page-object-design` (emit half).

**Medium weight — structure-heavy, judgment-light enough to score:**
the six `code-review` reviewers · the nine qa test reviewers · the three `standards-audit` skills · `business-analysis:stories` · `business-analysis:epics` · `requirements-breakdown`.

**Light weight, present but not dominant — for the discipline, not the domain:**
a tail of `code-auditor`, `be-planner`, and `business-analyst` runs. Include them so the adapter learns the evidence grammar and phase structure those agents exemplify best; do **not** include enough for the model to think it can *be* them.

**Excluded entirely:** `penetration-tester`, `infra-security-tester`, `security-test-planner`. Authorization-gated, `#volatile`, destructive-adjacent. Never train a small model toward behavior whose safety depends on a gate.

---

## 6. Routing — where the adapter is allowed to run

The adapter raises the floor; it does not change the ceiling. Wire a frontier fallback from day one and keep this split permanently:

| Route to the house adapter | Keep on frontier, always |
|---|---|
| the heavy-weight mechanical writers (§5) | `be-planner` · `security-test-planner` |
| `-explained.md` companion generation | `code-auditor` · `be-documenter` · `business-analyst` |
| structure-first reviewers, with findings spot-checked | `penetration-tester` · `infra-security-tester` |

The reason is the same in every right-hand row: the artifact's entire value is a claim of fidelity. An audit is worth something only because its citations were really read; a plan pack is worth something only because its agent names really resolve. A model that is 95% right about those is worse than no output, because the 5% is invisible and load-bearing.

---

## 7. Build path

### Phase 0 — Eval harness (do this regardless)

Prerequisite for everything, useful on its own: it also answers "does this library survive on a smaller model" for the portability question, and catches regressions when a skill is edited.

- [ ] `tools/eval/` — runner that executes a named skill or agent against a fixture repo and scores the artifact.
- [ ] **Fixture repos** — 5–10 small, frozen, representative projects (one per stack lane). Frozen matters: scores must be comparable across runs.
- [ ] **Scorers** — one per artifact family, implementing §3's checkable properties. Start with `file:line` validity, section completeness, ID stability across rounds, catalog-name resolution, compile/lint for generated code.
- [ ] **Report** — per-skill pass rate, per-scorer breakdown, diff vs. the previous run. Reuse `tools/token-audit.py`'s shape (it already parses frontmatter, walks the marketplace, prints per-plugin tables).
- [ ] **Baseline** — score the current frontier model on every fixture. Everything else is measured against this.

Exit: `python3 tools/eval/run.py --skill be-dotnet:patterns-apply` prints a score; a full sweep prints a table.

### Phase 1 — Establish the gap

- [ ] Run the harness against 3–4 open-weight bases across 2–3 size classes (e.g. Qwen3-8B / Qwen3-32B / Llama-3.3-70B), **untuned, on the current prompts**, via rented GPU-hours or an OpenRouter-style API.
- [ ] Produce a gap table: per skill, frontier vs. each base.
- [ ] **Decision gate.** If an untuned 32B already clears your bar on the heavy-weight lane, you do not need to fine-tune — you need a serving story. Stop and say so.

### Phase 2 — Data capture

- [ ] **Capture.** Log every agent run — loaded prompt, input, tool calls, final artifact, repo commit. A Claude Code hook (`settings.json`, per the `update-config` skill) can write these locally without changing how you work.
- [ ] **Gate.** Run each artifact through the Phase-0 scorers; auto-reject failures.
- [ ] **Spot-check.** Sample 5–10% of passes — scorers catch structural defects, not wrong-but-well-formed ones.
- [ ] **Redact.** Strip client-specific, credential-shaped, or NDA content before a pair enters the set. Enforce at capture time, not later.
- [ ] **Format.** JSONL `{system, messages[], artifact, scores{}, provenance{commit, date, agent, skills[]}}`. Keep provenance — you will re-filter later with better scorers.
- [ ] **Mix.** Assemble per §5 weights; record the mix so a later run is reproducible.

Exit: ~2,000+ gated pairs, pooled, with the intended weighting.

### Phase 3 — Train

- [ ] Base: the smallest model that cleared Phase 1's bar, plus one size class up as a control.
- [ ] Recipe (starting points, not tuned): QLoRA, r=16–32, alpha=32–64, dropout 0.05, targeting all attention + MLP projections; LR ~1e-4 cosine, 2–3 epochs.
- [ ] Tooling: **Axolotl** or **Unsloth** for the loop (QLoRA + packing + chat templates handled); **PEFT** directly if you want control.
- [ ] **Split by fixture repo, never randomly** — two runs against the same repo share nearly all their context, so a random split leaks.
- [ ] Score with the Phase-0 harness against three references: untuned same-size base, untuned one-size-up base, frontier.
- [ ] **Decision gate.** The adapter must beat the untuned same-size base by a margin worth the pipeline. If it merely matches the one-size-up base, **buy the bigger model instead** — that is a real and acceptable outcome.

### Phase 4 — Serve

- [ ] `vllm serve <base> --enable-lora --lora-modules house=<path>`. One adapter, no routing table.
- [ ] Warm vs. scale-to-zero decided by usage shape — mechanical lanes are batchy and tolerate cold starts; interactive ones do not.
- [ ] Implement the §6 split in the client: heavy-weight lane → house adapter, everything in the right-hand column → frontier. Fail closed — an unrecognised agent goes to frontier.
- [ ] Re-score monthly against the frozen fixtures. A drifting score means the library changed and the adapter is stale.

### Phase 5 — Maintenance

- [ ] Retrain when the shared discipline changes (a new global rule, a changed severity table, a new artifact convention) — not when a domain skill changes. Domain lives in the skills, deliberately.
- [ ] Keep the frozen fixtures frozen. If a fixture must change, it becomes a new fixture and the baseline is re-established.

---

## 8. Explicitly deferred: the per-agent fleet

Multi-LoRA serving (vLLM / SGLang hold one resident base and swap small adapters per request at a few percent overhead) makes a fleet *technically* cheap to serve. It is not cheap to build: forty-nine data-collection problems, forty-nine eval surfaces, and low-volume agents that never reach data threshold.

**Revisit only if** the house adapter lands and the Phase-0 harness still shows a specific heavy-weight skill trailing frontier by a margin that matters. Then train one skill-specific adapter *on top of* the house mix, serve it via multi-LoRA with the house adapter as fallback, and delete it if it does not beat the house adapter outright. Not before.

---

## 9. Open questions

- What is actual monthly spend today, split by agent? Without it the §2 ROI is hypothetical. Pull this before starting.
- Is offline / on-prem a hard requirement (client NDA, air-gapped engagement) or a preference? A requirement changes the verdict; a preference does not.
- Does transcript capture raise client-confidentiality issues that survive the Phase-2 redaction pass? If so, capture needs per-project opt-in rather than default-on.
- Which fixture repos — small enough to run cheaply, representative enough to score, unencumbered enough to commit?

---

## 10. Related documents

- `TOKEN-OPTIMIZATION-PLAN.md` — the cheaper, already-in-flight lever on the same cost problem. Take those wins first.
- `tools/token-audit.py` — the parsing/reporting shape the eval harness should reuse.
- Model portability (running the library on non-Anthropic models as-is) — separate plan, shares the Phase-0 harness.
