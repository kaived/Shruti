import { ArtifactNameSchema, ResultsSchema } from '../core/contracts';
import type { ArtifactName, Results } from '../core/contracts';
import { apiFetch, apiRequest, ApiError, errorMessageFromResponse, jobPath } from '../core/http';

export async function fetchJobResults(jobId: string, accessToken?: string): Promise<Results> {
  return apiRequest(
    jobPath(jobId, '/results'),
    ResultsSchema,
    { accessToken, cache: 'no-store' },
    'job results'
  );
}

export function getJobMediaUrl(jobId: string): string {
  return jobPath(jobId, '/media');
}

export function getJobArtifactUrl(jobId: string, name: ArtifactName): string {
  return jobPath(jobId, `/artifacts/${encodeURIComponent(name)}`);
}

export async function fetchJobArtifact(
  jobId: string,
  name: ArtifactName,
  accessToken?: string
): Promise<Blob> {
  const artifactName = ArtifactNameSchema.parse(name);
  const response = await apiFetch(getJobArtifactUrl(jobId, artifactName), { accessToken });
  if (!response.ok) {
    throw new ApiError(
      await errorMessageFromResponse(response, `Failed to download ${artifactName}.`),
      response.status
    );
  }
  return response.blob();
}
