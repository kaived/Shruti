import { useEffect, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { ProcessingHeader } from '../components/ProcessingHeader';
import { StageStepper } from '../components/StageStepper';
import type { ProcessingPageProps, StageConfig } from '../types';
import { Button } from '../../../shared/ui';

const DISPLAY_STAGES: StageConfig[] = [
  {
    key: 'media',
    label: 'Checking your video',
    subtext: 'Making sure the video and its sound can be read',
  },
  {
    key: 'transcription',
    label: 'Writing down what is said',
    subtext: 'Turning the Bengali speech into text and working out who is speaking',
  },
  {
    key: 'alignment',
    label: 'Matching words to the moment they are spoken',
    subtext: 'Lining each word up with the video and keeping English words in English',
  },
  {
    key: 'acoustics',
    label: 'Listening for music and sounds',
    subtext: 'Spotting music, silence and sound effects, and splitting captions into easy-to-read lines',
  },
  {
    key: 'translation',
    label: 'Translating to English and Hindi',
    subtext: 'Creating English and Hindi subtitles that match the Bengali captions',
  },
  {
    key: 'quality_control',
    label: 'Checking the captions',
    subtext: 'Marking any lines a person should double-check before publishing',
  },
];

/** Plain-language explanations for each failure, keyed by the backend error code. */
const FRIENDLY_ERRORS: Record<string, string> = {
  NO_AUDIO: 'This video has no sound, so there is nothing to caption. Please choose a video with speech.',
  NO_VIDEO: 'This file does not contain a video. Please choose a video file.',
  INVALID_DURATION: 'We could not tell how long this video is. The file may be damaged; please try another copy.',
  DURATION_LIMIT: 'This video is too long. Please upload a shorter video (up to 2 hours).',
  MEDIA_DECODE_FAILED: 'We could not open this video. It may be damaged or in an unusual format; please try an MP4 file.',
  WORKER_FAILED: 'Processing was interrupted. Press "Try again"; the parts that already finished will be kept.',
  PIPELINE_FAILED: 'Something went wrong while making your captions. Press "Try again"; the parts that already finished will be kept.',
  QUEUE_UNAVAILABLE: 'Our service is busy right now. Please wait a moment and press "Try again".',
  PROVIDER_NOT_CONFIGURED: 'The captioning service is temporarily unavailable. Please try again later.',
  FFMPEG_MISSING: 'The captioning service is temporarily unavailable. Please try again later.',
};
const DEFAULT_ERROR = 'Something went wrong while making your captions. Please press "Try again" or choose another video.';

export function ProcessingPage({
  job,
  filename,
  uploadProgress,
  onRetry,
  onCancel,
  isRetrying,
}: ProcessingPageProps) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Server timestamps are UTC; treat a zone-less ISO string as UTC.
  const parseUtc = (value?: string) =>
    value ? Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`) : NaN;
  const createdAt = parseUtc(job?.created_at);
  // Stop the clock once processing has stopped: count up to the job's last update.
  const hasStopped = job?.state === 'failed' || job?.state === 'blocked';
  const endAt = hasStopped ? parseUtc(job?.updated_at) : now;
  const elapsedSeconds = Number.isFinite(createdAt) && Number.isFinite(endAt)
    ? Math.max(0, Math.floor((endAt - createdAt) / 1000))
    : 0;

  const currentStage = job?.stage || 'media';
  const isFailed = job?.state === 'failed' || job?.state === 'blocked';

  const getStageIndex = (stageName: string): number => {
    switch (stageName) {
      case 'transcription':
      case 'diarization':
        return 1;
      case 'alignment':
      case 'code_switch':
        return 2;
      case 'acoustics':
      case 'shots':
      case 'bengali_cues':
        return 3;
      case 'translation':
      case 'translation_en':
      case 'translation_hi':
        return 4;
      case 'quality_control':
      case 'export':
      case 'finished':
        return 5;
      default: // configuration, uploading, upload_complete, media
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
              <div className="status-badge-failed">Stopped</div>
              <h2 className="processing-title">We couldn't finish this video</h2>
              <p className="processing-desc">
                {(job?.error_code && FRIENDLY_ERRORS[job.error_code]) || DEFAULT_ERROR}
              </p>
            </>
          ) : (
            <>
              <div className="status-badge-active">
                <span className="pulse-dot" />
                <span>Working on it</span>
              </div>
              <h2 className="processing-title">Making your captions and subtitles</h2>
              <p className="processing-desc">
                We're listening to the video, writing Bengali captions, translating them to English and Hindi, and checking the result.
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
            <Button
              variant="primary"
              size="md"
              isLoading={isRetrying}
              icon={<RotateCcw size={16} />}
              onClick={onRetry}
            >
              Try again
            </Button>
            {onCancel && (
              <Button variant="secondary" size="md" onClick={onCancel}>
                Choose another video
              </Button>
            )}
          </div>
        ) : (
          <div className="processing-safe-notice">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span>
              This takes a few minutes. You can close this tab: processing continues in the cloud,
              and you can open this video again from "My videos" at the top.
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
