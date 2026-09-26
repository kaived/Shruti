import { formatElapsed } from '../utils/timeFormat';

interface ProcessingHeaderProps {
  filename: string;
  elapsedSeconds: number;
}

export function ProcessingHeader({ filename, elapsedSeconds }: ProcessingHeaderProps) {
  return (
    <div className="processing-header">
      <div className="processing-file-badge">
        <span className="file-icon">🎬</span>
        <span className="file-name">{filename}</span>
      </div>

      <div className="processing-timer">
        <span className="timer-label">Elapsed:</span>
        <span className="timer-val">{formatElapsed(elapsedSeconds)}</span>
      </div>
    </div>
  );
}
