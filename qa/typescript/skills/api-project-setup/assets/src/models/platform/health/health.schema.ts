import { z } from 'zod';

export const HealthSchema = z
  .object({
    status: z.string(),
  })
  .strict();
