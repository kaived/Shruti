import type { Cue, Issue, ReviewFilterType } from '../types';
import { getFriendlyIssueInfo } from '../utils/issueHelpers';
import { formatTime } from '../utils/time';
import { Button } from '../../../shared/ui';

interface ReviewPanelProps {
  issues: Issue[];
  filteredIssues: Issue[];
  reviewFilter: ReviewFilterType;
  selectedIssueId: string | null;
  cues: Cue[];
  onFilterChange: (filter: ReviewFilterType) => void;
  onSelectIssue: (issueId: string) => void;
  onPrevIssue: () => void;
  onNextIssue: () => void;
  onToggleIssueResolved: (issueId: string) => void;
  onReplaySection: (startMs: number, endMs: number) => void;
  onEditCue: (cue: Cue) => void;
}

export function ReviewPanel({
  issues,
  filteredIssues,
  reviewFilter,
  selectedIssueId,
  cues,
  onFilterChange,
  onSelectIssue,
  onPrevIssue,
  onNextIssue,
  onToggleIssueResolved,
  onReplaySection,
  onEditCue,
}: ReviewPanelProps) {
  const unreviewedCount = issues.filter((i) => i.review_state !== 'resolved').length;
  const currentIssueIndex = selectedIssueId
    ? filteredIssues.findIndex((i) => i.id === selectedIssueId)
    : -1;

  return (
    <div className="review-panel-content">
      <div className="review-subbar">
        <div className="filter-pill-group">
          <button
            type="button"
            className={`filter-pill ${reviewFilter === 'needs_review' ? 'active' : ''}`}
            onClick={() => onFilterChange('needs_review')}
          >
            Needs review ({unreviewedCount})
          </button>
          <button
            type="button"
            className={`filter-pill ${reviewFilter === 'reviewed' ? 'active' : ''}`}
            onClick={() => onFilterChange('reviewed')}
          >
            Reviewed ({issues.length - unreviewedCount})
          </button>
          <button
            type="button"
            className={`filter-pill ${reviewFilter === 'all' ? 'active' : ''}`}
            onClick={() => onFilterChange('all')}
          >
            All ({issues.length})
          </button>
        </div>

        <div className="nav-issue-group">
          <button
            type="button"
            className="btn-icon-nav"
            onClick={onPrevIssue}
            disabled={filteredIssues.length === 0}
            title="Previous issue"
          >
            ‹
          </button>
          <span className="nav-issue-count">
            {filteredIssues.length > 0 && currentIssueIndex !== -1
              ? `${currentIssueIndex + 1} of ${filteredIssues.length}`
              : `${filteredIssues.length} issues`}
          </span>
          <button
            type="button"
            className="btn-icon-nav"
            onClick={onNextIssue}
            disabled={filteredIssues.length === 0}
            title="Next issue"
          >
            ›
          </button>
        </div>
      </div>

      <div className="issues-scroll-area">
        {filteredIssues.length === 0 ? (
          <div className="empty-panel-notice">
            <span className="empty-icon">✓</span>
            <h3>No issues in this filter</h3>
            <p>All flagged moments have been reviewed or resolved.</p>
          </div>
        ) : (
          filteredIssues.map((iss) => {
            const info = getFriendlyIssueInfo(iss.code);
            const isSelected = iss.id === selectedIssueId;
            const isResolved = iss.review_state === 'resolved';

            return (
              <div
                key={iss.id}
                className={`issue-card severity-${iss.severity} ${isSelected ? 'selected' : ''} ${
                  isResolved ? 'resolved' : ''
                }`}
                onClick={() => onSelectIssue(iss.id)}
              >
                <div className="issue-card-top">
                  <div className="issue-badge-group">
                    <span className={`badge-severity badge-${iss.severity}`}>{iss.severity}</span>
                    <span className="issue-time-range">
                      {formatTime(iss.start_ms)} – {formatTime(iss.end_ms)}
                    </span>
                    <span className="issue-lang-tag">{iss.language}</span>
                  </div>

                  <Button
                    variant={isResolved ? 'secondary' : 'primary'}
                    size="sm"
                    className="!py-0.5 !px-2.5 !text-xs shrink-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleIssueResolved(iss.id);
                    }}
                  >
                    {isResolved ? '✓ Reviewed' : 'Mark reviewed'}
                  </Button>
                </div>

                <h3 className="issue-friendly-title">{info.title}</h3>
                <p className="issue-friendly-desc">{info.explanation}</p>

                {iss.evidence && Object.keys(iss.evidence).length > 0 && (
                  <div className="issue-evidence-details">
                    <div className="evidence-summary">
                      {iss.evidence.rule_threshold !== undefined && (
                        <span>Threshold: {String(iss.evidence.rule_threshold)}</span>
                      )}
                      {iss.evidence.music_overlap_ms !== undefined && (
                        <span>Music overlap: {String(iss.evidence.music_overlap_ms)}ms</span>
                      )}
                      {iss.evidence.cps !== undefined && <span>CPS: {String(iss.evidence.cps)}</span>}
                    </div>
                  </div>
                )}

                <div className="issue-action-buttons flex items-center gap-2 mt-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="!py-1 !px-2.5 !text-xs"
                    onClick={(e) => {
                      e.stopPropagation();
                      onReplaySection(iss.start_ms, iss.end_ms);
                    }}
                  >
                    ▶ Play this section
                  </Button>

                  {iss.cue_ids.length > 0 && (
                    <Button
                      variant="secondary"
                      size="sm"
                      className="!py-1 !px-2.5 !text-xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        const targetCue = cues.find((c) => iss.cue_ids.includes(c.id));
                        if (targetCue) {
                          onEditCue(targetCue);
                        }
                      }}
                    >
                      ✎ Edit caption
                    </Button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
