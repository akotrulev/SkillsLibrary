export type EnrollmentStatus = 'active' | 'completed';

export type Enrollment = {
  readonly id: string;
  readonly learnerId: string;
  readonly courseId: string;
  readonly status: EnrollmentStatus;
  readonly paymentReference: string;
};
