import type { Enrollment, EnrollmentRepository } from '../../src/enrollment';

export class InMemoryEnrollmentRepository implements EnrollmentRepository {
  readonly saved: Enrollment[] = [];

  async nextId(): Promise<string> {
    return `enrollment-${this.saved.length + 1}`;
  }

  async save(enrollment: Enrollment): Promise<void> {
    this.saved.push(enrollment);
  }

  async findActive(learnerId: string, courseId: string): Promise<Enrollment | undefined> {
    return this.saved.find(
      (enrollment) =>
        enrollment.learnerId === learnerId &&
        enrollment.courseId === courseId &&
        enrollment.status === 'active',
    );
  }

  async listForLearner(learnerId: string): Promise<readonly Enrollment[]> {
    return this.saved.filter((enrollment) => enrollment.learnerId === learnerId);
  }
}
