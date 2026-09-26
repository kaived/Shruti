import { useState } from 'react';
import type { Cue, Language, Results } from '../types';
import { downloadEverythingZip, downloadTextFile, generateSrtString, generateVttString } from '../utils/exportFiles';

interface WorkspaceHeaderProps {
  jobId: string;
  filename: string;
  unreviewedCount: number;
  hasDeletedCues: boolean;
  tracks: Record<Language, Cue[]>;
  qc: Results['qc'];
  onNewVideo: () => void;
  onUndoDelete: () => void;
  onOpenQcModal: () => void;
}

export function WorkspaceHeader({
  jobId,
  filename,
  unreviewedCount,
  hasDeletedCues,
  tracks,
  qc,
  onNewVideo,
  onUndoDelete,
  onOpenQcModal,
}: WorkspaceHeaderProps) {
  const [downloadMenuOpen, setDownloadMenuOpen] = useState(false);
  const [isDownloadingZip, setIsDownloadingZip] = useState(false);

  const handleZip = async () => {
    setIsDownloadingZip(true);
    try {
      await downloadEverythingZip(jobId, filename, tracks, qc, unreviewedCount);
    } catch {
      alert('Could not package ZIP. Please download files individually.');
    } finally {
      setIsDownloadingZip(false);
      setDownloadMenuOpen(false);
    }
  };

  return (
    <header className="workspace-header">
      <div className="header-left">
        <button type="button" className="btn-back-home" onClick={onNewVideo} title="Upload new video">
          <span className="brand-glyph">শ্রু</span>
          <span className="brand-text">Shruti</span>
        </button>
        <span className="header-divider">/</span>
        <div className="video-title-meta">
          <h1 className="header-filename">{filename}</h1>
          <span className="badge-subtle">PS2 Production Review</span>
        </div>
      </div>

      <div className="header-center-status">
        <div className={`status-pill ${unreviewedCount > 0 ? 'status-needs-review' : 'status-clean'}`}>
          <span className="status-dot" />
          <span className="status-text">
            Captions generated · {unreviewedCount} {unreviewedCount === 1 ? 'moment needs' : 'moments need'} review
          </span>
        </div>
      </div>

      <div className="header-right-actions">
        {hasDeletedCues && (
          <button type="button" className="btn-undo-delete" onClick={onUndoDelete}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
            </svg>
            <span>Undo remove</span>
          </button>
        )}

        <div className="download-dropdown-wrapper">
          <button
            type="button"
            className="btn-download-primary"
            onClick={() => setDownloadMenuOpen(!downloadMenuOpen)}
          >
            <span>Download files</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          {downloadMenuOpen && (
            <div className="download-menu-dropdown">
              {unreviewedCount > 0 && (
                <div className="download-industry-warning">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <span>{unreviewedCount} unreviewed moments remain in this export.</span>
                </div>
              )}

              <button
                type="button"
                className="download-option-btn highlight"
                disabled={isDownloadingZip}
                onClick={handleZip}
              >
                <div className="option-title">Download everything — ZIP</div>
                <div className="option-sub">Bengali CC, EN/HI subtitles, QC report & manifest</div>
              </button>

              <div className="dropdown-separator" />

              <button
                type="button"
                className="download-option-btn"
                onClick={() => {
                  downloadTextFile('bengali.vtt', generateVttString(tracks.bn || []), 'text/vtt');
                  setDownloadMenuOpen(false);
                }}
              >
                <div className="option-title">Bengali closed captions — WebVTT</div>
                <div className="option-sub">Original dialogue, speakers & sound events</div>
              </button>

              <button
                type="button"
                className="download-option-btn"
                onClick={() => {
                  downloadTextFile('english.srt', generateSrtString(tracks.en || []), 'application/x-subrip');
                  setDownloadMenuOpen(false);
                }}
              >
                <div className="option-title">English subtitles — SRT</div>
                <div className="option-sub">Colloquial translation, timed for reading</div>
              </button>

              <button
                type="button"
                className="download-option-btn"
                onClick={() => {
                  downloadTextFile('hindi.srt', generateSrtString(tracks.hi || []), 'application/x-subrip');
                  setDownloadMenuOpen(false);
                }}
              >
                <div className="option-title">Hindi subtitles — SRT</div>
                <div className="option-sub">Natural phrasing preserving names & tone</div>
              </button>

              <button
                type="button"
                className="download-option-btn"
                onClick={() => {
                  downloadTextFile('qc_report.json', JSON.stringify(qc, null, 2), 'application/json');
                  setDownloadMenuOpen(false);
                }}
              >
                <div className="option-title">Quality report — JSON</div>
                <div className="option-sub">Machine evidence, checks & limitations</div>
              </button>

              <button
                type="button"
                className="download-option-btn inspect-qc"
                onClick={() => {
                  onOpenQcModal();
                  setDownloadMenuOpen(false);
                }}
              >
                <div className="option-title">Inspect Quality Report in App →</div>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
