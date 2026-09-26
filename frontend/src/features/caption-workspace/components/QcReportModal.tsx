import type { Results } from '../types';

interface QcReportModalProps {
  isOpen: boolean;
  qc: Results['qc'];
  onClose: () => void;
}

export function QcReportModal({ isOpen, qc, onClose }: QcReportModalProps) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop">
      <div className="modal-dialog wide">
        <div className="modal-header-row">
          <h3 className="modal-title">Automated Quality Control Report</h3>
          <button type="button" className="btn-modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="qc-report-body">
          <div className="qc-status-block">
            <div>
              <span className="qc-label">Release Readiness:</span>
              <strong>Human Release Approval Required</strong>
            </div>
            <div>
              <span className="qc-label">Overall Status:</span>
              <span className="badge-qc-status">{qc.status.replace(/_/g, ' ')}</span>
            </div>
          </div>

          <h4>Inspection Checklist</h4>
          <div className="qc-checks-grid">
            {Object.entries(qc.checks || {}).map(([key, val]) => (
              <div key={key} className="qc-check-card">
                <span className="check-title">{key.replace(/_/g, ' ')}</span>
                <span className="check-val">{val.replace(/_/g, ' ')}</span>
              </div>
            ))}
          </div>

          <h4>Documented System Limitations</h4>
          <ul className="qc-limitations-list">
            {qc.limitations.map((lim, i) => (
              <li key={i}>{lim}</li>
            ))}
          </ul>
        </div>

        <div className="modal-actions">
          <button type="button" className="btn-modal-primary" onClick={onClose}>
            Close report
          </button>
        </div>
      </div>
    </div>
  );
}
