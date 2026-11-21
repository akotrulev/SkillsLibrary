import { beforeEach, describe, expect, it } from 'vitest';
import { CatalogService } from '../../src/catalog';
import type { CatalogRow } from '../../src/catalog';
import { EnrollmentService, enrollLearner } from '../../src/enrollment';
import type { Enrollment } from '../../src/enrollment';
import { PaymentGateway } from '../../src/payments';
import { InMemoryEnrollmentRepository } from './in-memory-enrollment-repository';

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

const activeEnrollment: Enrollment = {
  id: 'enrollment-0',
  learnerId: 'learner-1',
  courseId: 'course-1',
  status: 'active',
  paymentReference: 'ch-0',
};

const approvingGateway = new PaymentGateway({
  charges: { create: async () => ({ id: 'ch-1', status: 'succeeded' as const }) },
});

const decliningGateway = new PaymentGateway({
  charges: { create: async () => ({ id: 'ch-2', status: 'failed' as const }) },
});

describe('enrollLearner', () => {
  let repository: InMemoryEnrollmentRepository;
  let enrollments: EnrollmentService;
  let catalog: CatalogService;

  beforeEach(async () => {
    repository = new InMemoryEnrollmentRepository();
    enrollments = new EnrollmentService(repository);
    catalog = new CatalogService(async () => [publishedRow, draftRow]);
    await catalog.refresh();
  });

  it('Should_Enroll_When_CourseIsPublishedAndPaymentSucceeds', async () => {
    const result = await enrollLearner(enrollments, catalog, approvingGateway, {
      learnerId: 'learner-1',
      courseId: 'course-1',
    });

    expect(result).toMatchObject({
      status: 'enrolled',
      enrollment: { courseId: 'course-1', paymentReference: 'ch-1' },
    });
  });

  it('Should_ReportCourseUnavailable_When_CourseIsNotPublished', async () => {
    const result = await enrollLearner(enrollments, catalog, approvingGateway, {
      learnerId: 'learner-1',
      courseId: 'course-2',
    });

    expect(result).toEqual({ status: 'course-unavailable' });
  });

  it('Should_ReportAlreadyEnrolled_When_LearnerHoldsAnActiveEnrollment', async () => {
    await repository.save(activeEnrollment);

    const result = await enrollLearner(enrollments, catalog, approvingGateway, {
      learnerId: 'learner-1',
      courseId: 'course-1',
    });

    expect(result).toEqual({ status: 'already-enrolled' });
  });

  it('Should_ReportPaymentDeclined_When_GatewayDeclinesTheCharge', async () => {
    const result = await enrollLearner(enrollments, catalog, decliningGateway, {
      learnerId: 'learner-1',
      courseId: 'course-1',
    });

    expect(result).toEqual({ status: 'payment-declined' });
  });

  it('Should_NotPersistEnrollment_When_GatewayDeclinesTheCharge', async () => {
    await enrollLearner(enrollments, catalog, decliningGateway, {
      learnerId: 'learner-1',
      courseId: 'course-1',
    });

    expect(repository.saved).toHaveLength(0);
  });

  it('Should_Throw_When_LearnerIdIsBlank', async () => {
    await expect(
      enrollLearner(enrollments, catalog, approvingGateway, { learnerId: '  ', courseId: 'course-1' }),
    ).rejects.toThrow(RangeError);
  });
});
