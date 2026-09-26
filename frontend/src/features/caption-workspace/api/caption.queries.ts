import { useQuery } from '@tanstack/react-query';
import { fetchJobResults } from '../../../shared/api-client';
import { workspaceKeys } from './caption.keys';

export function useJobResultsQuery(jobId: string | null, accessToken?: string, enabled = true) {
  return useQuery({
    queryKey: workspaceKeys.results(jobId || ''),
    queryFn: () => fetchJobResults(jobId!, accessToken),
    enabled: Boolean(jobId) && enabled,
    staleTime: 1000 * 60 * 30, // Results are immutable drafts, cache for 30 min
    retry: 1,
  });
}
