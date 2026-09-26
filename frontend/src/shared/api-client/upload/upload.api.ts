import { apiPath } from '../../config';
import axios from 'axios';

import { AccessSchema, CapabilitiesSchema } from '../core/contracts';
import type { Access, Capabilities } from '../core/contracts';
import { ApiError, apiClient, apiRequest, parseContract } from '../core/http';

export interface UploadVideoOptions {
  onProgress?: (percent: number) => void;
  uploadKey?: string;
  signal?: AbortSignal;
}

interface CloudUploadSession {
  id: string;
  access_token: string;
  upload_url: string;
}

export async function fetchCapabilities(): Promise<Capabilities> {
  return apiRequest(apiPath('/capabilities'), CapabilitiesSchema, undefined, 'capabilities');
}

function reportProgress(onProgress?: (percent: number) => void) {
  return (event: { loaded: number; total?: number }) => {
    if (event.total) {
      onProgress?.((event.loaded / event.total) * 100);
    }
  };
}

/**
 * Direct browser-to-GCS upload. Cloud Run caps request bodies at 32 MiB, so
 * episode-sized videos must bypass the API and be finalized afterwards.
 */
async function uploadViaCloudStorage(
  file: File,
  headers: Record<string, string>,
  { onProgress, signal }: UploadVideoOptions
): Promise<Access | null> {
  let session: CloudUploadSession;
  try {
    const response = await apiClient.post<CloudUploadSession>(
      apiPath('/cloud-uploads'),
      { filename: file.name, size_bytes: file.size },
      { headers, signal }
    );
    session = response.data;
  } catch (error) {
    // 404/503: this deployment has no bucket configured; use the API upload.
    if (error instanceof ApiError && (error.status === 404 || error.status === 503)) {
      return null;
    }
    throw error;
  }

  // Plain axios: the session URL is a bearer capability for GCS, not our API.
  await axios.put(session.upload_url, file, {
    headers: { 'Content-Type': file.type || 'video/mp4' },
    signal,
    onUploadProgress: reportProgress(onProgress),
  });

  await apiClient.post(apiPath(`/cloud-uploads/${session.id}/finalize`), undefined, {
    headers: { Authorization: `Bearer ${session.access_token}` },
    signal,
    timeout: 300000,
  });

  return parseContract(
    AccessSchema,
    { id: session.id, access_token: session.access_token, filename: file.name },
    'upload'
  );
}

/**
 * Uploads a video with real-time progress, preferring direct Cloud Storage uploads.
 */
export async function uploadVideoWithProgress(
  file: File,
  options: UploadVideoOptions = {}
): Promise<Access> {
  const { onProgress, uploadKey, signal } = options;
  const keyHeaders: Record<string, string> = uploadKey ? { 'X-Upload-Key': uploadKey } : {};

  const cloudAccess = await uploadViaCloudStorage(file, keyHeaders, options);
  if (cloudAccess) {
    return cloudAccess;
  }

  const url = apiPath(`/jobs?filename=${encodeURIComponent(file.name)}`);
  const response = await apiClient.post<unknown>(url, file, {
    headers: { ...keyHeaders, 'Content-Type': 'application/octet-stream' },
    signal,
    onUploadProgress: reportProgress(onProgress),
  });

  return parseContract(
    AccessSchema,
    { ...(response.data as object), filename: file.name },
    'upload'
  );
}
