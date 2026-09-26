import { z } from 'zod';

export const ScreenViewSchema = z.enum(['upload', 'processing', 'workspace']);

export const HomeStateSchema = z.object({
  selectedJobId: z.string().nullable(),
  uploadProgress: z.number().min(0).max(100).optional(),
  activeError: z.string().optional(),
});
