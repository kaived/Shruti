export function extractVideoMeta(
  file: File
): Promise<{ duration: number; thumbnailUrl: string | null }> {
  return new Promise((resolve) => {
    const video = document.createElement('video');
    const objectUrl = URL.createObjectURL(file);
    video.preload = 'metadata';
    video.src = objectUrl;
    video.muted = true;
    video.playsInline = true;

    video.onloadedmetadata = () => {
      video.currentTime = Math.min(1.0, video.duration / 3);
    };

    video.onseeked = () => {
      let thumb: string | null = null;
      try {
        const canvas = document.createElement('canvas');
        canvas.width = Math.min(video.videoWidth || 480, 480);
        canvas.height = Math.min(video.videoHeight || 270, 270);
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          thumb = canvas.toDataURL('image/jpeg', 0.8);
        }
      } catch {
        thumb = null;
      }
      URL.revokeObjectURL(objectUrl);
      resolve({ duration: video.duration, thumbnailUrl: thumb });
    };

    video.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      resolve({ duration: 0, thumbnailUrl: null });
    };
  });
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
