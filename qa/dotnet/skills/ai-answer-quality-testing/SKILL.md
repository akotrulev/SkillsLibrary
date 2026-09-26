---
name: qa-ai-answer-quality-testing-dotnet
description: Use when testing a RAG feature from a .NET / NUnit suite — decompose RETRIEVAL from GENERATION so a bad answer is localized, then assert the RAG triad (context relevance · groundedness · answer relevance) plus retrieval-ranking metrics; Ragas (default), DeepEval or promptfoo. Triggers "test our RAG pipeline", "is the answer grounded in the retrieved chunks", "evaluate context precision/recall", "build a RAG golden set". Not for non-RAG LLM evals (`qa-ai-feature-testing-dotnet`).
---

# RAG Testing (.NET 8 / NUnit — retrieval ⊕ generation, Ragas-spined)

A RAG feature is **two systems wearing one trench coat**: a **retriever** (query → top-k chunks from a vector /
hybrid index) and a **generator** (chunks + query → answer). A wrong answer is therefore *ambiguous* — it can be
the **retriever's** fault (it never fetched the chunk that holds the answer) or the **generator's** fault (it had
the chunk and hallucinated past it). **The cardinal discipline of RAG testing is to decompose the two and assert
each separately**, then assert end-to-end. An end-to-end-only suite tells you *that* the answer is wrong; it can't
tell you *which half to fix* — which is the entire point of testing a RAG.

This skill is the **RAG specialization of `qa-ai-feature-testing-dotnet`** — it inherits that skill's four ideas
(property-not-string · the-judge-is-a-versioned-artifact · an-eval-is-a-dataset · regression-vs-stochastic), its
judge-pinning + calibration discipline, and its spine mechanics. It does **not** repeat them. What it adds is the
**retrieval ⊕ generation decomposition**, the **RAG triad**, **retrieval-ranking metrics**, and the **golden set
that carries reference contexts** — the things a generic LLM-output test doesn't have.

> **The discipline this skill encodes** — five ideas on top of ai-feature-testing's four:
>
> 1. **Decompose retrieval from generation — always.** Test the retriever alone (did the right chunk come back,
>    ranked high?), the generator alone (given good context, is the answer grounded + complete?), then end-to-end.
>    A failing end-to-end case is triaged by which sub-test also fails.
> 2. **The RAG triad is the minimum coverage.** **Context Relevance** (are the retrieved chunks relevant to the
>    query?) · **Groundedness/Faithfulness** (is every claim in the answer supported by the retrieved context — no
>    hallucination?) · **Answer Relevance** (does the answer actually address the query?). Triad green ⇒ the loop
>    is sound; any leg red localizes the fault.
> 3. **When you have labeled relevant docs, retrieval is DETERMINISTIC — measure rank, not vibes.** Precision@k,
>    Recall@k, MRR, NDCG, Hit-Rate are computed from a ground-truth relevant-doc set — free, instant, never flaky.
>    Reach for an LLM judge (context relevance) only when you *lack* labels.
> 4. **A RAG golden set carries reference CONTEXTS, not just a reference answer.** `{query, ground-truth answer,
>    ground-truth relevant chunk-ids/contexts}`. Without the reference contexts you literally cannot compute
>    **recall** (did retrieval miss something?) — the most common production RAG failure.
> 5. **Test the "not in the corpus" path.** A RAG must *abstain or say "I don't know"* when the answer isn't in
>    the index — not hallucinate. The no-answer case is a first-class case, not an afterthought.

## Decision matrix — failure symptom → which stage → which assertion

