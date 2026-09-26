import { useEffect, useRef, useState } from 'react';
import { ArrowRight, ChevronDown, CircleAlert } from 'lucide-react';
import type { Cue, Language, Results } from '../types';
import { downloadEverythingZip, downloadTextFile, generateSrtString, generateVttString } from '../utils/exportFiles';
import { Button } from '../../../shared/ui';

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
  onUndoDelete,
  onOpenQcModal,
}: WorkspaceHeaderProps) {
  const [downloadMenuOpen, setDownloadMenuOpen] = useState(false);
  const downloadMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!downloadMenuOpen) return;
    const onPointer = (event: MouseEvent) => {
      if (downloadMenuRef.current && !downloadMenuRef.current.contains(event.target as Node)) {
        setDownloadMenuOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && setDownloadMenuOpen(false);
    document.addEventListener('mousedown', onPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [downloadMenuOpen]);
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
        <div className="video-title-meta">
          <h1 className="header-filename" title={filename}>{filename}</h1>
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
          <Button
            variant="secondary"
            size="sm"
            onClick={onUndoDelete}
            icon={
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="1 4 1 10 7 10" />
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
              </svg>
            }
          >
            Bring back deleted line
          </Button>
        )}

        <div className="download-dropdown-wrapper" ref={downloadMenuRef}>
          <Button
            variant="primary"
            size="md"
            onClick={() => setDownloadMenuOpen(!downloadMenuOpen)}
            aria-haspopup="menu"
            aria-expanded={downloadMenuOpen}
            iconRight={
              <ChevronDown
                size={15}
                aria-hidden="true"
                className={`transition-transform duration-200 ${downloadMenuOpen ? 'rotate-180' : ''}`}
              />
            }
          >
            Download files
          </Button>

          {downloadMenuOpen && (
            <div className="download-menu-dropdown">
              {unreviewedCount > 0 && (
                <div className="download-industry-warning">
                  <CircleAlert size={15} className="mt-px shrink-0" aria-hidden="true" />
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
                <div className="option-title inline-flex items-center gap-1.5">
                  Inspect Quality Report in App
                  <ArrowRight size={14} aria-hidden="true" />
                </div>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
