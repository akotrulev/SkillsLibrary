/**
 * Core domain types for Mission Control.
 *
 * A Run is one plan executed end-to-end against one target directory.
 * A Run has ordered Phases; a Phase has Tasks. Phases always run in order.
 * Within a phase, tasks run sequentially unless the phase is marked parallel-safe.
 */

export type TaskStatus =
  | "backlog" // planned, phase not reached yet
  | "ready" // phase active, dependencies met, not yet dispatched
  | "in_progress" // an implementer agent is running
  | "review" // agent finished, awaiting human acknowledgement
  | "done"
  | "blocked" // failed, or waiting on an unanswered open question
  | "skipped";

export type RunStatus =
  | "planning"
  | "planned" // plan parsed, awaiting start (and possibly question answers)
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";

/** One entry from the SkillsLibrary catalog. */
export interface CatalogAgent {
  /** Frontmatter `name`, e.g. "be-node". */
  name: string;
  description: string;
  /** Absolute path to the agent markdown file. */
  path: string;
  /** Repo-relative path, e.g. "backend/node/agents/be-node.md". */
  relPath: string;
  /** Top-level domain folder, e.g. "backend". */
  domain: string;
  /** Tools declared in frontmatter, if any. */
  tools?: string[];
}

export interface CatalogSkill {
  name: string;
  description: string;
  path: string;
  relPath: string;
  domain: string;
}

export interface Catalog {
  libraryRoot: string;
  agents: CatalogAgent[];
  skills: CatalogSkill[];
  /** Total agent/skill files discovered on disk, before reading. */
  candidateCount: number;
  /** Files that could not be read; each is an entry missing from the catalog. */
  unreadable: string[];
  indexedAt: string;
}

/** A question the planner could not resolve on its own. */
export interface OpenQuestion {
  id: string;
  question: string;
  /** Why this matters / what changes based on the answer. */
  context: string;
  options: OpenQuestionOption[];
  /** Task ids that should not run until this is answered. */
  blocksTaskIds: string[];
  /** The selected option id, or free-text if the user typed their own. */
  answer?: { optionId?: string; text: string; answeredAt: string };
}

export interface OpenQuestionOption {
  id: string;
  label: string;
  detail: string;
  /** Planner's pick, surfaced as "(Recommended)". */
  recommended?: boolean;
}

export interface Task {
  id: string;
  phaseId: string;
  title: string;
  /** What the implementer must build — the substance of the task. */
  intent: string;
  /** Concrete acceptance criteria the implementer must satisfy. */
  acceptanceCriteria: string[];
  /** Agent name from the catalog, e.g. "be-node". */
  agent: string;
  /** Skill names from the catalog the agent should load. */
  skills: string[];
  /** Files/dirs the task is expected to touch — used for parallel-safety checks. */
  files: string[];
  /** Task ids that must reach `done` first. */
  dependsOn: string[];
  status: TaskStatus;
  /** Short summary the implementer posts on completion. */
  summary?: string;
  error?: string;
  startedAt?: string;
  finishedAt?: string;
  costUsd?: number;
  /** Rolling log of agent activity, capped in the store. */
  log: TaskLogEntry[];
}

export interface TaskLogEntry {
  at: string;
  kind: "text" | "tool" | "error" | "system";
  text: string;
}

export interface Phase {
  id: string;
  index: number;
  name: string;
  goal: string;
  /**
   * When true, all ready tasks in this phase are dispatched concurrently
   * (bounded by maxParallel). When false, they run one at a time in order.
   */
  parallelSafe: boolean;
  /** Planner's justification for the parallel-safety call — shown in the UI. */
  parallelRationale: string;
}

export interface Run {
  id: string;
  title: string;
  /** Absolute path to the directory the implementers work in. */
  targetDir: string;
  /** The raw plan the user supplied. */
  planText: string;
  status: RunStatus;
  phases: Phase[];
  tasks: Task[];
  openQuestions: OpenQuestion[];
  /** Bounded concurrency for parallel-safe phases. */
  maxParallel: number;
  createdAt: string;
  updatedAt: string;
  error?: string;
  planningNotes?: string;
}

/** Server-sent event payload pushed to the board. */
export type RunEvent =
  | { type: "run:updated"; run: Run }
  | { type: "task:updated"; task: Task }
  | { type: "task:log"; taskId: string; entry: TaskLogEntry }
  | { type: "ping" };
