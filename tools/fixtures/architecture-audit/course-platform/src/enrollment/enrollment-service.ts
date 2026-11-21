import type { Enrollment } from './enrollment';
import type { EnrollmentRepository } from './enrollment-repository';

export class EnrollmentService {
  constructor(private readonly repository: EnrollmentRepository) {}

  nextId(): Promise<string> {
    return this.repository.nextId();
  }

  create(enrollment: Enrollment): Promise<void> {
    return this.repository.save(enrollment);
  }

  findActive(learnerId: string, courseId: string): Promise<Enrollment | undefined> {
    return this.repository.findActive(learnerId, courseId);
  }

  listForLearner(learnerId: string): Promise<readonly Enrollment[]> {
    return this.repository.listForLearner(learnerId);
  }
}
