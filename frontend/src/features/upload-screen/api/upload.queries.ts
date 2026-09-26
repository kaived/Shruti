import { useQuery } from '@tanstack/react-query';
import { fetchCapabilities } from '../../../shared/api-client';
import { uploadKeys } from './upload.keys';

export function useCapabilitiesQuery() {
  return useQuery({
    queryKey: uploadKeys.capabilities(),
    queryFn: fetchCapabilities,
    staleTime: 1000 * 60 * 10, // 10 minutes
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
