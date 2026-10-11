# Deep-dive — Ragas, the RAG-native eval spine

Read this when the chosen spine is **Ragas** (the default for a RAG suite). Ragas is the framework purpose-built
for the RAG triad + retrieval metrics; this file gives its current (v0.2+) API. The five RAG ideas and the
parent's four ideas (judge-pinning, calibration, dataset-as-data, regression-vs-stochastic) are unchanged — Ragas
just implements the triad legs for you.

## What Ragas is, and how this .NET suite drives it

[Ragas](https://docs.ragas.io) is the de-facto **open-source RAG-evaluation** framework: claim-level
**Faithfulness**, **ResponseRelevancy**, and LLM- *and* non-LLM **context precision/recall** metrics, plus a
corpus→**test-set generator**. It is **Python** — there is no NuGet — so from this .NET suite you drive it the same
honest way the stack drives promptfoo/DeepEval: **as a subprocess** (`System.Diagnostics.Process` →
`python eval_rag.py`) whose JSON output you parse with `System.Text.Json` and gate, the CLI-port shape of
`qa-dotnet:passive-scan`. Pin the **evaluator LLM** to the house-default Claude (CLAUDE.md) —
Ragas defaults to OpenAI.

> **Note on the API surface.** Ragas' legacy metric API (`Faithfulness(llm=…)` + `single_turn_ascore`, and
> `evaluate(dataset, metrics=…)`) is what's shown here; it deprecates in v0.4 and is removed in v1.0 in favor of a
> collections-based API. Pin your `ragas` version in the venv and check the docs on a bump.

## Setup (Python eval project beside the .NET app)

```bash
python -m venv evals/.venv && source evals/.venv/bin/activate
pip install -U ragas langchain-anthropic rapidfuzz   # rapidfuzz powers the deterministic NonLLM* metrics
export ANTHROPIC_API_KEY=...                          # the evaluator LLM provider (house default), via env only
```

```
evals/rag/
├── eval_rag.py             ← builds the EvaluationDataset, runs evaluate(), writes results.json
├── golden/rag-cases.json   ← {query, groundTruthAnswer, relevantChunkIds, referenceContexts} (data-driven)
└── gen_testset.py          ← optional: TestsetGenerator over the corpus → a DRAFT golden set (human-reviewed)
```

## Pin the evaluator LLM + embeddings (parent idea #2: the judge is an artifact)

Every LLM-based Ragas metric takes an evaluator `llm`; `ResponseRelevancy` and entity metrics also need
`embeddings`. Wrap the house-default Claude and reuse one instance — never let it float to the OpenAI default.

```python
# evals/rag/eval_rag.py
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_anthropic import ChatAnthropic
from langchain_community.embeddings import HuggingFaceEmbeddings   # or your prod embedding model

EVALUATOR = LangchainLLMWrapper(ChatAnthropic(model="claude-opus-4-8", temperature=0))  # pinned id+version
EMBEDDINGS = LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5"))
```

> Calibrate it against a human-labelled gold set before trusting verdicts — same discipline as the parent skill.
> `temperature=0` minimizes (does not eliminate) judge variance; re-baseline on a model bump.

## The metric library, mapped to the RAG triad + the two stages

`SingleTurnSample` carries the fields each metric reads — populate exactly the fields the metric needs (a missing
field silently degrades the score):

```python
from ragas.dataset_schema import SingleTurnSample
sample = SingleTurnSample(
    user_input="How long do I have to request a refund?",
    response=rag_pipeline(query),                 # the generated answer (system under test)
    retrieved_contexts=retrieved_chunks,          # what the LIVE retriever returned (list[str])
    reference="You have 30 days from delivery.",  # ground-truth answer (golden set)
    reference_contexts=["The refund window is 30 days from delivery."],  # ground-truth chunks (golden set)
)
```

