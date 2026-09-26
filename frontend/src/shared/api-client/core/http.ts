import { apiPath } from '../../config';
import type { ZodType } from 'zod';
import type { AxiosRequestConfig, AxiosResponse } from 'axios';
import { apiClient, ApiError, ApiContractError } from './client';

export { apiClient, ApiError, ApiContractError };

export interface ApiRequestOptions extends AxiosRequestConfig {
  accessToken?: string;
}

export function jobPath(jobId: string, suffix = ''): string {
  return apiPath(`/jobs/${encodeURIComponent(jobId)}${suffix}`);
}

export function parseContract<T>(schema: ZodType<T>, value: unknown, label: string): T {
  const parsed = schema.safeParse(value);
  if (!parsed.success) {
    throw new ApiContractError(`The backend returned an invalid ${label} response.`, {
      cause: parsed.error,
    });
  }
  return parsed.data;
}

/**
 * Execute an API request using Axios and validate the response payload with Zod.
 */
export async function apiRequest<T>(
  path: string,
  schema: ZodType<T>,
  options: ApiRequestOptions = {},
  label = 'API'
): Promise<T> {
  const { accessToken, method = 'GET', headers, ...restOptions } = options;

  const requestHeaders: Record<string, string> = {};
  if (headers) {
    Object.assign(requestHeaders, headers);
  }
  if (accessToken) {
    requestHeaders.Authorization = `Bearer ${accessToken}`;
  }

  const response: AxiosResponse<unknown> = await apiClient.request({
    url: path,
    method,
    headers: requestHeaders,
    ...restOptions,
  });

  return parseContract(schema, response.data, label);
}
