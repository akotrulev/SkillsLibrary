import type { z } from 'zod';
import type { HealthSchema } from './health.schema.js';

export { HealthSchema } from './health.schema.js';
export type HealthDto = z.infer<typeof HealthSchema>;
