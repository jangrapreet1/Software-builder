import React from 'react';

export type BuildStep =
  | 'idle'
  | 'detecting'
  | 'planning'
  | 'generating'
  | 'validating'
  | 'building'
  | 'launching'
  | 'running'
  | 'error'
  | 'resolving';

interface StepDef {
  key: BuildStep;
  label: string;
  icon: string;
  /** statuses that count as "active" for this step */
  activeFor?: string[];
}

const STEPS: StepDef[] = [
  { key: 'detecting',   label: 'Detect',    icon: 'fa-radar' },
  { key: 'planning',    label: 'Plan',       icon: 'fa-sitemap' },
  { key: 'generating',  label: 'Generate',   icon: 'fa-magic' },
  { key: 'validating',  label: 'Validate',   icon: 'fa-shield-check' },
  { key: 'building',    label: 'Build',      icon: 'fa-hammer' },
  { key: 'launching',   label: 'Launch',     icon: 'fa-rocket' },
  { key: 'running',     label: 'Running',    icon: 'fa-check-circle' },
];

/**
 * Map the coarse `InstanceState.status` → which stepper step is active.
 * The building status covers planning + generating + validating + building.
 */
function mapStatusToStep(status: string, currentStep?: string): BuildStep {
  if (status === 'idle')      return 'idle';
  if (status === 'detected')  return 'detecting';
  if (status === 'resolving') return 'resolving';
  if (status === 'error')     return 'error';
  if (status === 'running')   return 'running';
  if (status === 'stopped')   return 'idle';

  // building — try to be more granular by matching currentStep text
  if (status === 'building') {
    const step = (currentStep || '').toLowerCase();
    if (step.includes('plan') || step.includes('analyz'))  return 'planning';
    if (step.includes('generat') || step.includes('code')) return 'generating';
    if (step.includes('valid') || step.includes('syntax')) return 'validating';
    if (step.includes('build') || step.includes('docker')) return 'building';
    if (step.includes('launch') || step.includes('start')) return 'launching';
    return 'generating'; // default mid-build
  }
  if (status === 'testing') return 'validating';
  return 'idle';
}

function getStepIndex(step: BuildStep): number {
  return STEPS.findIndex(s => s.key === step);
}

interface Props {
  status: string;
  currentStep?: string;
}

const BuildWorkflowStepper: React.FC<Props> = ({ status, currentStep }) => {
  const activeStep = mapStatusToStep(status, currentStep);
  const activeIdx  = getStepIndex(activeStep);
  const isError    = status === 'error';
  const isIdle     = activeStep === 'idle';
  const isResolving = activeStep === 'resolving';

  if (isIdle) return null;

  return (
    <div className="glass-panel rounded-2xl px-6 py-4 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Build Pipeline
        </span>
        {isResolving && (
          <span className="text-xs text-amber-400 flex items-center gap-1.5 animate-pulse">
            <i className="fas fa-circle-notch fa-spin text-[10px]"></i>
            Auto-fixing…
          </span>
        )}
        {isError && (
          <span className="text-xs text-red-400 flex items-center gap-1.5">
            <i className="fas fa-exclamation-circle text-[10px]"></i>
            Build failed
          </span>
        )}
        {activeStep === 'running' && (
          <span className="text-xs text-emerald-400 flex items-center gap-1.5">
            <i className="fas fa-circle-check text-[10px]"></i>
            Live
          </span>
        )}
      </div>

      <div className="flex items-center">
        {STEPS.map((step, idx) => {
          const isDone    = !isError && activeIdx > idx;
          const isActive  = !isError && activeIdx === idx;
          const isFailed  = isError && activeIdx === idx;

          let circleClass = 'border-white/10 text-gray-600 bg-white/3';
          if (isDone)   circleClass = 'border-emerald-500/50 text-emerald-400 bg-emerald-500/10';
          if (isActive && !isError) circleClass = 'border-primary text-white bg-primary/20 shadow-[0_0_12px_rgba(99,102,241,0.4)]';
          if (isFailed) circleClass = 'border-red-500/50 text-red-400 bg-red-500/10';

          let lineClass = 'bg-white/5';
          if (isDone) lineClass = 'bg-emerald-500/40';
          if (isActive && idx < STEPS.length - 1) lineClass = 'bg-primary/30';

          return (
            <React.Fragment key={step.key}>
              <div className="stepper-node flex-none">
                <div className={`stepper-circle ${circleClass}`}>
                  {isDone ? (
                    <i className="fas fa-check text-[10px]"></i>
                  ) : isActive && !isError ? (
                    <i className={`fas ${step.icon} text-[10px] animate-pulse`}></i>
                  ) : isFailed ? (
                    <i className="fas fa-xmark text-[10px]"></i>
                  ) : (
                    <i className={`fas ${step.icon} text-[10px]`}></i>
                  )}
                </div>
                <span className={`text-[9px] font-medium mt-1 transition-colors duration-300 ${
                  isDone ? 'text-emerald-400' : isActive ? 'text-white' : isFailed ? 'text-red-400' : 'text-gray-600'
                }`}>
                  {step.label}
                </span>
              </div>

              {idx < STEPS.length - 1 && (
                <div className={`stepper-line mx-1 ${lineClass}`}></div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {currentStep && (
        <p className="text-[11px] text-gray-500 mt-3 text-center truncate">
          {currentStep}
        </p>
      )}
    </div>
  );
};

export default BuildWorkflowStepper;
