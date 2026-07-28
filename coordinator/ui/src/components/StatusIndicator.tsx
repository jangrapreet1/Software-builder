import React from 'react';

type Status = 'detected' | 'building' | 'running' | 'error' | 'stopped' | 'idle' | 'resolving' | 'testing';

interface StatusIndicatorProps {
  status: Status;
  progress?: number;
  currentStep?: string;
  logsUrl?: string;
}

interface StatusCfg {
  icon: string;
  color: string;
  bgColor: string;
  borderColor: string;
  label: string;
  barGradient: string;
  outerGlow: string;
}

const statusConfig: Record<Status, StatusCfg> = {
  detected:  { icon: 'fa-search',         color: 'text-blue-400',   bgColor: 'bg-blue-500/10',   borderColor: 'border-blue-500/20',   label: 'Detected',         barGradient: 'from-blue-500 to-indigo-400',   outerGlow: '' },
  building:  { icon: 'fa-circle-notch fa-spin', color: 'text-amber-400', bgColor: 'bg-amber-500/10', borderColor: 'border-amber-500/20', label: 'Building',    barGradient: 'from-amber-500 to-yellow-400',  outerGlow: 'shadow-[0_0_24px_rgba(245,158,11,0.12)]' },
  running:   { icon: 'fa-play-circle',    color: 'text-emerald-400',bgColor: 'bg-emerald-500/10',borderColor: 'border-emerald-500/20', label: 'Running',         barGradient: 'from-emerald-500 to-teal-400',  outerGlow: 'shadow-[0_0_30px_rgba(16,185,129,0.15)]' },
  error:     { icon: 'fa-exclamation-triangle', color: 'text-red-400', bgColor: 'bg-red-500/10',  borderColor: 'border-red-500/20',    label: 'Error',           barGradient: 'from-red-500 to-rose-600',      outerGlow: 'shadow-[0_0_24px_rgba(239,68,68,0.12)]' },
  stopped:   { icon: 'fa-stop-circle',    color: 'text-gray-400',   bgColor: 'bg-gray-500/10',   borderColor: 'border-gray-500/20',   label: 'Stopped',         barGradient: 'from-gray-600 to-gray-500',     outerGlow: '' },
  idle:      { icon: 'fa-pause-circle',   color: 'text-gray-500',   bgColor: 'bg-white/5',       borderColor: 'border-white/10',      label: 'Idle',            barGradient: 'from-indigo-600 to-indigo-500', outerGlow: '' },
  resolving: { icon: 'fa-wrench',         color: 'text-purple-400', bgColor: 'bg-purple-500/10', borderColor: 'border-purple-500/20', label: 'Resolving Issues',barGradient: 'from-purple-500 to-indigo-400', outerGlow: 'shadow-[0_0_24px_rgba(139,92,246,0.12)]' },
  testing:   { icon: 'fa-vial',           color: 'text-pink-400',   bgColor: 'bg-pink-500/10',   borderColor: 'border-pink-500/20',   label: 'Running Tests',   barGradient: 'from-pink-500 to-fuchsia-400',  outerGlow: '' },
};

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  progress,
  currentStep,
  logsUrl,
}) => {
  const config = statusConfig[status];
  const isAnimating = status === 'building' || status === 'resolving' || status === 'testing';

  // Pulsing dot color for active states
  const pulseDot =
    status === 'running'   ? 'bg-emerald-400' :
    status === 'building'  ? 'bg-amber-400' :
    status === 'resolving' ? 'bg-purple-400' :
    status === 'testing'   ? 'bg-pink-400' :
    null;

  return (
    <div className={`glass-panel rounded-2xl p-5 relative overflow-hidden transition-all duration-500 border ${config.borderColor} ${config.outerGlow}`}>
      {/* Ambient blob */}
      <div className={`absolute top-0 right-0 w-28 h-28 rounded-full blur-3xl opacity-15 -mr-8 -mt-8 ${config.bgColor}`}></div>

      <div className="relative flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          {/* Status icon */}
          <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${config.bgColor} ${config.borderColor} border`}>
            <i className={`fas ${config.icon} ${config.color} text-lg`}></i>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-gray-100 leading-tight">{config.label}</h3>
              {pulseDot && (
                <span className={`relative inline-flex w-2 h-2 rounded-full ${pulseDot}`}>
                  <span className={`absolute inset-0 rounded-full ${pulseDot} opacity-70 animate-ping`}></span>
                </span>
              )}
            </div>
            {currentStep && (
              <p className="text-[11px] text-gray-500 font-mono mt-0.5 max-w-[200px] truncate">{currentStep}</p>
            )}
          </div>
        </div>

        {logsUrl && (
          <a
            href={logsUrl}
            className="glass-button text-xs px-3 py-1.5 rounded-lg text-blue-300 hover:text-blue-100 hover:bg-blue-500/20 border-blue-500/20 shrink-0"
            title="View Logs"
            target="_blank"
            rel="noopener noreferrer"
          >
            <i className="fas fa-terminal mr-1.5"></i>Logs
          </a>
        )}
      </div>

      {progress !== undefined && (
        <div className="relative">
          <div className="flex justify-between items-end mb-1.5">
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Progress</span>
            <span className="text-sm font-bold text-white font-mono tabular-nums">{Math.round(progress)}%</span>
          </div>
          <div className="w-full h-2 bg-black/40 rounded-full overflow-hidden border border-white/5">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out bg-gradient-to-r ${config.barGradient} relative overflow-hidden`}
              style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
            >
              {isAnimating && (
                <div
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                  style={{ animation: 'shimmer 1.5s infinite' }}
                ></div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};