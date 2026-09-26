import { Modal, Input, Button } from '../../../shared/ui';

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
  const footerContent = (
    <div className="flex items-center justify-end gap-3 w-full">
      <Button variant="secondary" size="md" onClick={onClose}>
        Cancel
      </Button>
      <Button variant="primary" size="md" onClick={onApply}>
        Apply to all captions
      </Button>
    </div>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="md"
      title="Rename Speaker Throughout Video"
      subtitle={
        <span>
          Change all instances of <strong>"{targetSpeakerId}"</strong> across Bengali, English, and Hindi tracks.
        </span>
      }
      footer={footerContent}
    >
      <div className="py-2">
        <Input
          label="Character / Actor Name"
          type="text"
          value={newSpeakerName}
          onChange={(e) => onNewSpeakerNameChange(e.target.value)}
          placeholder="e.g. অমিত / Amit"
          autoFocus
        />
      </div>
    </Modal>
  );
}
