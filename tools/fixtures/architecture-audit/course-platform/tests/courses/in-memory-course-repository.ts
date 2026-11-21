import type { Course, CourseRepository } from '../../src/courses';

export class InMemoryCourseRepository implements CourseRepository {
  readonly saved: Course[] = [];

  async nextId(): Promise<string> {
    return `course-${this.saved.length + 1}`;
  }

  async save(course: Course): Promise<void> {
    this.saved.push(course);
  }

  async findById(id: string): Promise<Course | undefined> {
    return this.saved.find((course) => course.id === id);
  }
}
