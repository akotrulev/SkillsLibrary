import { beforeEach, describe, expect, it } from 'vitest';
import { submitCourse } from '../../src/courses';
import type { SubmitCourseInput } from '../../src/courses';
import { InMemoryCourseRepository } from './in-memory-course-repository';

const validInput: SubmitCourseInput = {
  authorId: 'author-1',
  title: 'Intro to Sourdough',
  summary: 'Bake a first loaf from scratch in a weekend.',
  lessonTitles: ['Flour and water', 'Shaping'],
  listPriceCents: 10000,
};

describe('submitCourse', () => {
  let repository: InMemoryCourseRepository;

  beforeEach(() => {
    repository = new InMemoryCourseRepository();
  });

  it('Should_SaveCourse_When_InputIsValid', async () => {
    const result = await submitCourse(repository, validInput);

    expect(result).toMatchObject({ status: 'saved', course: { title: 'Intro to Sourdough' } });
  });

  it('Should_PersistCourse_When_InputIsValid', async () => {
    await submitCourse(repository, validInput);

    expect(repository.saved).toHaveLength(1);
  });

  it('Should_ApplyDiscountAndTax_When_CodeIsLaunch10', async () => {
    const result = await submitCourse(repository, { ...validInput, discountCode: 'LAUNCH10' });

    expect(result).toMatchObject({ status: 'saved', course: { priceCents: 10800 } });
  });

  it('Should_RejectCourse_When_TitleIsOver120Characters', async () => {
    const result = await submitCourse(repository, { ...validInput, title: 'a'.repeat(121) });

    expect(result).toEqual({
      status: 'rejected',
      reasons: ['title must be at most 120 characters'],
    });
  });

  it('Should_RejectCourse_When_SummaryIsTooShort', async () => {
    const result = await submitCourse(repository, { ...validInput, summary: 'Too short' });

    expect(result).toEqual({
      status: 'rejected',
      reasons: ['summary must be at least 20 characters'],
    });
  });

  it('Should_RejectCourse_When_NoLessonIsGiven', async () => {
    const result = await submitCourse(repository, { ...validInput, lessonTitles: [] });

    expect(result).toEqual({
      status: 'rejected',
      reasons: ['a course needs at least one lesson'],
    });
  });

  it('Should_NotPersistCourse_When_InputIsRejected', async () => {
    await submitCourse(repository, { ...validInput, title: '   ' });

    expect(repository.saved).toHaveLength(0);
  });
});
