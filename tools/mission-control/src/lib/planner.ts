import { randomUUID } from "node:crypto";
import { query } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
import { getCatalog } from "./catalog";
import { DEFAULT_MAX_PARALLEL, LIBRARY_ROOT, PLANNER_MODEL } from "./config";
import { plannerSystemPrompt, plannerUserPrompt } from "./prompts";
import type { Run } from "./types";

const PlanSchema = z.object({
  title: z.string().default("Untitled plan"),
  planningNotes: z.string().default(""),
  phases: z
    .array(
      z.object({
        id: z.string(),
        name: z.string(),
        goal: z.string().default(""),
        parallelSafe: z.boolean().default(false),
        parallelRationale: z.string().default(""),
      }),
    )
    .min(1),
  tasks: z
    .array(
      z.object({
        id: z.string(),
        phaseId: z.string(),
        title: z.string(),
        intent: z.string().default(""),
        acceptanceCriteria: z.array(z.string()).default([]),
        agent: z.string(),
        skills: z.array(z.string()).default([]),
        files: z.array(z.string()).default([]),
        dependsOn: z.array(z.string()).default([]),
      }),
    )
    .min(1),
  openQuestions: z
    .array(
      z.object({
        id: z.string(),
        question: z.string(),
        context: z.string().default(""),
        blocksTaskIds: z.array(z.string()).default([]),
        options: z
          .array(
            z.object({
              id: z.string(),
              label: z.string(),
              detail: z.string().default(""),
              recommended: z.boolean().default(false),
            }),
          )
          .default([]),
      }),
    )
    .default([]),
});

/**
 * Pull the JSON object out of the planner's final message. Models occasionally
 * wrap it in a fence or add a sentence, so fall back to brace matching.
 */
function extractJson(text: string): unknown {
  const fenced = text.match(/```(?:json)?\s*\n([\s\S]*?)```/);
  const candidates = [fenced?.[1], text].filter(Boolean) as string[];

  for (const candidate of candidates) {
    const trimmed = candidate.trim();
    try {
      return JSON.parse(trimmed);
    } catch {
      // Fall through to brace matching.
    }
    const start = trimmed.indexOf("{");
    const end = trimmed.lastIndexOf("}");
    if (start !== -1 && end > start) {
      try {
        return JSON.parse(trimmed.slice(start, end + 1));
      } catch {
        // Try the next candidate.
      }
    }
  }
  throw new Error("Planner did not return parseable JSON.");
}

export interface PlanRequest {
  planText: string;
  targetDir: string;
  title?: string;
  maxParallel?: number;
}

/**
 * Run the planning pass and return a fully-formed Run (status `planned`).
 * The planner is read-only: it inspects the target directory but writes nothing.
 */
export async function planRun(request: PlanRequest): Promise<Run> {
  const catalog = await getCatalog();

  let finalText = "";
  for await (const message of query({
    prompt: plannerUserPrompt(request.planText, request.targetDir),
    options: {
      cwd: request.targetDir,
      model: PLANNER_MODEL,
      systemPrompt: plannerSystemPrompt(catalog),
      // Read-only: the planner inspects the repo but must not modify it.
      allowedTools: ["Read", "Glob", "Grep"],
      disallowedTools: ["Write", "Edit", "NotebookEdit", "Bash"],
      permissionMode: "dontAsk",
      additionalDirectories: [LIBRARY_ROOT],
      // Ignore the target repo's own agents/settings so planning is reproducible.
      settingSources: [],
      maxTurns: 60,
    },
  })) {
    if (message.type === "result") {
      if (message.subtype !== "success") {
        throw new Error(`Planner failed: ${message.subtype}`);
      }
      finalText = message.result;
    }
  }

  if (!finalText.trim()) throw new Error("Planner returned an empty response.");

  const plan = PlanSchema.parse(extractJson(finalText));

  // Bind the plan to the catalog: an unknown agent is a planning error we want
  // surfaced now, not at dispatch time.
  const agentNames = new Set(catalog.agents.map((a) => a.name));
  const unknown = [...new Set(plan.tasks.map((t) => t.agent))].filter(
    (name) => !agentNames.has(name),
  );
  if (unknown.length > 0) {
    throw new Error(
      `Planner assigned agents that are not in the catalog: ${unknown.join(", ")}`,
    );
  }

  const skillNames = new Set(catalog.skills.map((s) => s.name));
  const now = new Date().toISOString();
  const phaseOrder = new Map(plan.phases.map((p, i) => [p.id, i]));

  return {
    id: randomUUID(),
    title: request.title?.trim() || plan.title,
    targetDir: request.targetDir,
    planText: request.planText,
    status: "planned",
    planningNotes: plan.planningNotes,
    maxParallel: request.maxParallel ?? DEFAULT_MAX_PARALLEL,
    phases: plan.phases.map((p, index) => ({
      id: p.id,
      index,
      name: p.name,
      goal: p.goal,
      parallelSafe: p.parallelSafe,
      parallelRationale: p.parallelRationale,
    })),
    tasks: plan.tasks
      .slice()
      .sort(
        (a, b) => (phaseOrder.get(a.phaseId) ?? 0) - (phaseOrder.get(b.phaseId) ?? 0),
      )
      .map((t) => ({
        id: t.id,
        phaseId: t.phaseId,
        title: t.title,
        intent: t.intent,
        acceptanceCriteria: t.acceptanceCriteria,
        agent: t.agent,
        // Drop hallucinated skill names; the agent still loads its own.
        skills: t.skills.filter((s) => skillNames.has(s)),
        files: t.files,
        dependsOn: t.dependsOn,
        status: "backlog" as const,
        log: [],
      })),
    openQuestions: plan.openQuestions.map((q) => ({
      id: q.id,
      question: q.question,
      context: q.context,
      blocksTaskIds: q.blocksTaskIds,
      options: q.options,
    })),
    createdAt: now,
    updatedAt: now,
  };
}