| Ragas metric | Triad leg / stage | Computes | Needs | LLM? |
|---|---|---|---|---|
| `LLMContextRecall` | retrieval **recall** (stage 1) | claims in `reference` attributable to `retrieved_contexts` ÷ total | `user_input`, `response`, `reference`, `retrieved_contexts` | yes |
| `NonLLMContextRecall` | retrieval **recall** (stage 1) | relevant retrieved ÷ total reference contexts (string match) | `retrieved_contexts`, `reference_contexts` | **no (deterministic)** |
| `LLMContextPrecisionWithReference` | retrieval **precision/rank** (stage 1) | are relevant chunks ranked high, judged vs `reference` | `user_input`, `reference`, `retrieved_contexts` | yes |
| `LLMContextPrecisionWithoutReference` | retrieval **precision** (no labels) | relevance of each chunk vs the `response` | `user_input`, `response`, `retrieved_contexts` | yes |
| `NonLLMContextPrecisionWithReference` | retrieval **precision** (stage 1) | retrieved∩reference ÷ retrieved, via `rapidfuzz` similarity | `retrieved_contexts`, `reference_contexts` | **no (deterministic)** |
| `IDBasedContextPrecision` / `…Recall` | retrieval (stage 1) | overlap of `retrieved_context_ids` vs `reference_context_ids` | the id lists | **no (pure set-match)** |
| `Faithfulness` | **groundedness** (stage 2/3) | answer claims supported by context ÷ total claims | `user_input`, `response`, `retrieved_contexts` | yes |
| `FaithfulnesswithHHEM` | **groundedness** | same, via a local T5 NLI model (cheap, offline) | as above | no (local model) |
| `ResponseRelevancy` | **answer relevance** (stage 3) | mean cosine sim of N response-generated questions to `user_input` (NOT factuality) | `user_input`, `response`, `retrieved_contexts` | yes + embeddings |
| `FactualCorrectness` | generation **completeness/correctness** | claim-level F1 of `response` vs `reference` | `user_input`, `response`, `reference` | yes |
| `ContextEntityRecall` | retrieval recall (entities) | reference entities present in retrieved contexts | `reference`, `retrieved_contexts` | yes |
| `NoiseSensitivity` | generation **robustness** | how often a correct answer flips under irrelevant chunks (lower = better) | `user_input`, `response`, `reference`, `retrieved_contexts` | yes |

> **Prefer the `NonLLM*` / `IDBased*` variants for stage-1 retrieval whenever your golden set has reference
> contexts / chunk-ids** — they're deterministic, free, instant, never flaky (RAG idea #3). Use the `LLM*` context
> metrics only when you lack labels. The `Faithfulness` / `ResponseRelevancy` / `FactualCorrectness` legs are
> generation-side and inherently LLM/embedding-judged.

## Running a full evaluation — `evaluate()` over the dataset

```python
# evals/rag/eval_rag.py (continued)
import json
from ragas import evaluate, EvaluationDataset
from ragas.metrics import (
    Faithfulness, ResponseRelevancy, FactualCorrectness,
    LLMContextRecall, LLMContextPrecisionWithReference, NonLLMContextRecall, NoiseSensitivity,
)

rows = json.load(open("evals/rag/golden/rag-cases.json"))
samples = [
    SingleTurnSample(
        user_input=r["query"],
        response=rag_pipeline(r["query"]),                 # call the real RAG (stage 3 end-to-end)
        retrieved_contexts=last_retrieved_chunks(),        # capture what the retriever returned for this query
        reference=r["groundTruthAnswer"],
        reference_contexts=r["referenceContexts"],
    )
    for r in rows
]
dataset = EvaluationDataset(samples=samples)               # or EvaluationDataset.from_list([{...}])

result = evaluate(
    dataset=dataset,
    metrics=[
        NonLLMContextRecall(),                              # deterministic retrieval recall (stage 1)
        LLMContextPrecisionWithReference(llm=EVALUATOR),    # retrieval ranking
        Faithfulness(llm=EVALUATOR),                        # groundedness (stage 2/3)
        ResponseRelevancy(llm=EVALUATOR, embeddings=EMBEDDINGS),  # answer relevance
        FactualCorrectness(llm=EVALUATOR),                  # completeness vs reference
        NoiseSensitivity(llm=EVALUATOR),                    # robustness
    ],
    llm=EVALUATOR, embeddings=EMBEDDINGS,
)

df = result.to_pandas()                                    # per-row, per-metric scores
df.to_json("evals/.results/rag.json", orient="records")    # the artifact the .NET gate parses
# gate: fail the build if any metric's mean < its threshold (set per metric, deliberately)
THRESHOLDS = {"faithfulness": 0.85, "non_llm_context_recall": 0.8, "answer_relevancy": 0.7}
fails = {m: df[m].mean() for m, t in THRESHOLDS.items() if df[m].mean() < t}
raise SystemExit(1) if fails else print("RAG gate passed")
```

