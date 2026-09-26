import { z } from 'zod';
import { AccessSchema, CapabilitiesSchema, VideoMetadataSchema } from '../validation';

export type Capabilities = z.infer<typeof CapabilitiesSchema>;
export type Access = z.infer<typeof AccessSchema>;
export type VideoMetadata = z.infer<typeof VideoMetadataSchema>;

export interface UploadPageProps {
  capabilities: Capabilities | null;
  onStartUpload: (file: File, uploadKey?: string) => void;
  isUploading: boolean;
  uploadProgress?: number;
  errorMessage?: string;
  initialFile?: File | null;
}
