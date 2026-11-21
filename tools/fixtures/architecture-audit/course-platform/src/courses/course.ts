export const MIN_SUMMARY_LENGTH = 20;

export type Course = {
  readonly id: string;
  readonly authorId: string;
  readonly title: string;
  readonly summary: string;
  readonly lessonTitles: readonly string[];
  readonly priceCents: number;
  readonly duplicatedFrom?: string;
};