## Synthesize a draft golden set — `TestsetGenerator` (then human-review)

Bootstrapping `{query, answer, contexts}` triples from the corpus beats hand-writing them — but the output is a
**draft a human curates**, never ground truth on its own (a synthetic label is a hypothesis).

```python
# evals/rag/gen_testset.py
from ragas.testset import TestsetGenerator
from langchain_community.document_loaders import DirectoryLoader

docs = DirectoryLoader("corpus/").load()
generator = TestsetGenerator.from_langchain(generator_llm=EVALUATOR, embedding_model=EMBEDDINGS)
testset = generator.generate_with_langchain_docs(docs, testset_size=50)   # mix of simple/reasoning/multi-context
testset.to_pandas().to_json("evals/rag/golden/draft-cases.json", orient="records")
```

## Running the spine from .NET — `Process` → Python → `System.Text.Json` → gate

```csharp
// Tests/Support/Ragas.cs — invoke the Ragas eval script as a subprocess, gate NUnit on its exit code
using System.Diagnostics;
using System.Text.Json;

public static class Ragas
{
    public static async Task RunGateAsync(string script = "evals/rag/eval_rag.py",
                                          string results = "evals/.results/rag.json")
    {
        var psi = new ProcessStartInfo("evals/.venv/bin/python", script)
        {
            RedirectStandardOutput = true, RedirectStandardError = true,
        };
        using var proc = Process.Start(psi)!;
        await proc.WaitForExitAsync();

        // the script exits non-zero when any metric mean falls below its threshold — that is the gate
        if (File.Exists(results))
        {
            using var doc = JsonDocument.Parse(await File.ReadAllTextAsync(results));
            // map per-row scores -> Allure named results (qa-dotnet:test-reports)
        }
        Assert.That(proc.ExitCode, Is.Zero, "RAG eval gate failed — a triad/recall metric scored below threshold");
    }
}
```

## Anti-patterns (Ragas-specific — the RAG + parent anti-patterns still apply)

- **Letting the evaluator `llm` default to OpenAI.** *Fix:* one pinned `LangchainLLMWrapper(ChatAnthropic(...))`,
  reused; `ResponseRelevancy` also needs `embeddings` set.
- **Using `LLMContextRecall` when you have `reference_contexts`/ids.** Paying a judge for deterministic recall.
  *Fix:* `NonLLMContextRecall` / `IDBasedContextRecall`.
- **`Faithfulness` with empty `retrieved_contexts`.** Silently degrades. *Fix:* feed the actual retrieved chunks.
- **Reading `ResponseRelevancy` as factuality.** It measures relevance only — a fluent off-topic-but-grounded
  answer scores high. *Fix:* pair it with `Faithfulness` + `FactualCorrectness`.
- **Trusting a `TestsetGenerator` set unreviewed.** Synthetic labels are hypotheses. *Fix:* human-curate before it
  gates.
- **A single threshold for all metrics.** Recall and faithfulness have different risk profiles. *Fix:* per-metric
  thresholds set deliberately.

## Cross-references

- `SKILL.md` — the RAG-testing discipline (decomposition, triad, golden-set-with-contexts) that routes here.
- `qa-dotnet:ai-feature-testing` — the **parent**: four ideas, judge-pinning + calibration, the promptfoo / DeepEval
  spines (whose `references/deepeval.md` maps the same triad onto DeepEval's `Contextual*` metrics).
- `qa-dotnet:data-driven-testing` — the golden-set row mechanics.
- `qa-dotnet:db-*` — seed/assert/tear-down the vector index the retriever reads.
