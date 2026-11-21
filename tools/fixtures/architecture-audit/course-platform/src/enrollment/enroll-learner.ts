import type { CatalogService } from '../catalog';
import type { PaymentGateway } from '../payments';
import type { Enrollment } from './enrollment';
import type { EnrollmentService } from './enrollment-service';

export type EnrollLearnerInput = {
  readonly learnerId: string;
  readonly courseId: string;
};

export type EnrollLearnerResult =
  | { readonly status: 'enrolled'; readonly enrollment: Enrollment }
  | { readonly status: 'course-unavailable' }
  | { readonly status: 'already-enrolled' }
  | { readonly status: 'payment-declined' };

export async function enrollLearner(
  enrollments: EnrollmentService,
  catalog: CatalogService,
  gateway: PaymentGateway,
  input: EnrollLearnerInput,
): Promise<EnrollLearnerResult> {
  const learnerId = input.learnerId.trim();
  if (learnerId.length === 0) {
    throw new RangeError('id must not be blank');
  }
  const entry = catalog.find(input.courseId);
  if (entry === undefined || !entry.published) {
    return { status: 'course-unavailable' };
  }
  const existing = await enrollments.findActive(learnerId, entry.courseId);
  if (existing !== undefined) {
    return { status: 'already-enrolled' };
  }
  const id = await enrollments.nextId();
  const charge = await gateway.charge({
    learnerId,
    amountCents: entry.priceCents,
    idempotencyKey: id,
  });
  if (charge.status === 'declined') {
    return { status: 'payment-declined' };
  }
  const enrollment: Enrollment = {
    id,
    learnerId,
    courseId: entry.courseId,
    status: 'active',
    paymentReference: charge.reference,
  };
  await enrollments.create(enrollment);
  return { status: 'enrolled', enrollment };
}
