import { JobSchema, RetryResponseSchema } from '../core/contracts';
import type { Job, RetryResponse } from '../core/contracts';
import { apiRequest, jobPath } from '../core/http';

export async function fetchJobStatus(jobId: string, accessToken?: string): Promise<Job> {
  return apiRequest(
    jobPath(jobId),
    JobSchema,
    { accessToken, cache: 'no-store' },
    'job status'
  );
}

export async function retryJob(jobId: string, accessToken?: string): Promise<RetryResponse> {
  return apiRequest(
    jobPath(jobId, '/retry'),
    RetryResponseSchema,
    { method: 'POST', accessToken },
    'job retry'
  );
}
