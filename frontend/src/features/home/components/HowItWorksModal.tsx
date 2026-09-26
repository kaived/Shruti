import {
  CheckCircle2,
  FileText,
  Languages,
  Mic,
  ShieldCheck,
  UploadCloud,
  Zap,
} from 'lucide-react';
import { Modal, Button } from '../../../shared/ui';

export interface HowItWorksModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const PIPELINE_STEPS = [
  {
    step: '01',
    title: 'Upload your video',
    icon: UploadCloud,
    iconBg: 'bg-sky-50 text-sky-600',
    badge: 'MP4, MKV or WebM',
    description:
      'Choose a Bengali video (up to 500 MB). We check that the video and its sound can be read, then get to work. You can close the page while it runs.',
  },
  {
    step: '02',
    title: 'Bengali captions with speakers',
    icon: Mic,
    iconBg: 'bg-blue-50 text-blue-700',
    badge: 'Who said what, and when',
    description:
      'AI writes down the Bengali dialogue word by word, keeps English words like "office" or "meeting" in English, and labels each line with the person speaking.',
  },
  {
    step: '03',
    title: 'English and Hindi subtitles',
    icon: Languages,
    iconBg: 'bg-purple-50 text-purple-600',
    badge: 'English & Hindi',
    description:
      'Each Bengali line is translated into natural English and Hindi, timed to appear at exactly the same moment as the Bengali caption.',
  },
  {
    step: '04',
    title: 'Quality check and download',
    icon: CheckCircle2,
    iconBg: 'bg-emerald-50 text-emerald-600',
    badge: 'Review list included',
    description:
      'A separate AI listens for music and silence and flags any text that may not really have been said. You get a ranked list of lines to double-check, plus ready-to-use caption files.',
  },
];

const COMPLIANCE_PILLS = [
  { label: 'Line length', value: 'Up to 42 characters' },
  { label: 'Reading speed', value: 'Easy to follow' },
  { label: 'Made-up text', value: 'Flagged for review' },
  { label: 'Files', value: 'Captions + report' },
];

export function HowItWorksModal({ isOpen, onClose }: HowItWorksModalProps) {
  const footerContent = (
    <>
      <div className="flex items-center gap-2 text-xs text-slate-600">
        <FileText size={15} className="text-slate-400 shrink-0" />
        <span className="hidden sm:inline">
          You get Bengali captions, English and Hindi subtitles, and a report of lines to double-check.
        </span>
        <span className="sm:hidden">Captions, subtitles and a review report.</span>
      </div>
      <Button variant="primary" size="sm" onClick={onClose}>
        Got it
      </Button>
    </>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="4xl"
      badge={{
        icon: <Zap size={13} className="text-blue-600" />,
        text: 'Overview',
      }}
      title="How Shruti Works"
      subtitle="Turn a Bengali video into captions and English and Hindi subtitles, with a list of lines worth a second look."
      footer={footerContent}
    >
      <div className="flex flex-col gap-5">
        {/* 4 Pipeline Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {PIPELINE_STEPS.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.step}
                className="flex flex-col p-4 sm:p-5 bg-slate-50/70 hover:bg-white border border-slate-200/90 hover:border-slate-300 rounded-xl transition-all hover:shadow-xs"
              >
                {/* Symmetrical Top Row: [Icon + Step] on Left | [Feature Badge] on Right */}
                <div className="flex items-center justify-between mb-3.5 pb-2.5 border-b border-slate-200/60">
                  <div className="flex items-center gap-2.5">
                    <div className={`flex items-center justify-center w-8 h-8 rounded-lg shrink-0 ${item.iconBg}`}>
                      <Icon size={17} />
                    </div>
                    <span className="text-xs font-bold text-slate-500 font-mono tracking-wider uppercase">
                      Step {item.step}
                    </span>
                  </div>
                  <span className="text-[11px] font-semibold text-slate-600 bg-white border border-slate-200 px-2.5 py-1 rounded-md shadow-2xs">
                    {item.badge}
                  </span>
                </div>

                {/* Title and description */}
                <div className="flex-1">
                  <h3 className="text-sm sm:text-[15px] font-bold text-slate-900 tracking-tight leading-snug mb-1.5">
                    {item.title}
                  </h3>
                  <p className="text-xs sm:text-[13px] text-slate-600 leading-relaxed">
                    {item.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Quality Control & Standards Highlights */}
        <div className="flex flex-col gap-3 p-4 sm:p-4.5 rounded-xl bg-slate-50 border border-slate-200">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-700 uppercase tracking-wide">
            <ShieldCheck size={16} className="text-blue-700 shrink-0" />
            <span>Broadcast Subtitle Standards Built-In</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {COMPLIANCE_PILLS.map((pill) => (
              <div
                key={pill.label}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-white border border-slate-200/90 rounded-full text-xs shadow-2xs"
              >
                <span className="text-slate-500 font-medium">{pill.label}:</span>
                <span className="text-slate-900 font-semibold">{pill.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  );
}