| Symptom | Stage at fault | What to assert | Metric (Ragas · DeepEval · promptfoo) |
|---|---|---|---|
| Answer omits a fact that IS in the corpus | **retrieval** (recall) | the right chunk was retrieved | `LLMContextRecall` / `NonLLMContextRecall` · `ContextualRecallMetric` · `context-recall` |
| Retrieved chunks are off-topic / noisy | **retrieval** (precision) | retrieved chunks are relevant + ranked high | `LLMContextPrecisionWithReference` · `ContextualPrecisionMetric` · `context-relevance` |
| Right chunk retrieved but ranked low | **retrieval** (ranking) | rank of first relevant doc | MRR / NDCG (deterministic, see below) |
| Answer states facts NOT in the context | **generation** (faithfulness) | every claim grounded in retrieved context | `Faithfulness` · `FaithfulnessMetric` · `context-faithfulness` |
| Answer is grounded but doesn't answer the Q | **generation** (relevance) | answer addresses the query | `ResponseRelevancy` · `AnswerRelevancyMetric` · `answer-relevance` |
| Answer is incomplete vs ground truth | **generation** (completeness) | answer covers the reference claims | `FactualCorrectness` / G-Eval · `GEval` · `llm-rubric` |
| Hallucinates when answer ISN'T in corpus | **generation** (abstention) | refuses / says "not found" | rubric · `GEval` refusal · `llm-rubric` |
| Citations point to the wrong chunk | **generation** (attribution) | cited chunk-ids support the claim | custom (see Attribution below) |
| Adding a distractor chunk flips the answer | **generation** (robustness) | answer stable under noise | `NoiseSensitivity` · sample-rate · `--repeat` |

**Rule of thumb:** start at the **retrieval** rows — if recall is broken, no generator fix helps. Use the
**deterministic** ranking metrics whenever you have a labeled relevant-doc set; fall to the **LLM-judged** triad
legs when you don't. The generation rows are `qa-ai-feature-testing-dotnet`'s ladder applied to a *grounded* answer.

## Two-stage testing

### Stage 1 — retrieval in isolation (deterministic when you have labels)

When the golden set labels which chunk-ids are relevant per query, the retriever is a **ranking function** and you
score it with classic IR metrics — no LLM, no cost, no flake. This is `qa-data-driven-testing-dotnet` over
retrieval results.

```csharp
// Tests/RetrievalTests.cs — retrieval is a ranking problem; measure rank against labeled relevant ids
public class RetrievalTests
{
    private const int K = 5;
    private static IEnumerable<TestCaseData> Goldens() =>
        GoldenSet.Load("golden/rag-cases.json").Select(g => new TestCaseData(g).SetName($"retrieval: {g.Query}"));

    private static double RecallAtK(IReadOnlyList<string> retrieved, IReadOnlyList<string> relevant, int k)
    {
        var top = retrieved.Take(k).ToHashSet();
        return relevant.Count == 0 ? 1 : (double)relevant.Count(top.Contains) / relevant.Count;
    }
    private static double ReciprocalRank(IReadOnlyList<string> retrieved, IReadOnlyList<string> relevant)
    {
        var i = retrieved.ToList().FindIndex(relevant.Contains);
        return i < 0 ? 0 : 1.0 / (i + 1);
    }

    [TestCaseSource(nameof(Goldens))]
    public async Task Retrieval_finds_the_relevant_chunks(GoldenCase g)
    {
        var ranked = await _retriever.RetrieveAsync(g.Query, K);                 // ranked chunk-ids
        Assert.That(RecallAtK(ranked, g.RelevantChunkIds, K), Is.GreaterThanOrEqualTo(0.8));  // recall@5 ≥ 0.8
        Assert.That(ReciprocalRank(ranked, g.RelevantChunkIds), Is.GreaterThanOrEqualTo(0.5)); // first relevant in top-2
    }
}
```

> When you **don't** have labeled relevant chunks, you can't compute recall deterministically — fall back to an
> LLM judge for **context relevance** (Ragas `LLMContextPrecisionWithReference` against the ground-truth answer,
> or DeepEval `ContextualRelevancyMetric`). But prefer building labels: deterministic retrieval gates are the
> cheapest, sharpest signal you have.

### Stage 2 — generation given fixed context (isolate the generator)

Feed the generator a **known-good context** (the labeled relevant chunks, not the live retriever) and assert the
answer is **grounded** and **complete**. This isolates generation: if it fails here, the bug is in the prompt/model,
not retrieval. Use the parent skill's chosen spine for the grounding assertions (Ragas `Faithfulness`, DeepEval
`FaithfulnessMetric`, or promptfoo `context-faithfulness`).

