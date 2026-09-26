import { useQuery } from '@tanstack/react-query';
import { fetchJobStatus } from '../../../shared/api-client';
import { processingKeys } from './processing.keys';

const TERMINAL_STATES = new Set(['completed', 'partial', 'failed', 'blocked']);

export function useJobStatusQuery(jobId: string | null, accessToken?: string) {
  return useQuery({
    queryKey: processingKeys.job(jobId || ''),
    queryFn: () => fetchJobStatus(jobId!, accessToken),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      if (state && TERMINAL_STATES.has(state)) {
        return false;
      }
      return 1800; // Poll every 1.8 seconds while processing
    },
  });
}
