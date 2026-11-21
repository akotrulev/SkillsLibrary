import type { Course } from './course';
import type { CourseRepository } from './course-repository';

export async function findCourse(
  repository: CourseRepository,
  id: string,
): Promise<Course | undefined> {
  const trimmed = id.trim();
  if (trimmed.length === 0) {
    throw new RangeError('id must not be blank');
  }
  return repository.findById(trimmed);
}
