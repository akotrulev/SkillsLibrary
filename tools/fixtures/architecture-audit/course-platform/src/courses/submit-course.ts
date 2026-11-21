import { quote } from '../pricing';
import { MIN_SUMMARY_LENGTH } from './course';
import type { Course } from './course';
import type { CourseRepository } from './course-repository';

const MAX_TITLE_LENGTH = 120;

export type SubmitCourseInput = {
  readonly authorId: string;
  readonly title: string;
  readonly summary: string;
  readonly lessonTitles: readonly string[];
  readonly listPriceCents: number;
  readonly discountCode?: string;
};

export type SubmitCourseResult =
  | { readonly status: 'saved'; readonly course: Course }
  | { readonly status: 'rejected'; readonly reasons: readonly string[] };

export async function submitCourse(
  repository: CourseRepository,
  input: SubmitCourseInput,
): Promise<SubmitCourseResult> {
  const reasons: string[] = [];
  const title = input.title.trim();
  const summary = input.summary.trim();
  if (title.length === 0) {
    reasons.push('title is required');
  }
  if (title.length > MAX_TITLE_LENGTH) {
    reasons.push(`title must be at most ${MAX_TITLE_LENGTH} characters`);
  }
  if (summary.length < MIN_SUMMARY_LENGTH) {
    reasons.push(`summary must be at least ${MIN_SUMMARY_LENGTH} characters`);
  }
  if (input.lessonTitles.length === 0) {
    reasons.push('a course needs at least one lesson');
  }
  if (input.lessonTitles.some((lessonTitle) => lessonTitle.trim().length === 0)) {
    reasons.push('lesson titles must not be blank');
  }
  if (!Number.isInteger(input.listPriceCents) || input.listPriceCents < 0) {
    reasons.push('list price must be a whole number of cents, zero or more');
  }
  if (reasons.length > 0) {
    return { status: 'rejected', reasons };
  }
  const priceCents = quote(input.listPriceCents, input.discountCode);
  const course: Course = {
    id: await repository.nextId(),
    authorId: input.authorId,
    title,
    summary,
    lessonTitles: [...input.lessonTitles],
    priceCents,
  };
  await repository.save(course);
  return { status: 'saved', course };
}
