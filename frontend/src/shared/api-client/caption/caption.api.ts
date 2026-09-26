import { API_BASE_URL } from '../../config';
import { ArtifactNameSchema, ResultsSchema } from '../core/contracts';
import type { ArtifactName, Results } from '../core/contracts';
import { apiClient, apiRequest, jobPath } from '../core/http';

export async function fetchJobResults(jobId: string, accessToken?: string): Promise<Results> {
  return apiRequest(
    jobPath(jobId, '/results'),
    ResultsSchema,
    { accessToken, headers: { 'Cache-Control': 'no-cache' } },
    'job results'
  );
}

/**
 * Absolute media URL for <video>. The element cannot send a bearer header and a
 * cross-site cookie is not sent, so the job token travels as a query parameter.
 */
export function getJobMediaUrl(jobId: string, accessToken?: string): string {
  const query = accessToken ? `?access_token=${encodeURIComponent(accessToken)}` : '';
  return `${API_BASE_URL}${jobPath(jobId, '/media')}${query}`;
}

export function getJobArtifactUrl(jobId: string, name: ArtifactName): string {
  return jobPath(jobId, `/artifacts/${encodeURIComponent(name)}`);
}

/**
 * Downloads a generated artifact (e.g. .vtt, .srt, .json) as a binary Blob via Axios.
 */
export async function fetchJobArtifact(
  jobId: string,
  name: ArtifactName,
  accessToken?: string
): Promise<Blob> {
  const artifactName = ArtifactNameSchema.parse(name);
  const response = await apiClient.get<Blob>(getJobArtifactUrl(jobId, artifactName), {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
    responseType: 'blob',
  });
  return response.data;
}
