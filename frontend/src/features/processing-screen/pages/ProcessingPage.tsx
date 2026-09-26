import { useEffect, useState } from 'react';
import { ProcessingHeader } from '../components/ProcessingHeader';
import { StageStepper } from '../components/StageStepper';
import type { ProcessingPageProps, StageConfig } from '../types';

const DISPLAY_STAGES: StageConfig[] = [
  {
    key: 'media',
    label: 'Uploading and checking your video',
    subtext: 'Validating video container, codecs, and media duration',
  },
  {
    key: 'acoustics',
    label: 'Preparing audio',
    subtext: 'Extracting clean 16kHz speech track and independent acoustic evidence',
  },
  {
    key: 'transcription',
    label: 'Transcribing dialogue and identifying speakers',
    subtext: 'Recognizing Bengali & inline English words with speaker attribution',
  },
  {
    key: 'alignment',
    label: 'Timing and formatting captions',
    subtext: 'Monotonic forced alignment, line wrapping, and shot cut detection',
  },
  {
    key: 'translation',
    label: 'Creating English and Hindi subtitles',
    subtext: 'Generating colloquial subtitle phrasing and tone-matched translations',
  },
  {
    key: 'quality_control',
    label: 'Checking captions for possible issues',
    subtext: 'Auditing silence/music hallucinations, reading speed, and source links',
  },
];

export function ProcessingPage({
  job,
  filename,
  uploadProgress,
  onRetry,
  onCancel,
  isRetrying,
}: ProcessingPageProps) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds((sec) => sec + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const currentStage = job?.stage || 'media';
  const isFailed = job?.state === 'failed' || job?.state === 'blocked';

  const getStageIndex = (stageName: string): number => {
    switch (stageName) {
      case 'configuration':
      case 'media':
        return 0;
      case 'acoustics':
      case 'shots':
        return 1;
      case 'transcription':
        return 2;
      case 'alignment':
      case 'bengali_cues':
        return 3;
      case 'translation_en':
      case 'translation_hi':
      case 'translation':
        return 4;
      case 'quality_control':
      case 'export':
      case 'finished':
        return 5;
      default:
        return 0;
    }
  };

  const activeStageIdx = getStageIndex(currentStage);

  return (
    <div className="processing-screen-container">
      <div className="processing-card">
        <ProcessingHeader filename={filename} elapsedSeconds={elapsedSeconds} />

        <div className="processing-title-section">
          {isFailed ? (
            <>
              <div className="status-badge-failed">Processing stopped</div>
              <h2 className="processing-title">Something went wrong</h2>
              <p className="processing-desc">
                {job?.message || 'A failure occurred while processing this stage. Check configuration or retry.'}
              </p>
            </>
          ) : (
            <>
              <div className="status-badge-active">
                <span className="pulse-dot" />
                <span>Processing in background</span>
              </div>
              <h2 className="processing-title">Generating captions & subtitles</h2>
              <p className="processing-desc">
                We're running speech recognition, speaker attribution, acoustic checks, and multilingual translations.
              </p>
            </>
          )}
        </div>

        {uploadProgress !== undefined && uploadProgress < 100 && (
          <div className="upload-progress-container">
            <div className="progress-header">
              <span>Uploading video data</span>
              <span>{Math.round(uploadProgress)}%</span>
            </div>
            <div className="progress-bar-track">
              <div className="progress-bar-fill" style={{ width: `${uploadProgress}%` }} />
            </div>
          </div>
        )}

        <StageStepper
          stages={DISPLAY_STAGES}
          activeStageIdx={activeStageIdx}
          isFailed={isFailed}
        />

        {isFailed ? (
          <div className="processing-actions">
            <button
              type="button"
              className="btn-retry"
              disabled={isRetrying}
              onClick={onRetry}
            >
              {isRetrying ? 'Retrying…' : 'Retry processing'}
            </button>
            {onCancel && (
              <button type="button" className="btn-secondary" onClick={onCancel}>
                Choose another video
              </button>
            )}
          </div>
        ) : (
          <div className="processing-safe-notice">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span>You can return to this page; processing continues automatically on the background worker.</span>
          </div>
        )}
      </div>
    </div>
  );
}
