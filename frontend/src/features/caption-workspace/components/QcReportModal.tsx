import type { Results } from '../types';
import { Modal, Button } from '../../../shared/ui';
import { ShieldCheck, CheckCircle2 } from 'lucide-react';

interface QcReportModalProps {
  isOpen: boolean;
  qc: Results['qc'];
  onClose: () => void;
}

export function QcReportModal({ isOpen, qc, onClose }: QcReportModalProps) {
  const footerContent = (
    <div className="flex items-center justify-end w-full">
      <Button variant="primary" size="md" onClick={onClose}>
        Close report
      </Button>
    </div>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="2xl"
      badge={{
        icon: <ShieldCheck size={14} className="text-blue-600" />,
        text: 'Automated QC Audit',
      }}
      title="Automated Quality Control Report"
      subtitle="Comprehensive breakdown of acoustic verification, subtitle speed, and broadcast constraints."
      footer={footerContent}
    >
      <div className="flex flex-col gap-5 py-1">
        {/* Status block */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 bg-slate-50 border border-slate-200/80 rounded-xl text-xs">
          <div>
            <span className="block text-slate-500 font-medium mb-0.5">Release Readiness:</span>
            <strong className="text-slate-900 font-semibold">Human Release Approval Required</strong>
          </div>
          <div>
            <span className="block text-slate-500 font-medium mb-0.5">Overall Status:</span>
            <span className="inline-flex items-center gap-1 font-bold uppercase tracking-wider text-[#0047ab]">
              <CheckCircle2 size={13} />
              {qc.status.replace(/_/g, ' ')}
            </span>
          </div>
        </div>

        {/* Inspection Checklist */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5">
            Inspection Checklist
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {Object.entries(qc.checks || {}).map(([key, val]) => (
              <div
                key={key}
                className="p-3 bg-white border border-slate-200/90 rounded-lg shadow-2xs text-xs flex flex-col gap-0.5"
              >
                <span className="font-semibold text-slate-800 capitalize">
                  {key.replace(/_/g, ' ')}
                </span>
                <span className="font-medium text-[#0047ab] capitalize text-[11px]">
                  {val.replace(/_/g, ' ')}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Documented System Limitations */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
            Documented System Limitations
          </h4>
          <ul className="list-disc pl-5 space-y-1.5 text-xs text-slate-600 leading-relaxed">
            {qc.limitations.map((lim, i) => (
              <li key={i}>{lim}</li>
            ))}
          </ul>
        </div>
      </div>
    </Modal>
  );
}
