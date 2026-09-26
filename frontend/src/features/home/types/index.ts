import type { Dispatch, SetStateAction } from 'react';
import { z } from 'zod';
import type { Access } from '../../upload-screen';
import { HomeStateSchema, ScreenViewSchema } from '../validation';

export type ScreenView = z.infer<typeof ScreenViewSchema>;
export type HomeState = z.infer<typeof HomeStateSchema>;

export interface HomePageProps {
  jobs: Access[];
  setJobs: Dispatch<SetStateAction<Access[]>>;
  selectedJobId: string | null;
  setSelectedJobId: Dispatch<SetStateAction<string | null>>;
  onNewVideo: () => void;
  onUploadError?: (error: string) => void;
  pendingFile?: File | null;
  onClearPendingFile?: () => void;
}