### Stage 3 — end-to-end (the live loop) + the triad

Run the real retriever → generator and assert the **full triad**. A red leg here, cross-referenced with stages 1–2,
names the culprit.

## The golden set — it carries reference CONTEXTS

The single structural difference from an `ai-feature-testing` dataset: each row carries the **ground-truth relevant
contexts/chunk-ids** alongside the reference answer. Build it with `qa-data-driven-testing-dotnet` mechanics
(one row = one named case, loaded from an external file), and **never** commit real customer PII.

```jsonc
// golden/rag-cases.json — query + reference answer + reference contexts (the recall enabler)
[
  {
    "query": "How long do I have to request a refund?",
    "groundTruthAnswer": "You have 30 days from delivery to request a refund.",
    "relevantChunkIds": ["policy#refunds-window"],          // enables deterministic recall@k
    "referenceContexts": ["The refund window is 30 days from delivery."]  // enables context-recall judging
  },
  { "query": "What is the airspeed of an unladen swallow?",  // a NOT-IN-CORPUS case (idea #5)
    "groundTruthAnswer": "NOT_IN_CORPUS", "relevantChunkIds": [], "referenceContexts": [] }
]
```

> **Synthesize, then human-review.** Ragas ships a test-set generator that bootstraps `{query, answer, context}`
> triples from your corpus (see `references/ragas.md`); treat its output as a *draft* golden set a human curates —
> a synthetic label is a hypothesis, not ground truth.

## Choosing the spine — Ragas (default for RAG) vs DeepEval vs promptfoo

The four-ideas + judge-pinning + calibration all come from `qa-ai-feature-testing-dotnet`; this skill only adds
*which* assertions. Pick **one** spine per suite:

- **Ragas** (`references/ragas.md`) — the **RAG-native** framework and the default here: the four canonical RAG
  metrics (Faithfulness, ResponseRelevancy, LLMContextPrecision, LLMContextRecall) plus NoiseSensitivity,
  FactualCorrectness, and a corpus→test-set **generator**. Python — driven via `Process` + `System.Text.Json`
  exactly like promptfoo/DeepEval; pin the evaluator LLM to the house-default Claude.
- **DeepEval** — when the RAG suite lives beside a broader DeepEval suite (its `Contextual*`/`Faithfulness`/
  `AnswerRelevancy` metrics map 1:1 to the triad). See `qa-ai-feature-testing-dotnet`'s `references/deepeval.md`.
- **promptfoo** — when you want the declarative YAML matrix: `context-faithfulness` / `context-recall` /
  `context-relevance` / `answer-relevance` assertions over a CSV of cases. See `qa-ai-feature-testing-dotnet`.

**Don't double-run the same cases on two spines.** Deterministic retrieval metrics (stage 1) you compute in-code
regardless of spine.

## Attribution / citation testing

If the feature cites sources, the citation is a **deterministic** property: every cited chunk-id must (a) exist in
the retrieved set and (b) actually support the claim. Assert (a) in code (set-membership) and (b) with a faithfulness
judge scoped to the cited chunk only — a citation that points at an unretrieved or unsupporting chunk is a bug even
when the prose is fine.

## Anti-patterns

- **End-to-end-only testing.** Tells you the answer is wrong, not which half to fix. *Fix:* decompose — stage 1
  (retrieval) + stage 2 (generation on fixed context) + stage 3 (triad).
- **No ground-truth contexts in the golden set.** You cannot compute **recall** — the most common RAG failure goes
  unmeasured. *Fix:* label relevant chunk-ids / reference contexts per row.
- **Asserting the answer string** (`Is.EqualTo`). The parent-skill cardinal sin, sharper here: the risk is
  *ungrounded* content, not wording. *Fix:* faithfulness + answer-relevance, never the string.
- **An LLM judge where labeled ranking metrics fit.** Paying a judge to eyeball relevance you could compute as
  recall@k. *Fix:* build labels; deterministic IR metrics for retrieval.
