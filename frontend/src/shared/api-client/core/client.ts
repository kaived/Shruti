import { API_BASE_URL } from '../../config';
import axios, { AxiosError } from 'axios';
import type { AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';

export interface CustomRequestConfig extends AxiosRequestConfig {
  accessToken?: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly data?: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export class ApiContractError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = 'ApiContractError';
  }
}

/**
 * Pre-configured Axios instance for the Shruti API client.
 * Connects to Vite dev proxy (or VITE_API_BASE_URL) and passes session cookies.
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    Accept: 'application/json',
  },
  timeout: 60000,
});

// Request interceptor: Attach Authorization Bearer token if provided in config
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig & { accessToken?: string }) => {
    if (config.accessToken) {
      config.headers.set('Authorization', `Bearer ${config.accessToken}`);
    }
    return config;
  },
  (error: unknown) => Promise.reject(error)
);

// Response interceptor: Normalize backend responses and errors into typed ApiError
apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<{ detail?: unknown; message?: unknown }>;
      const status = axiosError.response?.status ?? 0;
      const data = axiosError.response?.data;

      // Plain-language messages for people using the studio; the server's technical
      // detail stays available on ApiError.data for debugging.
      const FRIENDLY_BY_STATUS: Record<number, string> = {
        403: 'The access key is not correct. Please check it and try again.',
        404: 'We could not find this video. It may have expired; please upload it again.',
        409: 'This video cannot be processed again. Please upload it again.',
        413: 'This file is too large. Please choose a video under 500 MB.',
        415: 'This file type is not supported. Please upload an MP4, MKV or WebM video.',
        429: 'Our service is busy right now. Please wait a moment and try again.',
      };
      let message = 'Something went wrong. Please try again.';
      if (FRIENDLY_BY_STATUS[status]) {
        message = FRIENDLY_BY_STATUS[status];
      } else if (typeof data?.detail === 'string' && status < 500) {
        message = data.detail;
      } else if (typeof data?.message === 'string') {
        message = data.message;
      } else if (status === 0 || !axiosError.response) {
        message = 'We could not connect. Please check your internet connection and try again.';
      } else if (status >= 500) {
        message = 'Our service had a temporary problem. Please try again in a moment.';
      } else if (axiosError.message && !axiosError.message.includes('ECONNREFUSED') && !axiosError.message.includes('127.0.0.1')) {
        message = axiosError.message;
      }

      return Promise.reject(new ApiError(message, status, data));
    }

    if (error instanceof Error) {
      return Promise.reject(new ApiError(error.message, 0));
    }

    return Promise.reject(new ApiError('Something went wrong. Please try again.', 0));
  }
);
