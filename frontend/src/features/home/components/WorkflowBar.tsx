import { Fragment } from 'react';
import type { ScreenView } from '../types';

interface WorkflowBarProps {
  currentView: ScreenView;
  filename?: string;
}

const STEPS: { key: ScreenView; label: string; stepNumber: string; subtitle: string }[] = [
  {
    key: 'upload',
    label: 'Upload Video',
    stepNumber: '01',
    subtitle: 'Select or drop Bengali media',
  },
  {
    key: 'processing',
    label: 'AI Captioning & Alignment',
    stepNumber: '02',
    subtitle: 'ASR, diarization & QC check',
  },
  {
    key: 'workspace',
    label: 'Caption Studio & QC Review',
    stepNumber: '03',
    subtitle: 'Review cues & download packages',
  },
];

export function WorkflowBar({ currentView, filename }: WorkflowBarProps) {
  return (
    <div className="home-workflow-bar" role="navigation" aria-label="Workflow progress">
      <div className="workflow-steps-container">
        {STEPS.map((step, idx) => {
          const isActive = currentView === step.key;
          const isPassed =
            (step.key === 'upload' && currentView !== 'upload') ||
            (step.key === 'processing' && currentView === 'workspace');

          return (
            <Fragment key={step.key}>
              <div
                className={`workflow-step-pill ${isActive ? 'is-active' : ''} ${isPassed ? 'is-passed' : ''}`}
              >
                <div className="step-num-badge">{isPassed ? '✓' : step.stepNumber}</div>
                <div className="step-text-col">
                  <span className="step-title">{step.label}</span>
                  <span className="step-desc">
                    {isActive && filename && step.key !== 'upload' ? filename : step.subtitle}
                  </span>
                </div>
              </div>

              {idx < STEPS.length - 1 && (
                <div
                  className={`step-divider-arrow ${isPassed ? 'is-passed' : isActive ? 'is-active' : ''}`}
                  aria-hidden="true"
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </div>
              )}
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}
