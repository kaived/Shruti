import { useRef } from 'react';
import type { ChangeEvent } from 'react';
import type { Access } from '../features/upload-screen';

interface NavbarProps {
  jobs: Access[];
  selectedJobId: string | null;
  onSelectJob: (id: string) => void;
  onNewVideo: () => void;
  onSelectFile?: (file: File) => void;
}

export function Navbar({
  jobs,
  selectedJobId,
  onSelectJob,
  onNewVideo,
  onSelectFile,
}: NavbarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (onSelectFile) {
        onSelectFile(file);
      } else {
        onNewVideo();
      }
      e.target.value = '';
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };
  return (
    <header className="top-navbar-wrapper">
      <nav className="top-nav" aria-label="Main Navigation">
        {/* Brand Group */}
        <div className="nav-brand-group">
          <button
            type="button"
            className="nav-brand-btn"
            onClick={onNewVideo}
            title="Go to upload screen"
          >
            <span className="brand-glyph" aria-hidden="true">
              শ্রু
            </span>
            <div className="brand-text-col">
              <span className="brand-title">Shruti</span>
              <span className="brand-subtitle">Hoichoi Caption Studio</span>
            </div>
          </button>
        </div>

        {/* Video Switcher Scroller (if active or past jobs exist) */}
        {jobs.length > 0 && (
          <div className="nav-jobs-scroller" role="tablist" aria-label="Active videos">
            {jobs.map((item) => {
              const isSelected = selectedJobId === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={isSelected}
                  className={`nav-job-pill ${isSelected ? 'active' : ''}`}
                  onClick={() => onSelectJob(item.id)}
                  title={`Switch to ${item.filename}`}
                >
                  <span className="nav-job-icon" aria-hidden="true">
                    🎬
                  </span>
                  <span className="nav-job-filename">{item.filename}</span>
                </button>
              );
            })}
          </div>
        )}

        {/* Right Action Group: New Video button */}
        <div className="nav-actions-group">
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp4,.mkv,.webm,video/mp4,video/x-matroska,video/webm"
            style={{ display: 'none' }}
            onChange={handleFileChange}
            aria-hidden="true"
          />
          <button
            type="button"
            className="btn-new-video"
            onClick={handleUploadClick}
            title="Choose a video file to upload"
          >
            <span className="btn-icon" aria-hidden="true">
              +
            </span>
            <span>Upload video</span>
          </button>
        </div>
      </nav>
    </header>
  );
}
