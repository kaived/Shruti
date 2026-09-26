import { AccessSchema, CapabilitiesSchema } from '../core/contracts';
import type { Access, Capabilities } from '../core/contracts';
import {
  apiRequest,
  ApiContractError,
  ApiError,
  errorMessageFromResponse,
  parseContract,
} from '../core/http';

export interface UploadVideoOptions {
  onProgress?: (percent: number) => void;
  uploadKey?: string;
}

export async function fetchCapabilities(): Promise<Capabilities> {
  return apiRequest('/api/capabilities', CapabilitiesSchema, { cache: 'no-store' }, 'capabilities');
}

export function uploadVideoWithProgress(
  file: File,
  { onProgress, uploadKey }: UploadVideoOptions = {}
): Promise<Access> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const url = `/api/jobs?filename=${encodeURIComponent(file.name)}`;

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.((event.loaded / event.total) * 100);
    };

    xhr.onload = () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        const response = {
          status: xhr.status,
          statusText: xhr.statusText,
          json: async () => JSON.parse(xhr.responseText) as unknown,
        };
        void errorMessageFromResponse(response, `Video upload failed with status ${xhr.status}.`)
          .then((message) => reject(new ApiError(message, xhr.status)))
          .catch(() => reject(new ApiError(`Video upload failed with status ${xhr.status}.`, xhr.status)));
        return;
      }

      try {
        const raw = JSON.parse(xhr.responseText) as unknown;
        resolve(parseContract(AccessSchema, { ...(raw as object), filename: file.name }, 'upload'));
      } catch (cause) {
        reject(
          cause instanceof ApiContractError
            ? cause
            : new ApiContractError('The backend returned an invalid upload response.', { cause })
        );
      }
    };

    xhr.onerror = () => reject(new ApiError('Network error during video upload.', 0));
    xhr.onabort = () => reject(new ApiError('Video upload was cancelled.', 0));

    xhr.open('POST', url);
    xhr.withCredentials = true;
    xhr.setRequestHeader('Content-Type', 'application/octet-stream');
    if (uploadKey) xhr.setRequestHeader('X-Upload-Key', uploadKey);
    xhr.send(file);
  });
}
