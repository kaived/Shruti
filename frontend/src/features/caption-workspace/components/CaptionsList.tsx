import React from 'react';
import type { Cue, Language } from '../types';
import { formatTime } from '../utils/time';

interface CaptionsListProps {
  cues: Cue[];
  activeCue: Cue | undefined;
  activeCueRef: React.RefObject<HTMLDivElement | null>;
  language: Language;
  trackHeading: string;
  autoScroll: boolean;
  editingCueId: string | null;
  editCueText: string;
  editCueStart: number;
  editCueEnd: number;
  editCueSpeaker: string;
  availableSpeakers: string[];
  onToggleAutoScroll: (checked: boolean) => void;
  onSeek: (ms: number) => void;
  onStartEdit: (cue: Cue) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onDeleteCue: (cueId: string) => void;
  onOpenRenameSpeaker: (speakerId: string) => void;
  setEditCueText: (val: string) => void;
  setEditCueStart: (val: number) => void;
  setEditCueEnd: (val: number) => void;
  setEditCueSpeaker: (val: string) => void;
}

export function CaptionsList({
  cues,
  activeCue,
  activeCueRef,
  language,
  trackHeading,
  autoScroll,
  editingCueId,
  editCueText,
  editCueStart,
  editCueEnd,
  editCueSpeaker,
  availableSpeakers,
  onToggleAutoScroll,
  onSeek,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  onDeleteCue,
  onOpenRenameSpeaker,
  setEditCueText,
  setEditCueStart,
  setEditCueEnd,
  setEditCueSpeaker,
}: CaptionsListProps) {
  return (
    <div className="captions-panel-content">
      <div className="captions-toolbar">
        <span className="caption-track-heading">{trackHeading}</span>
        <label className="autoscroll-toggle">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => onToggleAutoScroll(e.target.checked)}
          />
          <span>Follow playback</span>
        </label>
      </div>

      <div className="captions-scroll-area">
        {cues.length === 0 ? (
          <div className="empty-panel-notice">
            <p>No captions available in this track.</p>
          </div>
        ) : (
          cues.map((cue) => {
            const isCurrent = cue.id === activeCue?.id;
            const isEditing = cue.id === editingCueId;

            if (isEditing) {
              return (
                <div key={cue.id} className="cue-card-edit-mode">
                  <div className="edit-form-header">
                    <span>Editing caption {cue.id}</span>
                    <span className="edit-time-stamp">
                      {formatTime(editCueStart)} – {formatTime(editCueEnd)}
                    </span>
                  </div>

                  <textarea
                    className="edit-textarea"
                    value={editCueText}
                    rows={3}
                    onChange={(e) => setEditCueText(e.target.value)}
                    lang={language}
                  />

                  <div className="edit-fields-row">
                    <label className="field-sm">
                      <span>Speaker:</span>
                      <input
                        type="text"
                        list="speakers-datalist"
                        value={editCueSpeaker}
                        onChange={(e) => setEditCueSpeaker(e.target.value)}
                        placeholder="Speaker 1"
                      />
                      <datalist id="speakers-datalist">
                        {availableSpeakers.map((spk) => (
                          <option key={spk} value={spk} />
                        ))}
                      </datalist>
                    </label>
                    <label className="field-sm">
                      <span>Start (ms):</span>
                      <input
                        type="number"
                        step="100"
                        value={editCueStart}
                        onChange={(e) => setEditCueStart(Number(e.target.value))}
                      />
                    </label>
                    <label className="field-sm">
                      <span>End (ms):</span>
                      <input
                        type="number"
                        step="100"
                        value={editCueEnd}
                        onChange={(e) => setEditCueEnd(Number(e.target.value))}
                      />
                    </label>
                  </div>

                  <div className="edit-form-actions">
                    <button type="button" className="btn-save-cue" onClick={onSaveEdit}>
                      Save changes
                    </button>
                    <button type="button" className="btn-cancel-cue" onClick={onCancelEdit}>
                      Cancel
                    </button>
                  </div>
                </div>
              );
            }

            return (
              <div
                key={cue.id}
                ref={isCurrent ? activeCueRef : undefined}
                className={`cue-card-item ${isCurrent ? 'active-cue' : ''} ${
                  cue.kind === 'sound' ? 'sound-cue' : ''
                }`}
                onClick={() => onSeek(cue.start_ms)}
              >
                <div className="cue-meta-line">
                  <span className="cue-timestamp">{formatTime(cue.start_ms)}</span>

                  {cue.kind === 'sound' ? (
                    <span className="badge-sound-event">Sound event</span>
                  ) : (
                    <button
                      type="button"
                      className="speaker-pill-btn"
                      title="Click to rename this speaker everywhere"
                      onClick={(e) => {
                        e.stopPropagation();
                        const spk = cue.speaker_ids[0] || 'Speaker 1';
                        onOpenRenameSpeaker(spk);
                      }}
                    >
                      {cue.speaker_ids.join(', ') || 'Unattributed'}
                      <span className="rename-hint">✎</span>
                    </button>
                  )}

                  {cue.is_edited && <span className="badge-edited">Edited</span>}
                  {cue.needs_translation_update && (
                    <span className="badge-translation-outdated">Needs translation update</span>
                  )}

                  <div className="cue-quick-actions">
                    <button
                      type="button"
                      className="btn-cue-tool"
                      title="Edit text & timings"
                      onClick={(e) => {
                        e.stopPropagation();
                        onStartEdit(cue);
                      }}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn-cue-tool delete"
                      title="Remove caption (undoable)"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteCue(cue.id);
                      }}
                    >
                      ✕
                    </button>
                  </div>
                </div>

                <p className="cue-text-line" lang={language}>
                  {cue.text}
                </p>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
