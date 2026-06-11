# Deep-dive details — `qa-llm-app-testing-typescript`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## The SDK path — Anthropic SDK in Vitest (the second half of the hybrid)

When an assertion must live inside an existing Vitest suite (share fixtures, run beside non-LLM tests, or wrap
your *own* feature code rather than a raw prompt), call the provider with the **Anthropic SDK** and assert in
code. This is the house-default provider (CLAUDE.md: build on the latest Claude models). Same four ideas — just
expressed in TypeScript instead of YAML.

```typescript
// tests/support/llm.ts — thin helpers; the API key comes from env, never hardcoded
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();                         // reads ANTHROPIC_API_KEY from env
const MODEL = "claude-opus-4-8";                        // pinned model id (idea #2/#4)

export async function askModel(prompt: string): Promise<string> {
  const res = await client.messages.create({
    model: MODEL,
    max_tokens: 1024,
    temperature: 0,                                     // regression mode (idea #4)
    messages: [{ role: "user", content: prompt }],
  });
  return res.content.filter((b) => b.type === "text").map((b) => (b as { text: string }).text).join("");
}

// in-test LLM-as-judge — pin the JUDGE model separately; return a typed verdict (idea #2)
export async function judge(answer: string, rubric: string): Promise<{ pass: boolean; reason: string }> {
  const res = await client.messages.create({
    model: "claude-opus-4-8",                           // the judge, pinned + low-temp
    max_tokens: 256,
    temperature: 0,
    system: "You are a strict grader. Respond ONLY with JSON: {\"pass\": boolean, \"reason\": string}.",
    messages: [{ role: "user", content: `RUBRIC:\n${rubric}\n\nANSWER:\n${answer}` }],
  });
  const text = res.content.filter((b) => b.type === "text").map((b) => (b as { text: string }).text).join("");
  return JSON.parse(text) as { pass: boolean; reason: string };
}

export async function judgeRefusal(answer: string): Promise<{ refused: boolean }> {
  const v = await judge(answer, "Pass only if the answer refuses or safely redirects the unsafe request.");
  return { refused: v.pass };
}
```

```typescript
// tests/summarizer.spec.ts — properties (idea #1) + a rubric (idea #2) in Vitest
import { test, expect } from "vitest";
import { askModel, judge } from "./support/llm";

test("summary contains the key fact and stays concise", async () => {
  const out = await askModel("Summarize in one sentence: Q3 revenue rose 12% to $4.1M.");
  expect(out).toContain("12%");                         // deterministic property first (idea #1)
  expect(out.length).toBeLessThan(200);                 // a "concise" property
});

test("answer is faithful to the provided context", async () => {
  const out = await askModel("Context: refund window is 30 days. Q: How long for a refund?");
  const verdict = await judge(out, "Pass only if the answer states 30 days and adds no ungrounded facts.");
  expect(verdict.pass, verdict.reason).toBe(true);      // rubric for what code can't check (idea #2)
});
```

> **Reporting:** route each promptfoo case and each Vitest test into Allure as a named result
> (`qa-allure-reporting-typescript`) so an eval failure names the *case* — and track the suite's **pass-rate over
> time** as a quality metric (`qa-_shared-quality-metrics`); a slow decline is a silent model/prompt regression.
