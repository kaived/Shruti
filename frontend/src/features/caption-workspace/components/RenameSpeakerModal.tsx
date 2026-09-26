interface RenameSpeakerModalProps {
  isOpen: boolean;
  targetSpeakerId: string;
  newSpeakerName: string;
  onNewSpeakerNameChange: (val: string) => void;
  onClose: () => void;
  onApply: () => void;
}

export function RenameSpeakerModal({
  isOpen,
  targetSpeakerId,
  newSpeakerName,
  onNewSpeakerNameChange,
  onClose,
  onApply,
}: RenameSpeakerModalProps) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop">
      <div className="modal-dialog">
        <h3 className="modal-title">Rename Speaker Throughout Video</h3>
        <p className="modal-desc">
          Change all instances of <strong>"{targetSpeakerId}"</strong> across Bengali, English, and Hindi tracks.
        </p>

        <div className="modal-input-group">
          <label>Character / Actor Name</label>
          <input
            type="text"
            value={newSpeakerName}
            onChange={(e) => onNewSpeakerNameChange(e.target.value)}
            placeholder="e.g. অমিত / Amit"
            autoFocus
          />
        </div>

        <div className="modal-actions">
          <button type="button" className="btn-modal-cancel" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="btn-modal-primary" onClick={onApply}>
            Apply to all captions
          </button>
        </div>
      </div>
    </div>
  );
}
