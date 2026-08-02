import fs from "node:fs/promises";
import path from "node:path";
import { CATALOG_EXCLUDE_DIRS, DATA_DIR, LIBRARY_ROOT } from "./config";
import { parseFrontmatter, parseList } from "./frontmatter";
import type { Catalog, CatalogAgent, CatalogSkill } from "./types";

let cached: Catalog | null = null;

/**
 * Cap on a single file read attempt, so one wedged path cannot hang indexing.
 * Generous because the library can live on a slow or network-backed volume.
 */
const READ_TIMEOUT_MS = 20_000;
/** Attempts per file before giving up. Transient slow reads are common here. */
const READ_ATTEMPTS = 3;
/**
 * Files read concurrently. Deliberately low: on slow volumes a wide fan-out
 * makes every read contend and pushes them all toward the timeout.
 */
const READ_CONCURRENCY = 4;

const CACHE_FILE = path.join(DATA_DIR, "catalog.json");

interface Candidate {
  full: string;
  relPath: string;
  domain: string;
  isAgent: boolean;
}

/**
 * Phase 1 — collect candidate paths. Agent definitions live in `*​/agents/*.md`;
 * skills are `**​/SKILL.md`. No file contents are read here.
 */
async function collect(dir: string, out: Candidate[]): Promise<void> {
  let entries;
  try {
    entries = await fs.readdir(dir, { withFileTypes: true });
  } catch {
    return;
  }

  for (const entry of entries) {
    const full = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      if (CATALOG_EXCLUDE_DIRS.has(entry.name) || entry.name.startsWith(".")) continue;
      await collect(full, out);
      continue;
    }
    if (!entry.isFile() || !entry.name.endsWith(".md")) continue;

    const isAgent = path.basename(dir) === "agents";
    const isSkill = entry.name === "SKILL.md";
    if (!isAgent && !isSkill) continue;

    const relPath = path.relative(LIBRARY_ROOT, full);
    out.push({ full, relPath, domain: relPath.split(path.sep)[0] ?? "", isAgent });
  }
}

async function readOnce(file: string): Promise<string | null> {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), READ_TIMEOUT_MS);
  try {
    return await fs.readFile(file, { encoding: "utf8", signal: ac.signal });
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Read with retries. A dropped entry means an agent silently disappears from
 * the planner's catalog, so a slow read must not be treated as "absent".
 */
async function readFileResilient(file: string): Promise<string | null> {
  for (let attempt = 1; attempt <= READ_ATTEMPTS; attempt++) {
    const content = await readOnce(file);
    if (content !== null) return content;
    if (attempt < READ_ATTEMPTS) {
      await new Promise((resolve) => setTimeout(resolve, 150 * attempt));
    }
  }
  return null;
}

/** Run `worker` over `items` with a bounded number of in-flight promises. */
async function mapLimit<T, R>(
  items: T[],
  limit: number,
  worker: (item: T) => Promise<R>,
): Promise<R[]> {
  const results = new Array<R>(items.length);
  let next = 0;
  const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
    for (;;) {
      const i = next++;
      if (i >= items.length) return;
      results[i] = await worker(items[i]);
    }
  });
  await Promise.all(runners);
  return results;
}

