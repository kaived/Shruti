import type { Issue } from '../types';
import { formatTime } from '../utils/time';

interface TimelineTrackProps {
  currentTimeMs: number;
  durationMs: number;
  issues: Issue[];
  selectedIssueId: string | null;
  onSeek: (ms: number) => void;
  onSelectIssue: (issueId: string) => void;
}

export function TimelineTrack({
  currentTimeMs,
  durationMs,
  issues,
  selectedIssueId,
  onSeek,
  onSelectIssue,
}: TimelineTrackProps) {
  return (
    <div className="timeline-container">
      <div className="timeline-header">
        <span className="timeline-label">Visual timeline & review markers</span>
        <span className="timeline-hint">Pins indicate flagged audio / caption moments</span>
      </div>

      <div
        className="timeline-track"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const clickX = e.clientX - rect.left;
          const ratio = Math.max(0, Math.min(1, clickX / rect.width));
          if (durationMs > 0) {
            onSeek(ratio * durationMs);
          }
        }}
      >
        <div
          className="timeline-playhead-fill"
          style={{ width: `${durationMs > 0 ? (currentTimeMs / durationMs) * 100 : 0}%` }}
        />

        {issues.map((iss) => {
          if (durationMs <= 0) return null;
          const leftPercent = (iss.start_ms / durationMs) * 100;
          const isSelected = iss.id === selectedIssueId;
          const isResolved = iss.review_state === 'resolved';

          return (
            <button
              key={iss.id}
              type="button"
              className={`timeline-marker marker-${iss.severity} ${isSelected ? 'selected' : ''} ${
                isResolved ? 'resolved' : ''
              }`}
              style={{ left: `${leftPercent}%` }}
              title={`${iss.severity.toUpperCase()}: ${iss.code.replace(/_/g, ' ')} at ${formatTime(
                iss.start_ms
              )}`}
              onClick={(e) => {
                e.stopPropagation();
                onSelectIssue(iss.id);
                onSeek(iss.start_ms);
              }}
            />
          );
        })}
      </div>
    </div>
  );
}
