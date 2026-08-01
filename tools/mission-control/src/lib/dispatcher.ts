import { query } from "@anthropic-ai/claude-agent-sdk";
import { findAgent, getCatalog } from "./catalog";
import { IMPLEMENTER_MODEL, LIBRARY_ROOT } from "./config";
import { eventBus } from "./events";
import { implementerSystemPrompt, implementerUserPrompt } from "./prompts";
import { appendLog, updateRun } from "./store";
import type { Run, Task, TaskLogEntry } from "./types";

/** Tools an implementer may use without a permission prompt. */
const IMPLEMENTER_TOOLS = [
  "Read",
  "Write",
  "Edit",
  "Glob",
  "Grep",
  "Bash",
  "TodoWrite",
  "WebSearch",
  "WebFetch",
];

/** In-flight dispatches, so a run can be cancelled. */
const inflight = new Map<string, AbortController>();

function key(runId: string, taskId: string): string {
  return `${runId}:${taskId}`;
}

export function abortTask(runId: string, taskId: string): void {
  inflight.get(key(runId, taskId))?.abort();
}

export function abortRun(runId: string): void {
  for (const [k, controller] of inflight) {
    if (k.startsWith(`${runId}:`)) controller.abort();
  }
}

async function log(
  runId: string,
  taskId: string,
  kind: TaskLogEntry["kind"],
  text: string,
): Promise<void> {
  const entry: TaskLogEntry = { at: new Date().toISOString(), kind, text };
  await updateRun(runId, (run) => {
    const task = run.tasks.find((t) => t.id === taskId);
    if (task) appendLog(task, entry);
  });
  eventBus.publish(runId, { type: "task:log", taskId, entry });
}

/** Pull the `## Summary` block out of the implementer's final message. */
function extractSummary(finalText: string): string {
  const match = finalText.match(/##\s*Summary\s*\n([\s\S]*)$/i);
  const body = (match?.[1] ?? finalText).trim();
  // Keep the board readable if the agent ignored the length guidance.
  return body.length > 1200 ? `${body.slice(0, 1200)}…` : body;
}

export interface DispatchResult {
  ok: boolean;
  summary?: string;
  error?: string;
  costUsd?: number;
}

/**
 * Run one task to completion with its assigned library agent.
 *
 * The agent definition is injected programmatically rather than relied upon
 * from `.claude/agents`, because the implementer's cwd is the *target*
 * directory, which has no knowledge of this library.
 */
export async function dispatchTask(run: Run, task: Task): Promise<DispatchResult> {
  const catalog = await getCatalog();
  const agent = findAgent(catalog, task.agent);
  if (!agent) {
    return { ok: false, error: `Agent "${task.agent}" is not in the catalog.` };
  }

  const controller = new AbortController();
  inflight.set(key(run.id, task.id), controller);

  await log(run.id, task.id, "system", `Dispatching ${agent.name} (${agent.relPath})`);

  let finalText = "";
  let costUsd: number | undefined;

  try {
    for await (const message of query({
      prompt: implementerUserPrompt(run, task),
      options: {
        cwd: run.targetDir,
        model: IMPLEMENTER_MODEL,
        systemPrompt: implementerSystemPrompt(agent, LIBRARY_ROOT),
        allowedTools: IMPLEMENTER_TOOLS,
        permissionMode: "acceptEdits",
        // The agent reads its own definition and skills from the library.
        additionalDirectories: [LIBRARY_ROOT],
        // Load the target project's CLAUDE.md and settings — the implementer
        // should follow the conventions of the repo it is working in.
        settingSources: ["project"],
        abortController: controller,
        maxTurns: 200,
      },
    })) {
      if (message.type === "assistant") {
        for (const block of message.message.content) {
          if (block.type === "text" && block.text.trim()) {
            await log(run.id, task.id, "text", block.text.trim());
          } else if (block.type === "tool_use") {
            await log(run.id, task.id, "tool", describeToolUse(block));
          }
        }
      } else if (message.type === "result") {
        costUsd = message.total_cost_usd;
        if (message.subtype === "success") {
          finalText = message.result;
        } else {
          return {
            ok: false,
            error: `Agent ended with: ${message.subtype}`,
            costUsd,
          };
        }
      }
    }
  } catch (error) {
    const reason = controller.signal.aborted
      ? "Cancelled."
      : error instanceof Error
        ? error.message
        : String(error);
    return { ok: false, error: reason, costUsd };
  } finally {
    inflight.delete(key(run.id, task.id));
  }

  if (!finalText.trim()) {
    return { ok: false, error: "Agent produced no final output.", costUsd };
  }

  return { ok: true, summary: extractSummary(finalText), costUsd };
}

/** One-line, human-readable rendering of a tool call for the task log. */
function describeToolUse(block: { name: string; input?: unknown }): string {
  const input = (block.input ?? {}) as Record<string, unknown>;
  const first = (...keys: string[]): string | undefined => {
    for (const k of keys) {
      const v = input[k];
      if (typeof v === "string" && v.trim()) return v.trim();
    }
    return undefined;
  };

  const detail =
    first("file_path", "path", "command", "pattern", "query", "url", "description") ?? "";
  const oneLine = detail.split("\n")[0];
  const trimmed = oneLine.length > 160 ? `${oneLine.slice(0, 160)}…` : oneLine;
  return trimmed ? `${block.name}: ${trimmed}` : block.name;
}