export async function buildCatalog(): Promise<Catalog> {
  const candidates: Candidate[] = [];
  await collect(LIBRARY_ROOT, candidates);

  const agents: CatalogAgent[] = [];
  const skills: CatalogSkill[] = [];
  const unreadable: string[] = [];
  const malformed: string[] = [];

  await mapLimit(candidates, READ_CONCURRENCY, async (c) => {
    const source = await readFileResilient(c.full);
    if (source === null) {
      unreadable.push(c.relPath);
      return;
    }

    const { data } = parseFrontmatter(source);
    const name = data.name?.trim() ?? "";
    if (!name) {
      // Readable but unusable: no frontmatter `name` means nothing can address
      // it. Tracked so an authoring slip is visible instead of a silent gap.
      malformed.push(c.relPath);
      return;
    }
    const description = data.description?.trim() ?? "";

    if (c.isAgent) {
      agents.push({
        name,
        description,
        path: c.full,
        relPath: c.relPath,
        domain: c.domain,
        tools: parseList(data.tools),
      });
    } else {
      skills.push({
        name,
        description,
        path: c.full,
        relPath: c.relPath,
        domain: c.domain,
      });
    }
  });

  agents.sort((a, b) => a.name.localeCompare(b.name));
  skills.sort((a, b) => a.name.localeCompare(b.name));

  if (malformed.length > 0) {
    console.warn(
      `[catalog] ${malformed.length} file(s) have no frontmatter \`name\` and were skipped:\n  ${malformed.join("\n  ")}`,
    );
  }

  if (unreadable.length > 0) {
    // Visible rather than silent: a missing agent would otherwise look to the
    // planner like an agent that simply does not exist.
    console.warn(
      `[catalog] ${unreadable.length} file(s) could not be read after ${READ_ATTEMPTS} attempts:\n  ${unreadable.join("\n  ")}`,
    );
  }

  return {
    libraryRoot: LIBRARY_ROOT,
    agents,
    skills,
    candidateCount: candidates.length,
    unreadable,
    malformed,
    indexedAt: new Date().toISOString(),
  };
}

async function readCacheFile(): Promise<Catalog | null> {
  try {
    const parsed = JSON.parse(await fs.readFile(CACHE_FILE, "utf8")) as Catalog;
    if (parsed.libraryRoot !== LIBRARY_ROOT) return null;
    if (!parsed.agents?.length) return null;
    // A cache written before a field existed must not surface as undefined.
    return { ...parsed, unreadable: parsed.unreadable ?? [], malformed: parsed.malformed ?? [] };
  } catch {
    return null;
  }
}

async function writeCacheFile(catalog: Catalog): Promise<void> {
  try {
    await fs.mkdir(DATA_DIR, { recursive: true });
    await fs.writeFile(CACHE_FILE, JSON.stringify(catalog, null, 2), "utf8");
  } catch {
    // A non-writable data dir must not break indexing.
  }
}

/**
 * Catalog accessor. Serves the in-memory copy, then the on-disk cache, and
 * only rebuilds when neither is available (or `force` is set).
 */
export async function getCatalog(force = false): Promise<Catalog> {
  if (cached && !force) return cached;

  if (!force) {
    const fromDisk = await readCacheFile();
    if (fromDisk) {
      cached = fromDisk;
      return cached;
    }
  }

  cached = await buildCatalog();
  await writeCacheFile(cached);
  return cached;
}

export function findAgent(catalog: Catalog, name: string): CatalogAgent | undefined {
  return catalog.agents.find((a) => a.name === name);
}

export function findSkill(catalog: Catalog, name: string): CatalogSkill | undefined {
  return catalog.skills.find((s) => s.name === name);
}

/**
 * Compact catalog rendering for the planner prompt. Agent descriptions encode
 * when to use each agent, so they are kept (trimmed); skills are names only.
 */
export function renderCatalogForPlanner(catalog: Catalog): string {
  const trim = (s: string, n: number) => (s.length > n ? `${s.slice(0, n)}…` : s);

  const agents = catalog.agents
    .map((a) => `- ${a.name} [${a.domain}] — ${trim(a.description, 400)}`)
    .join("\n");

  const byDomain = new Map<string, CatalogSkill[]>();
  for (const s of catalog.skills) {
    const list = byDomain.get(s.domain) ?? [];
    list.push(s);
    byDomain.set(s.domain, list);
  }
  const skills = [...byDomain.entries()]
    .map(([domain, list]) => `### ${domain}\n${list.map((s) => s.name).join(", ")}`)
    .join("\n\n");

  return [
    `## Available agents (${catalog.agents.length})`,
    "",
    agents,
    "",
    `## Available skills (${catalog.skills.length}, names only)`,
    "",
    skills,
  ].join("\n");
}
