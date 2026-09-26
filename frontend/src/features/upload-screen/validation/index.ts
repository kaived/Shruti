import { z } from 'zod';

export { AccessSchema, CapabilitiesSchema } from '../../../shared/api-client/core/contracts';

export const VideoMetadataSchema = z.object({
  duration: z.number().nullable(),
  thumbnailUrl: z.string().nullable(),
});
