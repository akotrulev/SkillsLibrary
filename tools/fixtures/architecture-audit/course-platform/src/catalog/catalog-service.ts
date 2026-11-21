import { catalogCache } from './catalog-cache';
import type { CatalogEntry } from './catalog-entry';
import type { CatalogRow } from './catalog-row';

export type CatalogSource = () => Promise<readonly CatalogRow[]>;

function toEntry(row: CatalogRow): CatalogEntry {
  return {
    courseId: row.course_id,
    title: row.title,
    priceCents: row.price_cents,
    published: row.is_published,
  };
}

export class CatalogService {
  constructor(private readonly source: CatalogSource) {}

  async refresh(): Promise<void> {
    const rows = await this.source();
    catalogCache.clear();
    for (const row of rows) {
      catalogCache.set(row.course_id, row);
    }
  }

  find(courseId: string): CatalogEntry | undefined {
    const row = catalogCache.get(courseId);
    return row === undefined ? undefined : toEntry(row);
  }

  list(): readonly CatalogEntry[] {
    return [...catalogCache.values()].filter((row) => row.is_published).map(toEntry);
  }
}
