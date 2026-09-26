import { formatDuration, formatFileSize } from '../utils/videoMeta';

interface SelectedVideoCardProps {
  file: File;
  durationSec: number | null;
  thumbnailUrl: string | null;
  isUploading: boolean;
  uploadKeyRequired: boolean;
  uploadKey: string;
  onUploadKeyChange: (value: string) => void;
  onChangeVideo: () => void;
  onGenerateCaptions: () => void;
}

export function SelectedVideoCard({
  file,
  durationSec,
  thumbnailUrl,
  isUploading,
  uploadKeyRequired,
  uploadKey,
  onUploadKeyChange,
  onChangeVideo,
  onGenerateCaptions,
}: SelectedVideoCardProps) {
  return (
    <div className="selected-video-preview">
      <div className="thumbnail-box">
        {thumbnailUrl ? (
          <img src={thumbnailUrl} alt="Video thumbnail" className="video-thumb-img" />
        ) : (
          <div className="thumb-placeholder">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
          </div>
        )}
        {durationSec !== null && (
          <span className="video-duration-badge">{formatDuration(durationSec)}</span>
        )}
      </div>

      <div className="selected-meta-details">
        <div className="file-header">
          <div>
            <h3 className="selected-filename">{file.name}</h3>
            <p className="selected-filesize">{formatFileSize(file.size)}</p>
          </div>
          <button type="button" className="change-video-btn" onClick={onChangeVideo}>
            Change video
          </button>
        </div>

        <div className="included-outputs-box">
          <span className="included-label">Included outputs:</span>
          <div className="output-pills">
            <span className="pill-output">
              <span className="pill-lang">বাংলা</span> CC (.vtt)
            </span>
            <span className="pill-output">
              <span className="pill-lang">English</span> Subtitles (.srt)
            </span>
            <span className="pill-output">
              <span className="pill-lang">हिन्दी</span> Subtitles (.srt)
            </span>
            <span className="pill-output">
              <span className="pill-lang">QC</span> Report (.json)
            </span>
          </div>
        </div>

        {uploadKeyRequired && (
          <label className="upload-key-field">
            <span>Demo upload key</span>
            <input
              type="password"
              value={uploadKey}
              autoComplete="off"
              disabled={isUploading}
              placeholder="Enter the access key supplied for this demo"
              onChange={(event) => onUploadKeyChange(event.target.value)}
            />
          </label>
        )}

        <button
          type="button"
          className="btn-primary-generate"
          disabled={isUploading || (uploadKeyRequired && !uploadKey.trim())}
          onClick={onGenerateCaptions}
        >
          {isUploading ? (
            <>
              <span className="spinner-sm" />
              <span>Uploading video…</span>
            </>
          ) : (
            <>
              <span>Generate captions</span>
              <span className="arrow-icon">→</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
