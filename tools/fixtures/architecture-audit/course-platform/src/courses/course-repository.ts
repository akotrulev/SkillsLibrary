import type { Course } from './course';

export type CourseRepository = {
  nextId(): Promise<string>;
  save(course: Course): Promise<void>;
  findById(id: string): Promise<Course | undefined>;
};
