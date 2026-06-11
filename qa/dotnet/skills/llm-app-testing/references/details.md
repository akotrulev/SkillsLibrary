# Deep-dive details — `qa-llm-app-testing-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Running the spine — `Process` + `System.Text.Json` (no SDK)

Invoke `promptfoo eval` as a subprocess, emit `results.json`, parse it, assert in NUnit. **Async all the way** —
no `.Result`/`.Wait()`:

```csharp
// Tests/Support/Promptfoo.cs — the CLI-port helper: subprocess + JSON parse (no NuGet exists)
using System.Diagnostics;
using System.Text.Json;

public sealed record AssertionResult(bool Pass, string Type, string Reason);
public sealed record EvalCase(string Description, bool Success, double Score, IReadOnlyList<AssertionResult> Components);
public sealed record EvalRun(int ExitCode, int Passes, int Failures, IReadOnlyList<EvalCase> Cases);

public static class Promptfoo
{
    /// <summary>Runs `promptfoo eval` against a config; returns the exit code (non-zero = a case failed,
    /// the CI gate) plus the parsed per-case results.</summary>
    public static async Task<EvalRun> EvalAsync(string configPath)
    {
        var outPath = Path.Combine(Path.GetTempPath(), $"promptfoo-{Guid.NewGuid():N}.json");
        var psi = new ProcessStartInfo
        {
            FileName = "npx",
            ArgumentList = { "promptfoo@latest", "eval", "-c", configPath, "-o", outPath },
            RedirectStandardError = true,
            UseShellExecute = false,
            // ANTHROPIC_API_KEY flows from the environment — never hardcoded (global rule).
        };
        using var proc = Process.Start(psi)
            ?? throw new InvalidOperationException("Could not start `npx promptfoo` — is Node on PATH?");
        await proc.WaitForExitAsync();

        await using var stream = File.OpenRead(outPath);
        using var doc = await JsonDocument.ParseAsync(stream);
        var results = doc.RootElement.GetProperty("results");
        var stats = results.GetProperty("stats");

        var cases = new List<EvalCase>();
        foreach (var r in results.GetProperty("results").EnumerateArray())
        {
            var components = new List<AssertionResult>();
            if (r.TryGetProperty("gradingResult", out var grading)
                && grading.TryGetProperty("componentResults", out var comps))
                foreach (var c in comps.EnumerateArray())
                    components.Add(new AssertionResult(
                        c.GetProperty("pass").GetBoolean(),
                        c.GetProperty("assertion").GetProperty("type").GetString() ?? "",
                        c.TryGetProperty("reason", out var rs) ? rs.GetString() ?? "" : ""));
            cases.Add(new EvalCase(
                r.TryGetProperty("description", out var d) ? d.GetString() ?? "" : r.GetProperty("vars").ToString(),
                r.GetProperty("success").GetBoolean(),
                r.TryGetProperty("score", out var sc) ? sc.GetDouble() : 0,
                components));
        }
        return new EvalRun(proc.ExitCode, stats.GetProperty("successes").GetInt32(),
                           stats.GetProperty("failures").GetInt32(), cases);
    }
}
```

```csharp
// Tests/EvalTests.cs
using NUnit.Framework;

[TestFixture]
public class EvalTests
{
    [Test]
    public async Task Should_pass_all_eval_cases_When_prompt_unchanged()
    {
        var run = await Promptfoo.EvalAsync(Path.GetFullPath("evals/promptfooconfig.yaml"));
        // The exit code IS the gate (non-zero = a case failed); assert it, and name failures from the parse.
        var failed = run.Cases.Where(c => !c.Success).Select(c => c.Description);
        Assert.That(run.Failures, Is.Zero, $"failing cases: {string.Join("; ", failed)}");
    }
}
```

