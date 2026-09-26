import { useQuery } from '@tanstack/react-query';
import { fetchJobResults, fetchJobArtifact } from '../../../shared/api-client';
import type { ArtifactName } from '../../../shared/api-client';
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

export function useJobArtifactQuery(
  jobId: string | null,
  name: ArtifactName,
  accessToken?: string,
  enabled = true
) {
  return useQuery({
    queryKey: workspaceKeys.artifact(jobId || '', name),
    queryFn: () => fetchJobArtifact(jobId!, name, accessToken),
    enabled: Boolean(jobId) && enabled,
    staleTime: 1000 * 60 * 30,
    retry: 1,
  });
}
