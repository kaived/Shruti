import type { StageConfig } from '../types';

interface StageStepperProps {
  stages: StageConfig[];
  activeStageIdx: number;
  isFailed: boolean;
}

export function StageStepper({ stages, activeStageIdx, isFailed }: StageStepperProps) {
  return (
    <div className="stage-stepper">
      {stages.map((stg, idx) => {
        const isCompleted = !isFailed && idx < activeStageIdx;
        const isCurrent = !isFailed && idx === activeStageIdx;
        const isFailedStage = isFailed && idx === activeStageIdx;

        return (
          <div
            key={stg.key}
            className={`step-item ${isCompleted ? 'step-completed' : ''} ${
              isCurrent ? 'step-current' : ''
            } ${isFailedStage ? 'step-failed' : ''}`}
          >
            <div className="step-indicator">
              {isCompleted && (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              )}
              {isCurrent && <span className="step-spinner" />}
              {isFailedStage && <span>!</span>}
              {!isCompleted && !isCurrent && !isFailedStage && <span>{idx + 1}</span>}
            </div>

            <div className="step-content">
              <div className="step-name">{stg.label}</div>
              <div className="step-desc">{stg.subtext}</div>
            </div>

            {isCurrent && <span className="step-tag-active">In progress</span>}
            {isCompleted && <span className="step-tag-done">Done</span>}
          </div>
        );
      })}
    </div>
  );
}
