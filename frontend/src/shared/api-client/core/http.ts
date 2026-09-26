import type { ZodType } from 'zod';

interface ErrorPayload {
  detail?: unknown;
  message?: unknown;
}

export interface ApiRequestOptions extends RequestInit {
  accessToken?: string;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export class ApiContractError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = 'ApiContractError';
  }
}

export function jobPath(jobId: string, suffix = ''): string {
  return `/api/jobs/${encodeURIComponent(jobId)}${suffix}`;
}

export async function errorMessageFromResponse(
  response: Pick<Response, 'status' | 'statusText' | 'json'>,
  fallback: string
): Promise<string> {
  const payload = (await response.json().catch(() => null)) as ErrorPayload | null;
  if (typeof payload?.detail === 'string') return payload.detail;
  if (typeof payload?.message === 'string') return payload.message;
  return response.statusText || fallback;
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

export async function apiFetch(path: string, options: ApiRequestOptions = {}): Promise<Response> {
  const { accessToken, headers: initialHeaders, ...requestOptions } = options;
  const headers = new Headers(initialHeaders);
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);

  return fetch(path, {
    ...requestOptions,
    headers,
    credentials: 'same-origin',
  });
}

export async function apiRequest<T>(
  path: string,
  schema: ZodType<T>,
  options: ApiRequestOptions = {},
  label = 'API'
): Promise<T> {
  const response = await apiFetch(path, options);
  if (!response.ok) {
    throw new ApiError(
      await errorMessageFromResponse(response, `${label} request failed.`),
      response.status
    );
  }

  const payload = await response.json().catch((cause: unknown) => {
    throw new ApiContractError(`The backend returned non-JSON data for ${label}.`, { cause });
  });
  return parseContract(schema, payload, label);
}
