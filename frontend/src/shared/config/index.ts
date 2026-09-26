export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '');
export const API_VERSION = 'v1';
export const API_PREFIX = `/api/${API_VERSION}`;

/** Versioned API path relative to API_BASE_URL, e.g. apiPath('/jobs') -> '/api/v1/jobs'. */
export function apiPath(path: string): string {
  return `${API_PREFIX}${path.startsWith('/') ? path : `/${path}`}`;
}

/** Absolute URL for elements that bypass axios (e.g. <video src>). */
export function apiUrl(path: string): string {
  return `${API_BASE_URL}${apiPath(path)}`;
}
