import React from 'react';

type Status = 'detected' | 'building' | 'running' | 'error' | 'stopped' | 'idle' | 'resolving' | 'testing';

interface StatusIndicatorProps {
  status: Status;
  progress?: number;
  currentStep?: string;
  logsUrl?: string;
}

const statusConfig: Record<Status, { icon: string; color: string; bgColor: string; borderColor: string; label: string }> = {
  detected: {
    icon: 'fa-search',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/20',
    label: 'Detected'
  },
  building: {
    icon: 'fa-circle-notch fa-spin',
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/20',
    label: 'Building'
  },
  running: {
    icon: 'fa-play-circle',
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/20',
    label: 'Running'
  },
  error: {
    icon: 'fa-exclamation-triangle',
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/20',
    label: 'Error'
  },
  stopped: {
    icon: 'fa-stop-circle',
    color: 'text-gray-400',
    bgColor: 'bg-gray-500/10',
    borderColor: 'border-gray-500/20',
    label: 'Stopped'
  },
  idle: {
    icon: 'fa-pause-circle',
    color: 'text-gray-500',
    bgColor: 'bg-white/5',
    borderColor: 'border-white/10',
    label: 'Idle'
  },
  resolving: {
    icon: 'fa-wrench fa-spin',
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/20',
    label: 'Resolving Issues'
  },
  testing: {
    icon: 'fa-vial fa-spin',
    color: 'text-pink-400',
    bgColor: 'bg-pink-500/10',
    borderColor: 'border-pink-500/20',
    label: 'Running Tests'
  }
};

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  progress,
  currentStep,
  logsUrl
}) => {
  const config = statusConfig[status];

  return (
    <div className={`glass-panel rounded-2xl p-6 relative overflow-hidden transition-all duration-300 ${status === 'running' ? 'shadow-[0_0_30px_rgba(16,185,129,0.15)]' : ''}`}>
      {/* Background Glow */}
      <div className={`absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl opacity-10 -mr-10 -mt-10 ${config.bgColor.replace('bg-', 'bg-')}`}></div>

      <div className="flex items-start justify-between mb-6 relative">
        <div className="flex items-center space-x-4">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${config.bgColor} ${config.borderColor} border shadow-inner`}>
            <i className={`fas ${config.icon} ${config.color} text-xl drop-shadow-md`}></i>
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-100 tracking-tight">{config.label}</h3>
            {currentStep && (
              <p className="text-xs text-gray-400 font-mono mt-0.5 max-w-[200px] truncate">{currentStep}</p>
            )}
          </div>
        </div>
        {logsUrl && (
          <a
            href={logsUrl}
            className="glass-button text-xs px-3 py-1.5 rounded-lg text-blue-300 hover:text-blue-100 hover:bg-blue-500/20 border-blue-500/20"
            title="View Logs"
            target="_blank"
            rel="noopener noreferrer"
          >
            <i className="fas fa-terminal mr-1.5"></i>Logs
          </a>
        )}
      </div>

      {progress !== undefined && (
        <div className="mt-4 relative">
          <div className="flex justify-between items-end mb-2">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Progress</span>
            <span className="text-sm font-bold text-white font-mono">{progress}%</span>
          </div>
          <div className="w-full h-2 bg-black/40 rounded-full overflow-hidden border border-white/5">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out relative overflow-hidden ${status === 'error' ? 'bg-red-500' :
                  status === 'running' ? 'bg-emerald-500' :
                    status === 'building' ? 'bg-amber-500' :
                      'bg-indigo-500'
                }`}
              style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
            >
              {/* Shimmer effect */}
              {(status === 'building' || status === 'resolving') && (
                <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};