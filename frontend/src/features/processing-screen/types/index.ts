import { z } from 'zod';
import { JobSchema, StageConfigSchema } from '../validation';

export type Job = z.infer<typeof JobSchema>;
export type StageConfig = z.infer<typeof StageConfigSchema>;

export interface ProcessingPageProps {
  job: Job | null;
  filename: string;
  uploadProgress?: number;
  onRetry: () => void;
  onCancel?: () => void;
  isRetrying?: boolean;
}
