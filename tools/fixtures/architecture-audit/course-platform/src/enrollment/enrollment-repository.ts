import type { Enrollment } from './enrollment';

export type EnrollmentRepository = {
  nextId(): Promise<string>;
  save(enrollment: Enrollment): Promise<void>;
  findActive(learnerId: string, courseId: string): Promise<Enrollment | undefined>;
  listForLearner(learnerId: string): Promise<readonly Enrollment[]>;
};
