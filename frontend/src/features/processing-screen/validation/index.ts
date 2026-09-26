import { z } from 'zod';

export { JobMediaSchema, JobSchema } from '../../../shared/api-client/core/contracts';

export const StageConfigSchema = z.object({
  key: z.string(),
  label: z.string(),
  subtext: z.string(),
});
