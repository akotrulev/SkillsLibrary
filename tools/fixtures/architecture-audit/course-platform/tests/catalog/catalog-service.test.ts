import { beforeEach, describe, expect, it } from 'vitest';
import { CatalogService } from '../../src/catalog';
import type { CatalogRow } from '../../src/catalog';

const publishedRow: CatalogRow = {
  course_id: 'course-1',
  title: 'Intro to Sourdough',
  price_cents: 10800,
  is_published: true,
};

const draftRow: CatalogRow = {
  course_id: 'course-2',
  title: 'Advanced Rye',
  price_cents: 5400,
  is_published: false,
};

describe('CatalogService', () => {
  let catalog: CatalogService;

  beforeEach(async () => {
    catalog = new CatalogService(async () => [publishedRow, draftRow]);
    await catalog.refresh();
  });

  it('Should_ListOnlyPublishedCourses_When_CatalogIsRefreshed', () => {
    expect(catalog.list().map((entry) => entry.courseId)).toEqual(['course-1']);
  });

  it('Should_FindEntryWithCamelCaseFields_When_CourseIsKnown', () => {
    expect(catalog.find('course-2')).toEqual({
      courseId: 'course-2',
      title: 'Advanced Rye',
      priceCents: 5400,
      published: false,
    });
  });

  it('Should_ReturnUndefined_When_CourseIsUnknown', () => {
    expect(catalog.find('course-9')).toBeUndefined();
  });
});
