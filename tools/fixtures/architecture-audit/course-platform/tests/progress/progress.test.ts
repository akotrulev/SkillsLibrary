import { describe, expect, it } from 'vitest';
import { completionPercent, withLessonCompleted } from '../../src/progress';
import type { StudentProgress } from '../../src/progress';

const halfway: StudentProgress = {
  learnerId: 'learner-1',
  courseId: 'course-1',
  completedLessons: 1,
  totalLessons: 2,
};

describe('progress', () => {
  it('Should_ReturnFifty_When_HalfTheLessonsAreCompleted', () => {
    expect(completionPercent(halfway)).toBe(50);
  });

  it('Should_ReturnZero_When_CourseHasNoLessons', () => {
    expect(completionPercent({ ...halfway, completedLessons: 0, totalLessons: 0 })).toBe(0);
  });

  it('Should_CountOneMoreLesson_When_LessonIsCompleted', () => {
    expect(withLessonCompleted(halfway).completedLessons).toBe(2);
  });

  it('Should_StayAtTotal_When_AllLessonsAreCompleted', () => {
    expect(withLessonCompleted({ ...halfway, completedLessons: 2 }).completedLessons).toBe(2);
  });
});
