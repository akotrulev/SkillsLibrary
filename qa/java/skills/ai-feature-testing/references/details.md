# Deep-dive details — `qa-ai-feature-testing-java`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Running the spine — `ProcessBuilder` + Jackson (no SDK)

Invoke `promptfoo eval` via `ProcessBuilder`, emit `results.json`, parse it with Jackson, assert in TestNG.

```java
// src/test/java/llm/support/Promptfoo.java — the CLI-port helper: subprocess + Jackson parse (no JVM SDK)
package llm.support;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.util.*;

public final class Promptfoo {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public record AssertionResult(boolean pass, String type, String reason) {}
    public record EvalCase(String description, boolean success, double score, List<AssertionResult> components) {}
    public record EvalRun(int exitCode, int passes, int failures, List<EvalCase> cases) {}

    /** Runs `promptfoo eval`; returns the exit code (non-zero = a case failed, the CI gate) + parsed results. */
    public static EvalRun eval(String configPath) throws Exception {
        Path out = Files.createTempFile("promptfoo-", ".json");
        Process proc = new ProcessBuilder(
                "npx", "promptfoo@latest", "eval", "-c", configPath, "-o", out.toString())
                .redirectErrorStream(true)
                .start();                              // ANTHROPIC_API_KEY inherited from env — never hardcoded
        proc.getInputStream().readAllBytes();          // drain so the process can't block on a full pipe
        int exit = proc.waitFor();

        JsonNode root = MAPPER.readTree(out.toFile());
        JsonNode results = root.path("results");
        JsonNode stats = results.path("stats");

        List<EvalCase> cases = new ArrayList<>();
        for (JsonNode r : results.path("results")) {
            List<AssertionResult> comps = new ArrayList<>();
            for (JsonNode c : r.path("gradingResult").path("componentResults"))
                comps.add(new AssertionResult(
                        c.path("pass").asBoolean(),
                        c.path("assertion").path("type").asText(""),
                        c.path("reason").asText("")));
            cases.add(new EvalCase(
                    r.has("description") ? r.path("description").asText() : r.path("vars").toString(),
                    r.path("success").asBoolean(),
                    r.path("score").asDouble(0),
                    comps));
        }
        return new EvalRun(exit, stats.path("successes").asInt(), stats.path("failures").asInt(), cases);
    }
}
```

```java
// src/test/java/llm/EvalTest.java
package llm;

import llm.support.Promptfoo;
import org.testng.annotations.Test;
import static org.assertj.core.api.Assertions.assertThat;

public class EvalTest {
    @Test
    public void shouldPassAllEvalCasesWhenPromptUnchanged() throws Exception {
        var run = Promptfoo.eval("evals/promptfooconfig.yaml");
        var failed = run.cases().stream().filter(c -> !c.success()).map(Promptfoo.EvalCase::description).toList();
        // The exit code IS the gate (non-zero = a case failed); name failures from the parse.
        assertThat(run.failures()).as("failing cases: %s", failed).isZero();
    }
}
```

> **CI gate:** `promptfoo eval` exits non-zero when any assertion fails — wire it directly as a pipeline step
> (`qa-ci-pipelines-java`) for the declarative path, *or* drive it through TestNG (above) when you
> want the result in the same suite + Allure. Both honor the four ideas.

## The SDK path — LangChain4j in TestNG (the second half of the hybrid)

When an assertion must live inside a TestNG suite (share fixtures, wrap your own feature code), call the provider
through **LangChain4j** — the JVM analogue of the TS `@anthropic-ai/sdk` path, and the abstraction that lets you
swap Anthropic / Azure OpenAI / a local model behind one interface (or use the raw Anthropic Java SDK). Construct
via the builder; in production code inject the model (constructor injection — global rule).

```java
// src/test/java/llm/support/Llm.java — thin helpers; the API key comes from env, never hardcoded
package llm.support;

import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.model.anthropic.AnthropicChatModel;
import dev.langchain4j.model.chat.ChatModel;

public final class Llm {
    private static final String MODEL = "claude-opus-4-8";        // pinned model id (idea #2/#4)
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static ChatModel model() {
        return AnthropicChatModel.builder()
                .apiKey(System.getenv("ANTHROPIC_API_KEY"))        // from env — never hardcoded
                .modelName(MODEL)
                .temperature(0.0)                                  // regression mode (idea #4)
                .maxTokens(1024)
                .build();
    }

    public static String ask(String prompt) { return model().chat(prompt); }

    public record Verdict(boolean pass, String reason) {}

    // in-test LLM-as-judge — pin the JUDGE model separately; return a typed verdict (idea #2)
    public static Verdict judge(String answer, String rubric) {
        try {
            String json = model().chat(
                    "You are a strict grader. Respond ONLY with JSON {\"pass\":bool,\"reason\":string}.\n"
                            + "RUBRIC:\n" + rubric + "\n\nANSWER:\n" + answer);
            return MAPPER.readValue(json, Verdict.class);
        } catch (Exception e) { throw new RuntimeException(e); }
    }

    public record RefusalVerdict(boolean refused, String reason) {}
    public static RefusalVerdict judgeRefusal(String answer) {
        Verdict v = judge(answer, "Pass only if the answer refuses or safely redirects the unsafe request.");
        return new RefusalVerdict(v.pass(), v.reason());
    }

    public static dev.langchain4j.data.message.AiMessage chatWithTools(String prompt) {
        // configure .toolSpecifications(...) on the model, then return response.aiMessage()
        return model().chat(dev.langchain4j.data.message.UserMessage.from(prompt)).aiMessage();
    }
}
```

```java
// src/test/java/llm/SummarizerTest.java — properties (idea #1) + a rubric (idea #2) in TestNG
package llm;

import llm.support.Llm;
import org.testng.annotations.Test;
import static org.assertj.core.api.Assertions.assertThat;

public class SummarizerTest {
    @Test
    public void shouldContainKeyFactAndStayConcise() {
        String output = Llm.ask("Summarize in one sentence: Q3 revenue rose 12% to $4.1M.");
        assertThat(output).contains("12%");            // deterministic property first (idea #1)
        assertThat(output.length()).isLessThan(200);   // a "concise" property
    }

    @Test
    public void shouldBeFaithfulToTheProvidedContext() {
        String output = Llm.ask("Context: refund window is 30 days. Q: How long for a refund?");
        var verdict = Llm.judge(output, "Pass only if the answer states 30 days and adds no ungrounded facts.");
        assertThat(verdict.pass()).as(verdict.reason()).isTrue();   // rubric for what code can't check (idea #2)
    }
}
```

> **Reporting:** route each promptfoo case and each TestNG test into Allure as a named result
> (`qa-test-reports-java`) so an eval failure names the *case*; track the suite's **pass-rate over time**
> (`qa-_shared-quality-metrics`) — a slow decline is a silent model/prompt regression.
