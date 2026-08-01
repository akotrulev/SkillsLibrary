import path from "node:path";

/**
 * Root of the SkillsLibrary repo. Mission Control lives at
 * <root>/tools/mission-control, so the default is two levels up.
 * Override with MISSION_CONTROL_LIBRARY_ROOT.
 */
export const LIBRARY_ROOT = path.resolve(
  process.env.MISSION_CONTROL_LIBRARY_ROOT ?? path.join(process.cwd(), "..", ".."),
);

/** Where run state is persisted. */
export const DATA_DIR = path.resolve(
  process.env.MISSION_CONTROL_DATA_DIR ?? path.join(process.cwd(), ".data"),
);

export const RUNS_DIR = path.join(DATA_DIR, "runs");

/** Model used for the planner pass. */
export const PLANNER_MODEL = process.env.MISSION_CONTROL_PLANNER_MODEL ?? "claude-opus-5";

/** Default model for implementer agents ('inherit' keeps the agent's own choice). */
export const IMPLEMENTER_MODEL = process.env.MISSION_CONTROL_IMPLEMENTER_MODEL ?? "claude-opus-5";

/** Default concurrency ceiling inside a parallel-safe phase. */
export const DEFAULT_MAX_PARALLEL = Number(process.env.MISSION_CONTROL_MAX_PARALLEL ?? 3);

/** Max log entries retained per task (keeps run files bounded). */
export const MAX_LOG_ENTRIES = 400;

/**
 * Top-level folders in the library that are agent/skill sources.
 * `tools/` (this app) and vendored/meta content are excluded.
 */
export const CATALOG_EXCLUDE_DIRS = new Set([
  "node_modules",
  ".git",
  ".next",
  "tools",
  "docs",
  "extras",
  ".claude-plugin",
]);