- **No not-in-corpus case.** The RAG hallucinates confidently on out-of-scope queries and you never see it. *Fix:*
  an abstention case asserting "I don't know" / refusal (idea #5).
- **Faithfulness without passing the retrieved context.** The metric silently degrades to a generic check. *Fix:*
  feed the actual retrieved chunks to the metric.
- **Testing the generator against the LIVE retriever only.** A generation regression hides behind retrieval noise.
  *Fix:* stage 2 pins a known-good context.
- **Ignoring rank.** Recall@k passes but the right chunk is 9th and the generator ignores it ("lost in the
  middle"). *Fix:* also assert MRR/NDCG or a small k.
- **A frozen golden set against a live index.** The corpus drifts; yesterday's labels rot. *Fix:* version the
  golden set with the index snapshot; re-label on a re-index.
- **Real customer documents/PII as fixtures.** It's in git forever. *Fix:* synthetic corpus + synthetic queries.

## Examples

**Localizing a regression.** A nightly eval drops: end-to-end faithfulness falls from 0.9 → 0.6. Stage-1 retrieval
metrics are *unchanged* (recall@5 still 0.85) → retrieval is fine; the fault is generation. Stage-2 (generator on
fixed context) reproduces the low faithfulness → confirmed: a prompt edit made the model embellish. The
decomposition turned "the RAG got worse" into "this prompt change broke grounding" in two sub-tests.

**Composing with the parent + data-driven + db:** the **golden set** uses `qa-data-driven-testing-dotnet`
mechanics; the **judge** is pinned + calibrated per `qa-ai-feature-testing-dotnet`; the **index fixture** (seed the
vector store, assert state, tear down) reuses `qa-db-testing-*-dotnet` discipline for the store; the **stochastic**
noise-sensitivity check asserts a pass-rate (parent idea #4), not a single sample.

## Rules (hard constraints)

- **Decompose retrieval from generation.** Every RAG suite has stage-1 (retrieval), stage-2 (generation on fixed
  context), and stage-3 (end-to-end triad). A failing end-to-end case must be triageable to a stage.
- **Cover the RAG triad** — context relevance, groundedness/faithfulness, answer relevance — as the floor, plus the
  **not-in-corpus abstention** case.
- **The golden set carries reference contexts/chunk-ids**, not just a reference answer — recall is otherwise
  unmeasurable. Synthetic sets are human-reviewed drafts.
- **Deterministic retrieval metrics when labels exist** (recall@k, precision@k, MRR, NDCG) — judge-based context
  relevance only when they don't. **Never assert the answer string.**
- **Inherit, don't repeat, the parent skill:** the four ideas, judge model-id pinning + gold-set calibration,
  regression-vs-stochastic (sample N≥3 for a rate), budgets-are-assertions, keys-via-env, no-PII all come from
  `qa-ai-feature-testing-dotnet`. Async all the way; no `Thread.Sleep`.

## Cross-references

- **`qa-ai-feature-testing-dotnet`** — the **parent**: the four ideas, the assertion ladder, judge-pinning +
  calibration, the spine choice (promptfoo/DeepEval) and their references. RAG testing is its specialization; read
  it first.
- `references/ragas.md` — the **RAG-native spine**: Ragas metrics + the corpus→test-set generator, invoked as a
  subprocess (`Process` + `System.Text.Json`), evaluator LLM pinned to Claude.
- `qa-data-driven-testing-dotnet` — the golden-set row mechanics (one row = one named case, loaded externally).
- `qa-db-connection-dotnet` / `…-testcontainers-dotnet` — seed/assert/tear-down the **vector or hybrid index**
  the retriever reads (the RAG "DB").
- `qa-ai-answer-quality-testing-typescript` · `qa-ai-answer-quality-testing-java` — the sibling stacks; same five ideas, Ragas/DeepEval driven
  as a subprocess via `execa`/`ProcessBuilder`.
- `qa-_shared-quality-metrics` — track triad + recall@k **over time** (a declining recall is a silent index/embed
  regression). `qa-test-reports-dotnet` — each stage/case as a named result.
- The `qa-llm-dotnet` **agent** owns this skill alongside `ai-feature-testing` (RAG is a step of the LLM-eval run).
