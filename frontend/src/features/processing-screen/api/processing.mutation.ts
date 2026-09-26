import { useMutation, useQueryClient } from '@tanstack/react-query';
import { retryJob } from '../../../shared/api-client';
import type { RetryResponse } from '../../../shared/api-client';
import { processingKeys } from './processing.keys';

interface RetryJobParams {
  jobId: string;
  accessToken?: string;
}

export function useRetryJobMutation() {
  const queryClient = useQueryClient();

  return useMutation<RetryResponse, Error, RetryJobParams>({
    mutationFn: ({ jobId, accessToken }) => retryJob(jobId, accessToken),
    onSuccess: (_, { jobId }) => {
      void queryClient.invalidateQueries({ queryKey: processingKeys.job(jobId) });
    },
  });
}
