import { useEffect, useState } from 'react';
import { DropzoneArea } from '../components/DropzoneArea';
import { SelectedVideoCard } from '../components/SelectedVideoCard';
import type { UploadPageProps } from '../types';
import { extractVideoMeta } from '../utils/videoMeta';

export function UploadPage({
  capabilities,
  onStartUpload,
  isUploading,
  errorMessage,
  initialFile,
}: UploadPageProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(initialFile || null);
  const [durationSec, setDurationSec] = useState<number | null>(null);
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null);
  const [uploadKey, setUploadKey] = useState('');

  useEffect(() => {
    if (initialFile) {
      setSelectedFile(initialFile);
    }
  }, [initialFile]);

  useEffect(() => {
    if (!selectedFile) {
      return;
    }

    let isMounted = true;
    void extractVideoMeta(selectedFile).then(({ duration, thumbnailUrl: thumb }) => {
      if (isMounted) {
        setDurationSec(duration);
        setThumbnailUrl(thumb);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [selectedFile]);

  const maxUploadMb = capabilities
    ? Math.round(capabilities.max_upload_bytes / (1024 * 1024))
    : 500;

  return (
    <div className="upload-screen-container">
      <div className="upload-hero">
        <span className="brand-pill">Bengali Caption & Subtitle Studio</span>
        <h1 className="hero-title">Every word. In context.</h1>
        <p className="hero-subtitle">
          Turn your Bengali videos into accessible closed captions and professional English and Hindi subtitles with automated quality control.
        </p>
      </div>

      <div className="upload-card">
        {errorMessage && (
          <div className="notice-error" role="alert">
            <svg
              className="notice-icon"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div className="notice-message">{errorMessage}</div>
          </div>
        )}

        {!selectedFile ? (
          <DropzoneArea maxUploadMb={maxUploadMb} onSelectFile={(file) => setSelectedFile(file)} />
        ) : (
          <SelectedVideoCard
            file={selectedFile}
            durationSec={durationSec}
            thumbnailUrl={thumbnailUrl}
            isUploading={isUploading}
            uploadKeyRequired={capabilities?.upload_key_required ?? false}
            uploadKey={uploadKey}
            onUploadKeyChange={setUploadKey}
            onChangeVideo={() => {
              setSelectedFile(null);
              setUploadKey('');
            }}
            onGenerateCaptions={() => onStartUpload(selectedFile, uploadKey || undefined)}
          />
        )}
      </div>
    </div>
  );
}
