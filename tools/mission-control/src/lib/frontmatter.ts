/**
 * Minimal frontmatter reader for this library's agent/skill markdown.
 *
 * Why not a YAML engine: these files write `description:` as a long, unquoted
 * single-line value that routinely contains colons, quotes, backticks and
 * commas (e.g. `Triggers: "scaffold a Result type in TS"`). That is not valid
 * YAML — js-yaml both rejects it ("incomplete explicit mapping pair") and, on
 * the longer descriptions, backtracks for tens of seconds per file.
 *
 * The real format is simpler than YAML and entirely regular:
 *   ---
 *   key: everything up to end of line, colons and all
 *   key2: ...
 *   ---
 * A continuation line (no `key:` prefix) is appended to the previous value.
 */

export interface Frontmatter {
  data: Record<string, string>;
  body: string;
}

const DELIMITER = "---";
/** `key:` at line start — keys are simple identifiers in this library. */
const KEY_LINE = /^([A-Za-z_][A-Za-z0-9_-]*):\s?(.*)$/;

export function parseFrontmatter(source: string): Frontmatter {
  // Tolerate a BOM and leading blank lines before the opening delimiter.
  const text = source.replace(/^﻿/, "");
  const lines = text.split(/\r?\n/);

  let i = 0;
  while (i < lines.length && lines[i].trim() === "") i++;
  if (lines[i]?.trim() !== DELIMITER) return { data: {}, body: source };

  const start = i + 1;
  let end = -1;
  for (let j = start; j < lines.length; j++) {
    if (lines[j].trim() === DELIMITER) {
      end = j;
      break;
    }
  }
  if (end === -1) return { data: {}, body: source }; // Unterminated block.

  const data: Record<string, string> = {};
  let lastKey: string | null = null;

  for (let j = start; j < end; j++) {
    const line = lines[j];
    if (line.trim() === "") {
      lastKey = null;
      continue;
    }
    const match = KEY_LINE.exec(line);
    if (match) {
      lastKey = match[1];
      data[lastKey] = stripQuotes(match[2].trim());
    } else if (lastKey) {
      // Continuation of the previous value.
      data[lastKey] = `${data[lastKey]} ${line.trim()}`.trim();
    }
  }

  return { data, body: lines.slice(end + 1).join("\n") };
}

/** Strip a single layer of matching wrapping quotes, if present. */
function stripQuotes(value: string): string {
  if (value.length >= 2) {
    const first = value[0];
    const last = value[value.length - 1];
    if ((first === '"' || first === "'") && first === last) return value.slice(1, -1);
  }
  return value;
}

/** Split a comma-separated frontmatter list (e.g. `tools:`). */
export function parseList(value: string | undefined): string[] | undefined {
  if (!value) return undefined;
  const items = value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
  return items.length > 0 ? items : undefined;
}