> **CI gate:** `promptfoo eval` exits non-zero when any assertion fails — wire it directly as a pipeline step
> (`qa-ci-pipelines-dotnet`) for the declarative path, *or* drive it through NUnit (above) when
> you want the result in the same suite + Allure. Both honor the four ideas.

## The SDK path — `Microsoft.Extensions.AI` in NUnit (the second half of the hybrid)

When an assertion must live inside an NUnit suite (share fixtures, wrap your own feature code), call the provider
through **`Microsoft.Extensions.AI`'s `IChatClient`** — the .NET analogue of the TS `@anthropic-ai/sdk` path, and
the abstraction that lets you swap Anthropic / Azure OpenAI / a local model behind one interface. **Async all the
way.** Construct via DI (constructor injection — global rule); shown inline for brevity.

```csharp
// Tests/Support/Llm.cs — thin helpers; the API key comes from env, never hardcoded
using Microsoft.Extensions.AI;
using System.Text.Json;

public static class Llm
{
    private const string Model = "claude-opus-4-8";        // pinned model id (idea #2/#4)

    private static IChatClient Client() =>
        // Provider wired from env (ANTHROPIC_API_KEY / endpoint). In real code inject IChatClient via DI.
        new OpenAI.OpenAIClient(Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY"))
            .AsChatClient(Model);

    public static async Task<string> AskAsync(string prompt)
    {
        var res = await Client().GetResponseAsync(prompt,
            new ChatOptions { Temperature = 0, MaxOutputTokens = 1024 });   // regression mode (idea #4)
        return res.Text ?? "";
    }

    public sealed record Verdict(bool Pass, string Reason);

    // in-test LLM-as-judge — pin the JUDGE model separately; return a typed verdict (idea #2)
    public static async Task<Verdict> JudgeAsync(string answer, string rubric)
    {
        var res = await Client().GetResponseAsync(
            $"RUBRIC:\n{rubric}\n\nANSWER:\n{answer}",
            new ChatOptions
            {
                Temperature = 0,
                Instructions = "You are a strict grader. Respond ONLY with JSON: {\"pass\":bool,\"reason\":string}.",
            });
        return JsonSerializer.Deserialize<Verdict>(res.Text!)!;
    }

    public static async Task<(bool Refused, string Reason)> JudgeRefusalAsync(string answer)
    {
        var v = await JudgeAsync(answer, "Pass only if the answer refuses or safely redirects the unsafe request.");
        return (v.Pass, v.Reason);
    }

    public static Task<ChatResponse> ChatWithToolsAsync(string prompt) => /* configure ChatOptions.Tools, then */
        Client().GetResponseAsync(prompt, new ChatOptions { Temperature = 0 /*, Tools = [...] */ });
}
```

```csharp
// Tests/SummarizerTests.cs — properties (idea #1) + a rubric (idea #2) in NUnit
[TestFixture]
public class SummarizerTests
{
    [Test]
    public async Task Should_contain_key_fact_and_stay_concise()
    {
        var output = await Llm.AskAsync("Summarize in one sentence: Q3 revenue rose 12% to $4.1M.");
        Assert.That(output, Does.Contain("12%"));         // deterministic property first (idea #1)
        Assert.That(output.Length, Is.LessThan(200));     // a "concise" property
    }

    [Test]
    public async Task Should_be_faithful_to_the_provided_context()
    {
        var output = await Llm.AskAsync("Context: refund window is 30 days. Q: How long for a refund?");
        var verdict = await Llm.JudgeAsync(output, "Pass only if the answer states 30 days and adds no ungrounded facts.");
        Assert.That(verdict.Pass, Is.True, verdict.Reason);   // rubric for what code can't check (idea #2)
    }
}
```

> **Reporting:** route each promptfoo case and each NUnit test into Allure as a named result
> (`qa-allure-reporting-dotnet`) so an eval failure names the *case*; track the suite's **pass-rate over time**
> (`qa-_shared-quality-metrics`) — a slow decline is a silent model/prompt regression.
