import { useMutation } from '@tanstack/react-query';
import { uploadVideoWithProgress } from '../../../shared/api-client';
import type { Access } from '../../../shared/api-client';

interface UploadVideoParams {
  file: File;
  onProgress?: (percent: number) => void;
  uploadKey?: string;
}

export function useUploadVideoMutation() {
  return useMutation<Access, Error, UploadVideoParams>({
    mutationFn: ({ file, onProgress, uploadKey }) =>
      uploadVideoWithProgress(file, { onProgress, uploadKey }),
  });
}
