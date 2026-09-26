import React, { useRef, useState } from 'react';

interface DropzoneAreaProps {
  maxUploadMb: number;
  onSelectFile: (file: File) => void;
}

export function DropzoneArea({ maxUploadMb, onSelectFile }: DropzoneAreaProps) {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onSelectFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onSelectFile(e.target.files[0]);
    }
  };

  return (
    <div
      className={`dropzone-area ${dragActive ? 'drag-active' : ''}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".mp4,.mkv,.webm,video/mp4,video/x-matroska,video/webm"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />
      <div className="dropzone-icon-bubble">
        <svg
          width="36"
          height="36"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      </div>
      <h2 className="dropzone-title">Upload your Bengali video</h2>
      <p className="dropzone-prompt">
        Drag and drop your file here, or <span className="browse-link">browse files</span>
      </p>
      <div className="dropzone-limits">
        <span>MP4, MKV, or WebM</span>
        <span className="dot-divider">•</span>
        <span>Up to {maxUploadMb} MB</span>
      </div>
    </div>
  );
}
