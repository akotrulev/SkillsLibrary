export type StudentProgress = {
  readonly learnerId: string;
  readonly courseId: string;
  readonly completedLessons: number;
  readonly totalLessons: number;
};

export function completionPercent(progress: StudentProgress): number {
  if (progress.totalLessons === 0) {
    return 0;
  }
  return Math.floor((progress.completedLessons / progress.totalLessons) * 100);
}

export function withLessonCompleted(progress: StudentProgress): StudentProgress {
  if (progress.completedLessons >= progress.totalLessons) {
    return progress;
  }
  return { ...progress, completedLessons: progress.completedLessons + 1 };
}
